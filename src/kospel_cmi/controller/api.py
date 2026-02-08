"""
High-level abstraction layer for managing electric heater settings and reading sensor values.

This module provides a registry-driven interface that automatically supports all settings
defined in SETTINGS_REGISTRY. The controller depends only on a RegisterBackend (HTTP or YAML).
"""

import logging
from typing import Dict, Any

from ..kospel.backend import RegisterBackend
from .registry import SETTINGS_REGISTRY, SettingDefinition

logger = logging.getLogger(__name__)


class HeaterController:
    """High-level controller for managing heater settings and sensor values.

    This class uses SETTINGS_REGISTRY as the source of truth for all settings,
    providing dynamic property access to all registry-defined settings.
    It reads and writes registers via the injected RegisterBackend.

    Supports async context manager protocol. When using HttpRegisterBackend,
    call aclose() or use ``async with HeaterController(...)`` to release the
    HTTP session when done.
    """

    def __init__(
        self,
        backend: RegisterBackend,
        registry: Dict[str, SettingDefinition] = SETTINGS_REGISTRY,
    ):
        """Initialize with a register backend.

        Args:
            backend: RegisterBackend for read/write (e.g. HttpRegisterBackend or YamlRegisterBackend)
            registry: Settings registry to use (defaults to SETTINGS_REGISTRY)
        """
        self._backend = backend
        self._registry = registry
        self._settings: Dict[str, Any] = {}  # Stores all decoded setting values
        self._pending_writes: Dict[
            str, Any
        ] = {}  # Tracks modified settings for batch writes
        self._register_cache: Dict[
            str, str
        ] = {}  # Cached register values (only registry registers)

    async def aclose(self) -> None:
        """Release resources owned by the controller and its backend.

        Calls the backend's aclose() if it has one (e.g. HttpRegisterBackend
        closes the aiohttp ClientSession). Safe to call multiple times (idempotent).

        Consumers should call aclose() when done with the controller (e.g. on
        integration unload), or use the controller as an async context manager.
        """
        aclose = getattr(self._backend, "aclose", None)
        if aclose is not None:
            await aclose()

    async def __aenter__(self) -> "HeaterController":
        """Enter async context. Returns self."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context. Releases resources via aclose()."""
        await self.aclose()

    async def refresh(self) -> None:
        """Load all settings from the backend (single batch read of registers)."""
        logger.info("Refreshing heater settings from backend")
        all_registers = await self._backend.read_registers("0b00", 256)

        if not all_registers:
            logger.warning("No registers read from backend")
            return

        self.from_registers(all_registers)
        logger.info("Heater settings refreshed successfully")

    def from_registers(self, registers: Dict[str, str]) -> None:
        """Load settings from already-fetched register data.

        This is more efficient than refresh() as it avoids additional API calls.

        Args:
            registers: Dictionary mapping register addresses to hex values
        """
        logger.debug(f"Decoding settings from {len(registers)} registers")

        # Clear previous settings
        self._settings.clear()
        self._register_cache.clear()

        # Iterate through all entries in SETTINGS_REGISTRY
        for setting_name, setting_def in self._registry.items():
            register = setting_def.register

            # Get register hex value (use default if missing)
            hex_val = registers.get(register)
            if not hex_val:
                logger.warning(
                    f"Register {register} not found in registers. Assigning empty value."
                )
                hex_val = "0000"

            # Store raw value in cache
            self._register_cache[register] = hex_val

            # Decode the setting value
            try:
                decoded_value = setting_def.decode(hex_val)
                self._settings[setting_name] = decoded_value
            except Exception as e:
                logger.warning(
                    f"Failed to decode {setting_name} from register {register}: {e}"
                )
                self._settings[setting_name] = None

        decoded_summary = " | ".join(
            f"{setting_name} ({setting.register}): {self._register_cache[setting.register]} → {self._settings[setting_name]}"
            for setting_name, setting in self._registry.items()
        )
        logger.debug(f"Decoded settings: {decoded_summary}")

        # Clear pending writes since we've refreshed
        self._pending_writes.clear()
        logger.debug(f"Decoded {len(self._settings)} settings")

    def __getattr__(self, name: str) -> Any:
        """Dynamic property access for settings.

        Args:
            name: Setting name (must exist in registry)

        Returns:
            Setting value

        Raises:
            AttributeError: If setting doesn't exist in registry
        """
        # Check if it's a private attribute (starts with _)
        if name.startswith("_"):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

        # Check if setting exists in registry
        if name not in self._registry:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'. "
                f"Available settings: {', '.join(sorted(self._registry.keys()))}"
            )

        # Return value from _settings (may be None if not loaded)
        return self._settings.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Dynamic property setting for writable settings.

        Args:
            name: Setting name (must exist in registry and be writable)
            value: Value to set

        Raises:
            AttributeError: If setting doesn't exist or is read-only
        """
        # Handle private attributes normally
        if name.startswith("_") or name in ("_backend", "_registry"):
            super().__setattr__(name, value)
            return

        # Check if setting exists in registry
        if name not in self._registry:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'. "
                f"Available settings: {', '.join(sorted(self._registry.keys()))}"
            )

        setting_def = self._registry[name]

        # Validate that setting is writable
        if setting_def.is_read_only:
            raise AttributeError(f"Setting '{name}' is read-only")

        # Store in both _settings and _pending_writes
        self._settings[name] = value
        self._pending_writes[name] = value
        logger.debug(f"Set {name} = {value} (pending write)")

    async def save(self) -> bool:
        """Write all pending changes to the heater.

        Returns:
            True if all writes succeeded, False otherwise
        """
        if not self._pending_writes:
            logger.debug("No pending writes")
            return True

        logger.info(f"Saving {len(self._pending_writes)} setting(s) to API")
        success = True

        # Group writes by register to batch read-modify-write operations
        writes_by_register: Dict[str, Dict[str, Any]] = {}
        for setting_name, value in self._pending_writes.items():
            setting_def = self._registry[setting_name]
            register = setting_def.register

            if register not in writes_by_register:
                writes_by_register[register] = {}
            writes_by_register[register][setting_name] = (value, setting_def)

        # Process each register
        for register, settings_to_write in writes_by_register.items():
            # Get current register value (from cache or read from API)
            original_hex = self._register_cache.get(register)
            if original_hex is None:
                logger.debug(f"Reading register {register} for write operation")
                original_hex = await self._backend.read_register(register)
                if original_hex is None:
                    logger.error(
                        f"Failed to read register {register} for write operation"
                    )
                    success = False
                    continue
                self._register_cache[register] = original_hex

            # Encode all settings for this register sequentially
            # Each encoder modifies the hex based on the previous result
            current_hex = original_hex
            for setting_name, (value, setting_def) in settings_to_write.items():
                try:
                    encoded_hex = setting_def.encode(value, current_hex=current_hex)
                    if encoded_hex is None:
                        logger.error(f"Failed to encode {setting_name}")
                        success = False
                        continue
                    current_hex = (
                        encoded_hex  # Use result for next setting in same register
                    )
                    logger.debug(
                        f"Encoded {setting_name}: {original_hex} → {current_hex}"
                    )
                except Exception as e:
                    logger.error(f"Error encoding {setting_name}: {e}")
                    success = False
                    continue

            # Write the register if it changed
            if current_hex != original_hex:
                write_success = await self._backend.write_register(
                    register, current_hex
                )
                if write_success:
                    logger.info(
                        f"Successfully wrote register {register}: {original_hex} → {current_hex}"
                    )
                    # Update cache with new value
                    self._register_cache[register] = current_hex
                    # Re-decode all settings for this register to update _settings dict
                    for setting_name, setting_def in self._registry.items():
                        if setting_def.register == register:
                            try:
                                decoded_value = setting_def.decode(current_hex)
                                self._settings[setting_name] = decoded_value
                                logger.debug(
                                    f"Updated {setting_name} = {decoded_value} after write"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to re-decode {setting_name} after write: {e}"
                                )
                else:
                    logger.error(f"Failed to write register {register}")
                    success = False
            else:
                logger.debug(f"Register {register} unchanged, skipping write")

        # Clear pending writes on success
        if success:
            self._pending_writes.clear()
            logger.info("All settings saved successfully")
        else:
            logger.error("Some settings failed to save")

        return success

    def get_setting(self, name: str) -> Any:
        """Explicit getter for a setting.

        Args:
            name: Setting name

        Returns:
            Setting value

        Raises:
            KeyError: If setting doesn't exist in registry
        """
        if name not in self._registry:
            raise KeyError(f"Setting '{name}' not found in registry")
        return self._settings.get(name)

    def set_setting(self, name: str, value: Any) -> None:
        """Explicit setter for a setting.

        Args:
            name: Setting name
            value: Value to set

        Raises:
            KeyError: If setting doesn't exist in registry
            ValueError: If setting is read-only
        """
        if name not in self._registry:
            raise KeyError(f"Setting '{name}' not found in registry")
        setting_def = self._registry[name]
        if setting_def.encode_function is None:
            raise ValueError(f"Setting '{name}' is read-only")
        self._settings[name] = value
        self._pending_writes[name] = value

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings.

        Returns:
            Dictionary mapping setting names to values
        """
        return self._settings.copy()

    def print_settings(self) -> None:
        """Print all current settings in a readable format."""
        print("\n--- Heater Settings ---")

        for setting_name in sorted(self._registry.keys()):
            value = self._settings.get(setting_name)
            setting_def = self._registry[setting_name]

            # Format value for display
            if value is None:
                value_str = "Unknown/Not loaded"
            elif isinstance(value, bool):
                value_str = "Enabled" if value else "Disabled"
            elif isinstance(value, float):
                value_str = (
                    f"{value:.1f}°C"
                    if "temperature" in setting_name
                    else f"{value:.2f}"
                )
            elif hasattr(value, "value"):  # Enum
                value_str = value.value
            else:
                value_str = str(value)

            read_only_str = " (read-only)" if setting_def.is_read_only else ""
            print(f"{setting_name}: {value_str}{read_only_str}")

        # Pending writes status
        if self._pending_writes:
            print(f"\nUnsaved Changes: Yes ({len(self._pending_writes)} setting(s))")
        else:
            print("\nUnsaved Changes: No")
        print()
