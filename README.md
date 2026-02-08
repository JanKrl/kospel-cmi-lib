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

**Alternative: explicit `aclose()`** (for long-lived integrations like Home Assistant):

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

## Documentation

- [Architecture](https://github.com/JanKrl/kospel-cmi-lib/blob/master/docs/architecture.md — layers, components, and data flow
- [Technical specifications](https://github.com/JanKrl/kospel-cmi-lib/blob/master/docs/technical.md) — data formats, protocols, testing, and coding standards

## License

Apache License 2.0

## Links

- [Repository](https://github.com/JanKrl/kospel-cmi-lib)
