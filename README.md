# kospel-cmi-lib

Python client for the Kospel C.MI electric heater HTTP API.

## Features

- **Async-first**: Built on `asyncio` and `aiohttp` for non-blocking I/O
- **Type-safe**: Strict type hinting throughout
- **Registry-driven**: Settings defined declaratively in a central registry; dynamic property access on `HeaterController`
- **Simulator-capable**: Full simulator for offline development and testing (no hardware required)
- **Protocol-based**: Decoder/encoder interfaces via Python `Protocol` types

## Installation

```bash
# With uv (recommended)
uv add kospel-cmi-lib

# With pip
pip install kospel-cmi-lib
```

## Usage

Create a register backend (HTTP or YAML), then pass it to `HeaterController`.
When using `HttpRegisterBackend`, call `aclose()` or use the controller as an
async context manager to release the HTTP session when done.

**Recommended: async context manager** (resources released automatically):

```python
import asyncio
import aiohttp
from kospel_cmi.controller.api import HeaterController
from kospel_cmi.kospel.backend import HttpRegisterBackend, YamlRegisterBackend


async def main() -> None:
    api_base_url = "http://192.168.1.1/api/dev/65"  # Replace with your heater URL
    async with aiohttp.ClientSession() as session:
        backend = HttpRegisterBackend(session, api_base_url)
        async with HeaterController(backend=backend) as controller:
            await controller.refresh()
            print(controller.heater_mode)  # Access registry-defined settings
            # controller.heater_mode = "manual"  # Modify (if writable)
            # await controller.save()  # Write pending changes to the device
    # Session and controller resources released here


asyncio.run(main())
```

**Alternative: explicit `aclose()`** (for long-lived integrations):

```python
controller = HeaterController(backend=HttpRegisterBackend(session, api_base_url))
try:
    await controller.refresh()
    # ... use controller ...
finally:
    await controller.aclose()
```

For offline development or tests, use the YAML backend (no HTTP, no close needed):

```python
backend = YamlRegisterBackend(state_file="/path/to/state.yaml")
controller = HeaterController(backend=backend)
await controller.refresh()
```

### Setting Heater Mode

```python
import asyncio
import aiohttp
from kospel_cmi.controller.api import HeaterController
from kospel_cmi.kospel.backend import HttpRegisterBackend
from kospel_cmi.registers.enums import HeaterMode, ManualMode

async def main():
    async with aiohttp.ClientSession() as session:
        backend = HttpRegisterBackend(session, "http://192.168.1.1/api/dev/65")
        async with HeaterController(backend=backend) as controller:
            await controller.refresh()
            
            # Modify settings
            controller.heater_mode = HeaterMode.WINTER
            controller.manual_temperature = 22.0
            controller.is_manual_mode_enabled = ManualMode.ENABLED
            
            # Write all changes at once
            success = await controller.save()
            print(f"Settings saved: {success}")

asyncio.run(main())
```

## Heater API Protocol

### Register System

The heater exposes registers as hexadecimal strings in **little-endian format**:

- **Register Format**: 4-character hex string (e.g., `"d700"`)
- **Byte Order**: Little-endian (bytes swapped)
  - `"d700"` means: bytes are `[0xd7, 0x00]` in memory
  - When read as big-endian: `0x00d7` = 215
- **Value Type**: Signed 16-bit integers (-32768 to 32767)

### Flag Registers

Some registers use individual bits as flags (specific register addresses may vary per device/version):

**Register 0b55** (Flags):
- Bit 3: Summer mode
- Bit 4: Water heater enabled
- Bit 5: Winter mode
- Bit 9: Manual mode enabled

**Register 0b51** (Component Status):
- Bit 0: Pump CO running
- Bit 1: Pump circulation running
- Bit 2: Valve position (0=CO, 1=DHW)

**Heater Mode Logic** (register 0b55, bits 3 & 5):
- Summer: Bit 3=1, Bit 5=0
- Winter: Bit 3=0, Bit 5=1
- Off: Bit 3=0, Bit 5=0

### API Endpoints

**Base URL**: `http://<HEATER_IP>/api/dev/<DEVICE_ID>`

**Read Register**:
- `GET /api/dev/<DEVICE_ID>/<register>/<count>`
- Example: `GET /api/dev/65/0b55/1`
- Response: `{"regs": {"0b55": "d700"}, "sn": "...", "time": "..."}`

**Write Register**:
- `POST /api/dev/<DEVICE_ID>/<register>`
- Body: Hex string (e.g., `"d700"`)
- Response: `{"status": "0"}` on success

**Read Multiple Registers**:
- `GET /api/dev/<DEVICE_ID>/0b00/256` (reads 256 registers starting from 0b00)
- Response: `{"regs": {"0b00": "...", "0b01": "...", ...}}`

### Example Register Values

Register values may vary per device type / version. Currently the project includes only one `SETTINGS_REGISTRY` but may be extended with multiple configurations for various device types.

| Register | Description | Format | Example |
|----------|-------------|--------|---------|
| `0b31` | Room temperature setting | Temp (×10) | `"00e1"` = 22.5°C |
| `0b4b` | Room current temperature | Temp (×10) | `"00e6"` = 23.0°C |
| `0b2f` | Water temperature setting | Temp (×10) | `"01a4"` = 42.0°C |
| `0b4e` | Pressure | Pressure (×100) | `"01f4"` = 5.00 bar |
| `0b51` | Component status flags | Flags | `"0005"` (bits 0,2 set) |
| `0b55` | System flags | Flags | `"02a0"` (bits 5,7,9 set) |
| `0b8a` | Heater mode priority | Integer | `"0000"` = CO Priority |
| `0b8d` | Manual temperature | Temp (×10) | `"00e1"` = 22.5°C |

## SETTINGS_REGISTRY

The `SETTINGS_REGISTRY` (`kospel_cmi.controller.registry`) maps semantic setting names to their register locations and parsing logic. It serves as the single source of truth for how settings are stored in heater registers.

### Purpose

- **Centralized Configuration**: All register-to-setting mappings are defined in one place
- **Reusable Parsing**: Settings can be parsed from already-fetched register data without additional API calls
- **Type Safety**: Associates each setting with its proper decode/encode functions and data type
- **Dynamic Properties**: `HeaterController` automatically exposes all registry settings as properties

### Structure

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

### SettingDefinition Fields

- **`register`** (str): The register address where the setting is stored (e.g., `"0b55"`)
- **`bit_index`** (int, optional): For flag-based settings, the bit index within the register. Omitted for full-register values (like temperatures)
- **`decode_function`** (Decoder): Function that takes `(hex_val: str, bit_index: Optional[int])` and returns the decoded value
- **`encode_function`** (Encoder, optional): Function that takes `(value, bit_index: Optional[int], current_hex: Optional[str])` and returns hex string. None for read-only settings
- **`is_read_only`** (bool): Derived property (True if encode_function is None)

**Note**: The `encode()` method on `SettingDefinition` takes `(value, current_hex)` - the register and bit_index are stored in the definition itself.

### Example Registry Entries

**Flag-based setting** (single bit):
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

**Full register value** (temperature):
```python
"manual_temperature": SettingDefinition(
    register="0b8d",
    decode_function=decode_scaled_temp,
    encode_function=encode_scaled_temp
)
```

**Multi-bit setting** (heater mode):
```python
"heater_mode": SettingDefinition(
    register="0b55",
    decode_function=decode_heater_mode,
    encode_function=encode_heater_mode
)
```

**Read-only status** (pump running):
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

### Decode/Encode Map Functions

The `decode_map()` and `encode_map()` functions are factory functions that create decoder/encoder functions for boolean flag bits that map to enum values.

**`decode_map(true_value, false_value)`**:
- Returns a decoder function that reads a boolean bit from a register
- Maps `True` (bit=1) to `true_value` enum
- Maps `False` (bit=0) to `false_value` enum
- Used for settings like `ManualMode`, `WaterHeaterEnabled`, `PumpStatus`

**`encode_map(true_value, false_value)`**:
- Returns an encoder function that writes an enum value as a boolean bit
- Maps `true_value` enum to `True` (bit=1)
- Maps `false_value` enum to `False` (bit=0)
- Also accepts plain boolean values
- Uses read-modify-write pattern to preserve other bits in the register

**Example usage**:
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

### Usage

The registry is used internally by:

1. **`HeaterController.from_registers()`**: Decodes settings from already-fetched register data
2. **`HeaterController.save()`**: Encodes settings to register values before writing
3. **`HeaterController.__getattr__()`**: Provides dynamic property access to all registry settings
4. **`HeaterController.__setattr__()`**: Validates and stores pending writes for registry settings

## Common Register Mappings

### Temperature Registers (scaled ×10)
- `0b31`: Room temperature setting
- `0b4b`: Room current temperature
- `0b2f`: Water temperature setting
- `0b4a`: Water current temperature
- `0b4c`: Outside temperature
- `0b48`: Inlet temperature
- `0b49`: Outlet temperature
- `0b44`: Factor
- `0b8d`: Manual temperature
- `0b68`: Room temperature economy
- `0b69`: Room temperature comfort minus
- `0b6a`: Room temperature comfort
- `0b6b`: Room temperature comfort plus
- `0b66`: CWU temperature economy
- `0b67`: CWU temperature comfort

### Pressure/Flow Registers
- `0b4e`: Pressure (scaled ×100)
- `0b4f`: Flow rate (l/min, scaled ×10)
- `0b8a`: Pressure (scaled ×100)

### Flag Registers
- `0b51`: Component status (pumps, valve)
- `0b55`: System flags (modes, manual mode, water heater)

### Mode Registers
- `0b8a`: Heater mode priority (0=CO, 1=Heat Source, 2=Buffer)
- `0b55`: Heater mode (bits 3,5 for summer/winter/off)

## Development Guidelines

### Adding New Settings

1. **Add to `SETTINGS_REGISTRY`** in `controller/registry.py`:
   ```python
   "new_setting": SettingDefinition(
       register="0bXX",
       bit_index=Y,  # If it's a flag bit (omit for full register values)
       decode_function=decode_new_setting_from_reg,
       encode_function=encode_new_setting_to_reg  # Omit for read-only
   )
   ```

2. **Create decode function** in `registers/decoders.py` (if needed):
   ```python
   def decode_new_setting_from_reg(reg_hex: str, bit_index: Optional[int] = None) -> Optional[Type]:
       """Decode the setting value from a register hex string."""
       # For flag bits, use decode_bit_boolean or decode_map
       # For full register values, use decode_scaled_temp, decode_scaled_pressure, etc.
   ```

3. **Create encode function** in `registers/encoders.py` (if writable):
   ```python
   def encode_new_setting_to_reg(value: Type, bit_index: Optional[int], current_hex: Optional[str]) -> Optional[str]:
       """Encode the setting value to a register hex string.
       
       Args:
           value: The value to encode (enum, bool, float, etc.)
           bit_index: Bit index if it's a flag bit (None for full register values)
           current_hex: Current hex value of the register (required for read-modify-write)
       """
       # For flag bits: use encode_bit_boolean() or encode_map()
       # For full register values: use int_to_reg() directly
   ```

4. **Add enum** in `registers/enums.py` (if needed):
   ```python
   class NewSetting(Enum):
       VALUE1 = "Value 1"
       VALUE2 = "Value 2"
   ```

**Note**: Once added to `SETTINGS_REGISTRY`, the setting will automatically be available as a dynamic property on `HeaterController`!

### Best Practices

- **Use high-level API**: Prefer `HeaterController` class over direct register manipulation
- **Batch operations**: Use `HeaterController` class when modifying multiple settings
- **Avoid redundant calls**: Use `from_registers()` when you already have register data
- **Error handling**: Check return values and handle `None` results appropriately
- **Simulator mode**: Use YAML backend for development and testing

## Troubleshooting

### Common Issues

**Negative register values**: Normal for flags registers. The value `-32080` for register `0b55` means bits 8-15 are set, which is expected when multiple flags are enabled.

**Setting changes not taking effect**: Some settings may require additional flags to be set. Check the heater documentation or JS source for dependencies.

**API timeouts**: Ensure the heater IP is correct and reachable. Default timeout is 5 seconds (configurable in code).

**Import errors**: Make sure you're importing from the correct modules:
- `HeaterController` from `kospel_cmi.controller.api`
- `HttpRegisterBackend`, `YamlRegisterBackend` from `kospel_cmi.kospel.backend`
- `HeaterMode`, `ManualMode`, etc. from `kospel_cmi.registers.enums`
- Low-level API functions from `kospel_cmi.kospel.api` (if needed)

**Test failures**: 
- Ensure all test dependencies are installed: `uv sync --group dev`
- Check that test fixtures are properly configured
- Verify environment variables are not interfering with tests

## Documentation

- [Architecture](https://github.com/JanKrl/kospel-cmi-lib/blob/master/docs/architecture.md) — layers, components, and data flow
- [Technical specifications](https://github.com/JanKrl/kospel-cmi-lib/blob/master/docs/technical.md) — data formats, protocols, testing, and coding standards

## References

This library was reverse-engineered from JavaScript code used in the heater's web interface. Key findings:

- Register encoding uses little-endian byte order
- Flag bits are used for boolean settings within registers
- Temperature and pressure values are scaled for precision
- Read-Modify-Write pattern is required for setting flag bits

## License

Apache License 2.0

## Links

- [Repository](https://github.com/JanKrl/kospel-cmi-lib)
