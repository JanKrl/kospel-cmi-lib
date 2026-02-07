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

Use `aiohttp.ClientSession` and `HeaterController` to read and write heater settings:

```python
import asyncio
import aiohttp
from kospel_cmi.controller.api import HeaterController


async def main() -> None:
    api_base_url = "http://192.168.1.1/api/dev/65"  # Replace with your heater URL
    async with aiohttp.ClientSession() as session:
        controller = HeaterController(session, api_base_url)
        await controller.refresh()
        print(controller.heater_mode)  # Access registry-defined settings as attributes
        # controller.heater_mode = "manual"  # Modify (if writable)
        # await controller.save()  # Write pending changes to the device


asyncio.run(main())
```

For offline development, enable the simulator (no HTTP calls):

```python
controller = HeaterController(session, api_base_url, simulation_mode=True)
await controller.refresh()
```

You can also control simulation via the `SIMULATION_MODE` environment variable; see the [technical documentation](https://github.com/JanKrl/kospel-cmi-lib/blob/master/docs/technical.md).

## Documentation

- [Architecture](https://github.com/JanKrl/kospel-cmi-lib/blob/master/docs/architecture.md — layers, components, and data flow
- [Technical specifications](https://github.com/JanKrl/kospel-cmi-lib/blob/master/docs/technical.md) — data formats, protocols, testing, and coding standards

## License

Apache License 2.0

## Links

- [Repository](https://github.com/JanKrl/kospel-cmi-lib)
