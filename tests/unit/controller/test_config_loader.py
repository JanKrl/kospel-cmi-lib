"""Unit tests for load_registry and config validation."""

import tempfile
from pathlib import Path

import pytest

from kospel_cmi.controller.registry import (
    RegistryConfigError,
    load_registry,
    SettingDefinition,
)


class TestLoadRegistry:
    """Tests for load_registry function."""

    def test_load_registry_returns_dict_of_setting_definitions(self) -> None:
        """load_registry returns Dict[str, SettingDefinition]."""
        registry = load_registry("kospel_cmi_standard")
        assert isinstance(registry, dict)
        assert all(isinstance(v, SettingDefinition) for v in registry.values())
        assert "heater_mode" in registry
        assert "manual_temperature" in registry

    def test_loaded_registry_has_expected_settings(self) -> None:
        """Loaded registry contains all settings from YAML."""
        registry = load_registry("kospel_cmi_standard")
        expected = {
            "heater_mode",
            "room_mode",
            "cwu_mode",
            "is_water_heater_enabled",
            "is_pump_co_running",
            "is_pump_circulation_running",
            "valve_position",
            "manual_temperature",
            "room_temperature_economy",
            "room_temperature_comfort",
            "room_temperature_comfort_plus",
            "room_temperature_comfort_minus",
            "cwu_temperature_economy",
            "cwu_temperature_comfort",
            "pressure",
            "water_current_temperature",
            "room_temperature",
            "party_vacation_end_minute",
            "party_vacation_end_hour",
            "party_vacation_end_day",
            "party_vacation_end_month",
            "party_vacation_end_year",
            "inlet_temperature",
            "outlet_temperature",
            "outside_temperature",
            "supply_setpoint",
            "room_setpoint",
            "power",
            "flow",
            "error_code",
            "work_mode",
        }
        assert set(registry.keys()) == expected

    def test_loaded_registry_decodes_same_as_hardcoded(self) -> None:
        """load_registry produces registry that decodes like the old hardcoded one."""
        from kospel_cmi.registers.enums import HeaterMode

        registry = load_registry("kospel_cmi_standard")
        heater_mode_def = registry["heater_mode"]
        temp_def = registry["manual_temperature"]
        pressure_def = registry["pressure"]

        # heater_mode: 0b55, bits 3,5,6,7,9
        assert heater_mode_def.decode("0800") == HeaterMode.SUMMER
        assert heater_mode_def.decode("2000") == HeaterMode.WINTER
        assert heater_mode_def.decode("0000") == HeaterMode.OFF
        assert heater_mode_def.decode("4000") == HeaterMode.PARTY
        assert heater_mode_def.decode("8000") == HeaterMode.VACATION
        assert heater_mode_def.decode("0002") == HeaterMode.MANUAL
        # manual_temperature: scaled by 10, 22.5 -> 225 -> 00e1 (le)
        assert temp_def.decode("e100") == 22.5
        # pressure: scaled by 100
        assert pressure_def.decode("6400") == 1.0

    def test_read_only_settings_have_no_encode(self) -> None:
        """Read-only settings have is_read_only=True."""
        registry = load_registry("kospel_cmi_standard")
        assert registry["pressure"].is_read_only
        assert registry["room_temperature"].is_read_only
        assert registry["water_current_temperature"].is_read_only
        assert registry["is_pump_co_running"].is_read_only
        assert not registry["heater_mode"].is_read_only

    def test_map_encode_decode_roundtrip(self) -> None:
        """Map-type setting encode then decode yields same value."""
        from kospel_cmi.registers.enums import WaterHeaterEnabled

        registry = load_registry("kospel_cmi_standard")
        water_heater_def = registry["is_water_heater_enabled"]
        # Encode ENABLED into base 0000
        encoded = water_heater_def.encode(WaterHeaterEnabled.ENABLED, current_hex="0000")
        assert encoded is not None
        decoded = water_heater_def.decode(encoded)
        assert decoded == WaterHeaterEnabled.ENABLED

    def test_unknown_config_raises(self) -> None:
        """Unknown config name raises RegistryConfigError."""
        with pytest.raises(RegistryConfigError, match="not found"):
            load_registry("nonexistent_config")


class TestRegistryConfigValidation:
    """Tests for schema validation and RegistryConfigError."""

    def test_invalid_yaml_raises(self) -> None:
        """Malformed YAML raises RegistryConfigError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "bad.yaml").write_text("not: valid: yaml: [")
            with pytest.raises(RegistryConfigError, match="Invalid YAML"):
                load_registry("bad", config_dir=path)

    def test_empty_config_raises(self) -> None:
        """Empty config raises RegistryConfigError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "empty.yaml").write_text("{}")
            with pytest.raises(RegistryConfigError, match="empty"):
                load_registry("empty", config_dir=path)

    def test_missing_decode_raises(self) -> None:
        """Setting without decode raises RegistryConfigError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "missing.yaml").write_text(
                "heater_mode:\n  register: \"0b55\"\n  encode: heater_mode\n"
            )
            with pytest.raises(RegistryConfigError, match="decode|validation"):
                load_registry("missing", config_dir=path)

    def test_map_without_bit_index_raises(self) -> None:
        """Map decode/encode without bit_index raises RegistryConfigError at load time."""
        config_dir = Path(__file__).resolve().parent.parent.parent / "fixtures" / "configs"
        with pytest.raises(RegistryConfigError, match="bit_index is required"):
            load_registry("bad_map", config_dir=config_dir)
