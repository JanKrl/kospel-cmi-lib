# Register System

This module handles encoding and decoding of heater register values.

## Register Format

The heater exposes registers as hexadecimal strings in **little-endian format**:

- **Register Format**: 4-character hex string (e.g., `"d700"`)
- **Byte Order**: Little-endian (bytes swapped)
  - `"d700"` means: bytes are `[0xd7, 0x00]` in memory
  - When read as big-endian: `0x00d7` = 215
- **Value Type**: Signed 16-bit integers (-32768 to 32767)

## Scaled Values

Temperatures and pressures are stored with scaling factors for precision:

- **Temperatures**: Stored ×10 (e.g., 22.5°C → 225 → `"00e1"`)
- **Pressure**: Stored ×100 (e.g., 5.00 bar → 500 → `"01f4"`)

This provides 0.1°C precision for temperatures and 0.01 bar precision for pressure.

## Flag Registers

Some registers use individual bits as flags (specific register addresses may vary per device/version):

### Register 0b55 (System Flags)

- Bit 3: Summer mode
- Bit 4: Water heater enabled
- Bit 5: Winter mode
- Bit 9: Manual mode enabled

**Heater Mode Logic** (register 0b55, bits 3 & 5):
- Summer: Bit 3=1, Bit 5=0
- Winter: Bit 3=0, Bit 5=1
- Off: Bit 3=0, Bit 5=0

### Register 0b51 (Component Status)

- Bit 0: Pump CO running
- Bit 1: Pump circulation running
- Bit 2: Valve position (0=CO, 1=DHW)

## Example Register Values

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

## Implementation

Register encoding/decoding is implemented in:
- `utils.py` - Core utilities (`reg_to_int`, `int_to_reg`, `set_bit`, `get_bit`)
- `decoders.py` - Decoder functions for various register types
- `encoders.py` - Encoder functions for various register types
- `enums.py` - Enum types for semantic values

## Read-Modify-Write Pattern

Flag bits require reading the current register value, modifying the specific bit, and writing back the entire register. This pattern is implemented in the encoder functions to preserve other bits in the register.

## Negative Values

Negative register values are normal for flag registers. The value `-32080` for register `0b55` means bits 8-15 are set, which is expected when multiple flags are enabled.
