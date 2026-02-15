"""
Registry of the heater registers. It contains list of known registers and information needed to decode and encode them.

Settings are loaded from YAML config files via load_registry(name). Configs live in the package configs/ directory.
"""

import logging
from importlib import resources
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

import yaml
from pydantic import BaseModel, Field

from ..registers import DECODER_REGISTRY, ENCODER_REGISTRY, ENUM_REGISTRY
from ..registers.decoders import (
    Decoder,
    decode_map,
    decode_heater_mode,
    decode_scaled_temp,
    decode_scaled_pressure,
)
from ..registers.encoders import (
    Encoder,
    encode_heater_mode,
    encode_map,
    encode_scaled_temp,
)

logger = logging.getLogger(__name__)


class RegistryConfigError(Exception):
    """Raised when registry YAML config is invalid or incomplete."""


@dataclass
class SettingDefinition:
    """Definition of a setting's register and bit location."""

    register: str
    decode_function: Decoder
    encode_function: Optional[Encoder] = None
    bit_index: Optional[int] = None

    @property
    def is_read_only(self) -> bool:
        """Derived property: read-only if no encode_function."""
        return self.encode_function is None

    def decode(self, hex_val: str) -> Any:
        """Decode the value from a register hex string."""
        return self.decode_function(hex_val, self.bit_index)

    def encode(self, value: Any, current_hex: Optional[str] = None) -> Optional[str]:
        """Encode a value to a register hex string."""
        if self.encode_function is None:
            raise ValueError("Setting is read-only (no encode_function)")
        return self.encode_function(value, self.bit_index, current_hex)


# --- Pydantic schema for YAML validation ---


class MapDecodeEncodeSpec(BaseModel):
    """Parameterized map type: maps bit to enum values."""

    type: str = Field(..., pattern="^map$")
    true_value: str = Field(..., min_length=1)
    false_value: str = Field(..., min_length=1)


class SettingSpec(BaseModel):
    """Schema for a single setting in YAML config."""

    reg: str = Field(..., min_length=1, alias="register")
    decode: Union[str, MapDecodeEncodeSpec]
    encode: Optional[Union[str, MapDecodeEncodeSpec]] = None
    bit_index: Optional[int] = Field(None, ge=0, le=15)

    model_config = {"populate_by_name": True}


def _resolve_enum_path(path: str) -> Any:
    """Resolve 'ManualMode.ENABLED' to ManualMode.ENABLED using ENUM_REGISTRY."""
    parts = path.split(".", 1)
    if len(parts) != 2:
        raise RegistryConfigError(f"Invalid enum path: {path!r}. Expected 'EnumName.MEMBER'.")
    enum_name, member_name = parts
    if enum_name not in ENUM_REGISTRY:
        raise RegistryConfigError(
            f"Unknown enum {enum_name!r} in path {path!r}. "
            f"Known: {list(ENUM_REGISTRY.keys())}."
        )
    enum_cls = ENUM_REGISTRY[enum_name]
    if not hasattr(enum_cls, member_name):
        raise RegistryConfigError(
            f"Unknown member {member_name!r} in enum {enum_name}. "
            f"Known: {[m for m in dir(enum_cls) if not m.startswith('_')]}."
        )
    return getattr(enum_cls, member_name)


def _resolve_spec(
    spec: Optional[Union[str, MapDecodeEncodeSpec]],
    setting_name: str,
    *,
    registry: dict[str, Any],
    factory_fn: Callable[..., Any],
    kind: str,
) -> Optional[Any]:
    """Resolve decode/encode spec to a callable. Returns None if spec is None."""
    if spec is None:
        return None
    if isinstance(spec, str):
        if spec not in registry:
            raise RegistryConfigError(
                f"Unknown {kind} {spec!r} for setting {setting_name!r}. "
                f"Known: {list(registry.keys())}."
            )
        return registry[spec]
    if spec.type == "map":
        true_val = _resolve_enum_path(spec.true_value)
        false_val = _resolve_enum_path(spec.false_value)
        return factory_fn(true_value=true_val, false_value=false_val)
    raise RegistryConfigError(
        f"Unknown {kind} type {spec.type!r} for setting {setting_name!r}."
    )


def _resolve_decode(spec: Union[str, MapDecodeEncodeSpec], setting_name: str) -> Decoder:
    """Resolve decode spec to a decoder callable."""
    result = _resolve_spec(
        spec, setting_name,
        registry=DECODER_REGISTRY,
        factory_fn=decode_map,
        kind="decoder",
    )
    assert result is not None  # decode is required
    return result


def _resolve_encode(
    spec: Optional[Union[str, MapDecodeEncodeSpec]], setting_name: str
) -> Optional[Encoder]:
    """Resolve encode spec to an encoder callable, or None for read-only."""
    return _resolve_spec(
        spec, setting_name,
        registry=ENCODER_REGISTRY,
        factory_fn=encode_map,
        kind="encoder",
    )


def _parse_setting(setting_name: str, raw: dict[str, Any]) -> SettingDefinition:
    """Parse raw YAML setting dict into SettingDefinition."""
    spec = SettingSpec.model_validate(raw)
    decode_fn = _resolve_decode(spec.decode, setting_name)
    encode_fn = _resolve_encode(spec.encode, setting_name)
    return SettingDefinition(
        register=spec.reg,
        decode_function=decode_fn,
        encode_function=encode_fn,
        bit_index=spec.bit_index,
    )


def load_registry(
    name: str,
    config_dir: Optional[Path] = None,
) -> dict[str, SettingDefinition]:
    """Load settings registry from YAML config by name.

    Args:
        name: Config file name without extension (e.g. 'kospel_cmi_standard').
        config_dir: Optional directory for config files (used in tests). If None, loads from package configs/.

    Returns:
        Dict mapping setting names to SettingDefinition.

    Raises:
        RegistryConfigError: If config is invalid, incomplete, or not found.
    """
    if config_dir is not None:
        config_path = config_dir / f"{name}.yaml"
        if not config_path.exists():
            logger.error("Config file not found: %s", config_path)
            raise RegistryConfigError(f"Config {name!r} not found at {config_path}.")
        content = config_path.read_text()
    else:
        try:
            pkg = resources.files("kospel_cmi")
            config_path = pkg / "configs" / f"{name}.yaml"
            content = config_path.read_text()
        except FileNotFoundError as e:
            logger.error("Config not found: %s", e)
            raise RegistryConfigError(
                f"Config {name!r} not found in package configs."
            ) from e

    try:
        raw = yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.error("Invalid YAML in config %s: %s", name, e)
        raise RegistryConfigError(f"Invalid YAML in config {name!r}: {e}.") from e

    if not isinstance(raw, dict):
        logger.error("Config %s root must be a dict, got %s", name, type(raw))
        raise RegistryConfigError(
            f"Config {name!r} root must be a mapping, got {type(raw).__name__}."
        )

    if not raw:
        logger.error("Config %s is empty", name)
        raise RegistryConfigError(f"Config {name!r} is empty.")

    result: dict[str, SettingDefinition] = {}
    for setting_name, setting_raw in raw.items():
        if not isinstance(setting_raw, dict):
            raise RegistryConfigError(
                f"Setting {setting_name!r} must be a mapping, got {type(setting_raw).__name__}."
            )
        try:
            result[setting_name] = _parse_setting(setting_name, setting_raw)
        except Exception as e:
            if isinstance(e, RegistryConfigError):
                raise
            logger.exception("Failed to parse setting %s", setting_name)
            raise RegistryConfigError(
                f"Failed to parse setting {setting_name!r}: {e}."
            ) from e

    return result
