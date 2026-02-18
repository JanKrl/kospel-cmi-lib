# Reverse-Engineering Tools

Tools for exploring and reverse-engineering heater registers.

## Register Scanner

Scans a range of registers from the device, applies multiple interpretation parsers
(raw int, scaled temperature, scaled pressure, bit flags), and outputs results in
human-readable or YAML format.

### CLI Usage

```bash
# HTTP mode (requires heater on network)
kospel-scan-registers --url http://192.168.1.1/api/dev/65 0b00 256

# YAML mode (offline, uses state file)
kospel-scan-registers --yaml /path/to/state.yaml 0b00 256

# Write to file (YAML format for diffing)
kospel-scan-registers --url http://192.168.1.1/api/dev/65 -o scan.yaml

# Include empty registers (hex 0000)
kospel-scan-registers --url http://192.168.1.1/api/dev/65 --show-empty
```

**Options:**
- `--url URL` - HTTP mode: base URL of the heater API
- `--yaml PATH` - YAML mode: path to state file (for offline development)
- `-o FILE` / `--output FILE` - Write results to file instead of stdout
- `--show-empty` - Include registers with hex 0000 (default: hide them)
- `START_REGISTER` - Starting address (default: 0b00)
- `COUNT` - Number of registers (default: 256)

### Python API

```python
import asyncio
import aiohttp
from kospel_cmi.kospel.backend import HttpRegisterBackend, YamlRegisterBackend
from kospel_cmi.tools import scan_register_range, format_scan_result, serialize_scan_result

async def main():
    async with aiohttp.ClientSession() as session:
        backend = HttpRegisterBackend(session, "http://192.168.1.1/api/dev/65")
        result = await scan_register_range(backend, "0b00", 16)
        print(format_scan_result(result))  # empty registers hidden by default
        yaml_str = serialize_scan_result(result)

asyncio.run(main())
```

### Console Output Format

Table with aligned columns (Register, Hex, Int, °C, bar, Bits). Bits use
`●` = set, `·` = clear for quick visual scanning:

```
Register Scan: 0b00 - 0b0f (16 registers)

Register Hex        Int     °C    bar  Bits
-------- ------ ------- ------ ------  -------------------
0b00     d700       215   21.5   2.15  ···· ···· ●●·● ·●●●
0b01     a401       420   42.0   4.20  ···· ···● ●·●· ·●··
```

### File Output Format (YAML)

When using `-o FILE`, output is YAML for both human and machine use. Designed
for future diff tools that compare two scan files.

**Schema:**

```yaml
format_version: "1"
scan:
  start_register: "0b00"
  count: 256
  timestamp: "2025-02-18T12:00:00Z"
  hide_empty: true      # when empty registers were omitted
  registers_shown: 42   # number of registers in output
registers:
  "0b00":
    hex: "d700"
    raw_int: 215
    scaled_temp: 21.5
    scaled_pressure: 2.15
    bits: {0: true, 1: true, 2: true, 3: false, ...}
  "0b01":
    ...
```

- **format_version**: Allows future tools to detect and handle format changes
- **Registers keyed by address**: Stable, line-oriented diffs
- **Deterministic key order**: Registers sorted by address
- **null** for missing or failed parser results
