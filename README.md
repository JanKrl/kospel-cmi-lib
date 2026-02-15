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

### Setting Heater Mode

```python
import asyncio
import aiohttp
from kospel_cmi.controller.api import HeaterController
from kospel_cmi.controller.registry import load_registry
from kospel_cmi.kospel.backend import HttpRegisterBackend
from kospel_cmi.registers.enums import HeaterMode, ManualMode

async def main():
    registry = load_registry("kospel_cmi_standard")
    async with aiohttp.ClientSession() as session:
        backend = HttpRegisterBackend(session, "http://192.168.1.1/api/dev/65")
        async with HeaterController(backend=backend, registry=registry) as controller:
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

## Documentation

### Module Documentation

Module-specific documentation is co-located with the code (GitHub automatically displays these when browsing directories):

- **[kospel/](src/kospel_cmi/kospel/README.md)** - HTTP API endpoints and protocol
- **[registers/](src/kospel_cmi/registers/README.md)** - Register encoding, decoding, and mappings
- **[controller/](src/kospel_cmi/controller/README.md)** - YAML registry config and load_registry

### Project Documentation

- **[Development Guide](docs/development.md)** - Contributing and extending the library
- **[Architecture](docs/architecture.md)** - System design, layers, components, and data flow
- **[Technical Specs](docs/technical.md)** - Implementation details, data formats, protocols, testing, and coding standards

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
