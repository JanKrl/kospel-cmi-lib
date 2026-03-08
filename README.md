# kospel-cmi-lib

Python client for the Kospel C.MI electric heater HTTP API.

## Features

- **Async-first**: Built on `asyncio` and `aiohttp` for non-blocking I/O
- **Type-safe**: Strict type hinting throughout
- **Registry-driven**: Settings defined declaratively in a central registry; dynamic property access on `HeaterController`
- **Simulator-capable**: Full simulator for offline development and testing (no hardware required)
- **Protocol-based**: Decoder/encoder interfaces via Python `Protocol` types
- **Device discovery**: `probe_device()` and `discover_devices()` to find Kospel devices on the network (no device_id required)

## Installation

```bash
# With uv (recommended)
uv add kospel-cmi-lib

# With pip
pip install kospel-cmi-lib
```

## Usage

Create a register backend (HTTP or YAML), load a registry config, and pass both to `HeaterController`.
When using `HttpRegisterBackend`, call `aclose()` or use the controller as an
async context manager to release the HTTP session when done.

**Recommended: async context manager** (resources released automatically):

```python
import asyncio
import aiohttp
from kospel_cmi.controller.api import HeaterController
from kospel_cmi.controller.registry import load_registry
from kospel_cmi.kospel.backend import HttpRegisterBackend, YamlRegisterBackend


async def main() -> None:
    api_base_url = "http://192.168.1.1/api/dev/65"  # Replace with your heater URL
    registry = load_registry("kospel_cmi_standard")
    async with aiohttp.ClientSession() as session:
        backend = HttpRegisterBackend(session, api_base_url)
        async with HeaterController(backend=backend, registry=registry) as controller:
            await controller.refresh()
            print(controller.heater_mode)  # Access registry-defined settings
            # controller.heater_mode = "manual"  # Modify (if writable)
            # await controller.save()  # Write pending changes to the device
    # Session and controller resources released here


asyncio.run(main())
```

**Alternative: explicit `aclose()`** (for long-lived integrations):

```python
registry = load_registry("kospel_cmi_standard")
controller = HeaterController(backend=HttpRegisterBackend(session, api_base_url), registry=registry)
try:
    await controller.refresh()
    # ... use controller ...
finally:
    await controller.aclose()
```

For offline development or tests, use the YAML backend (no HTTP, no close needed):

```python
registry = load_registry("kospel_cmi_standard")
backend = YamlRegisterBackend(state_file="/path/to/state.yaml")
controller = HeaterController(backend=backend, registry=registry)
await controller.refresh()
```

### Device Discovery

**CLI** — scan network and list devices (no config needed):

```bash
kospel-discover                    # Scans common subnets
kospel-discover 192.168.101.0/24  # Scan specific subnet
```

**Python API**:

```python
import aiohttp
from kospel_cmi import probe_device, discover_devices

async with aiohttp.ClientSession() as session:
    info = await probe_device(session, "192.168.101.49")
    if info:
        print(f"Found: {info.serial_number}, {info.api_base_url}")

    found = await discover_devices(session, "192.168.101.0/24")
    for device in found:
        print(device.host, device.serial_number, device.api_base_url)
```

### Setting Heater Mode

```python
import asyncio
import aiohttp
from kospel_cmi.controller.api import HeaterController
from kospel_cmi.controller.registry import load_registry
from kospel_cmi.kospel.backend import HttpRegisterBackend
from kospel_cmi.registers.enums import CwuMode, HeaterMode

async def main():
    registry = load_registry("kospel_cmi_standard")
    async with aiohttp.ClientSession() as session:
        backend = HttpRegisterBackend(session, "http://192.168.1.1/api/dev/65")
        async with HeaterController(backend=backend, registry=registry) as controller:
            await controller.refresh()

            # Manual heating: mode + temperature in one call (recommended)
            await controller.set_manual_heating(22.0)

            # Or set properties and save
            controller.heater_mode = HeaterMode.WINTER
            controller.manual_temperature = 22.0  # Used when MANUAL mode
            await controller.save()

            # Water: set mode and temperature separately
            await controller.set_water_mode(CwuMode.COMFORT)
            await controller.set_water_comfort_temperature(38.0)
            await controller.set_water_economy_temperature(35.0)

asyncio.run(main())
```

## Documentation

### Module Documentation

Module-specific documentation is co-located with the code (GitHub automatically displays these when browsing directories):

- **[kospel/](src/kospel_cmi/kospel/README.md)** - HTTP API endpoints and protocol
- **[registers/](src/kospel_cmi/registers/README.md)** - Register encoding, decoding, and mappings
- **[controller/](src/kospel_cmi/controller/README.md)** - YAML registry config and load_registry
- **[tools/](src/kospel_cmi/tools/README.md)** - Register scanner and live scanner for reverse-engineering

### Project Documentation

- **[Development Guide](docs/development.md)** - Contributing and extending the library
- **[Architecture](docs/architecture.md)** - System design, layers, components, and data flow
- **[Technical Specs](docs/technical.md)** - Implementation details, data formats, protocols, testing, and coding standards


## Roadmap

### `v1.0.0` Engine & Explorer

1. Local control - basic device functions can be operated using the library
2. Robust interface - an interface for 3rd party tools (i.e., Home Assistant integration)
3. Reverse-engineering toolset - `kospel-scan-registers` and `kospel-scan-live` for exploring registers

### `v2.0.0` Plug & Play for Kospel ecosystem

1. Support multiple device types
2. Device discovery
3. Advanced state management (error and warning flags, fault detection, debug)

## References

This library was reverse-engineered from JavaScript code used in the heater's web interface. Key findings:

- Register encoding uses little-endian byte order
- Flag bits are used for boolean settings within registers
- Temperature and pressure values are scaled for precision
- Read-Modify-Write pattern is required for setting flag bits

## License

Apache License 2.0
