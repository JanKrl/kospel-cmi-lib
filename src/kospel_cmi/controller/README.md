# SETTINGS_REGISTRY

The `SETTINGS_REGISTRY` (`kospel_cmi.controller.registry`) maps semantic setting names to their register locations and parsing logic. It serves as the single source of truth for how settings are stored in heater registers.

## Purpose

- **Centralized Configuration**: All register-to-setting mappings are defined in one place
- **Reusable Parsing**: Settings can be parsed from already-fetched register data without additional API calls
- **Type Safety**: Associates each setting with its proper decode/encode functions and data type
- **Dynamic Properties**: `HeaterController` automatically exposes all registry settings as properties

## Structure

Each entry in `SETTINGS_REGISTRY` maps a semantic name to a `SettingDefinition`:

```python
"setting_name": SettingDefinition(
    register="0b55",              # Register address (e.g., "0b55", "0b51")
    bit_index=3,                  # Optional: bit index for flag bits
    decode_function=decode_function, # Function to decode value from hex string
    encode_function=encode_function, # Optional: function to encode value to hex string
    is_read_only=False            # Derived property (True if encode_function is None)
)
```

## SettingDefinition Fields

- **`register`** (str): The register address where the setting is stored (e.g., `"0b55"`)
- **`bit_index`** (int, optional): For flag-based settings, the bit index within the register. Omitted for full-register values (like temperatures)
- **`decode_function`** (Decoder): Function that takes `(hex_val: str, bit_index: Optional[int])` and returns the decoded value
- **`encode_function`** (Encoder, optional): Function that takes `(value, bit_index: Optional[int], current_hex: Optional[str])` and returns hex string. None for read-only settings
- **`is_read_only`** (bool): Derived property (True if encode_function is None)

**Note**: The `encode()` method on `SettingDefinition` takes `(value, current_hex)` - the register and bit_index are stored in the definition itself.

## Example Registry Entries

### Flag-based setting (single bit)

```python
"is_manual_mode_enabled": SettingDefinition(
    register="0b55",
    bit_index=9,
    decode_function=decode_map(
        true_value=ManualMode.ENABLED,
        false_value=ManualMode.DISABLED,
    ),
    encode_function=encode_map(
        true_value=ManualMode.ENABLED,
        false_value=ManualMode.DISABLED,
    ),
)
```

### Full register value (temperature)

```python
"manual_temperature": SettingDefinition(
    register="0b8d",
    decode_function=decode_scaled_temp,
    encode_function=encode_scaled_temp
)
```

### Multi-bit setting (heater mode)

```python
"heater_mode": SettingDefinition(
    register="0b55",
    decode_function=decode_heater_mode,
    encode_function=encode_heater_mode
)
```

### Read-only status (pump running)

```python
"is_pump_co_running": SettingDefinition(
    register="0b51",
    bit_index=0,
    decode_function=decode_map(
        true_value=PumpStatus.RUNNING,
        false_value=PumpStatus.IDLE,
    ),
    # Read-only: no encode_function
)
```

## Decode/Encode Map Functions

The `decode_map()` and `encode_map()` functions are factory functions that create decoder/encoder functions for boolean flag bits that map to enum values.

### `decode_map(true_value, false_value)`

- Returns a decoder function that reads a boolean bit from a register
- Maps `True` (bit=1) to `true_value` enum
- Maps `False` (bit=0) to `false_value` enum
- Used for settings like `ManualMode`, `WaterHeaterEnabled`, `PumpStatus`

### `encode_map(true_value, false_value)`

- Returns an encoder function that writes an enum value as a boolean bit
- Maps `true_value` enum to `True` (bit=1)
- Maps `false_value` enum to `False` (bit=0)
- Also accepts plain boolean values
- Uses read-modify-write pattern to preserve other bits in the register

### Example usage

```python
from kospel_cmi.registers.decoders import decode_map
from kospel_cmi.registers.encoders import encode_map
from kospel_cmi.registers.enums import ManualMode

# Create a decoder that maps bit 9 to ManualMode enum
decoder = decode_map(
    true_value=ManualMode.ENABLED,
    false_value=ManualMode.DISABLED,
)

# Create an encoder that maps ManualMode enum to bit 9
encoder = encode_map(
    true_value=ManualMode.ENABLED,
    false_value=ManualMode.DISABLED,
)

# Use in registry
"is_manual_mode_enabled": SettingDefinition(
    register="0b55",
    bit_index=9,
    decode_function=decoder,
    encode_function=encoder,
)
```

## Usage

The registry is used internally by:

1. **`HeaterController.from_registers()`**: Decodes settings from already-fetched register data
2. **`HeaterController.save()`**: Encodes settings to register values before writing
3. **`HeaterController.__getattr__()`**: Provides dynamic property access to all registry settings
4. **`HeaterController.__setattr__()`**: Validates and stores pending writes for registry settings

## Adding New Settings

See the [Development Guide](../../../docs/development.md) for step-by-step instructions on adding new settings to the registry.
