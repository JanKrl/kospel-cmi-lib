# Registry Configuration

Settings are defined in YAML config files and loaded via `load_registry(name)`.
Each config maps semantic setting names to their register locations and decode/encode logic.
`HeaterController` uses the loaded registry as the source of truth for all settings.

## Loading a Registry

```python
from kospel_cmi.controller.registry import load_registry, SettingDefinition

# Load from package configs (configs/kospel_cmi_standard.yaml)
registry: dict[str, SettingDefinition] = load_registry("kospel_cmi_standard")

# Pass to HeaterController
from kospel_cmi.controller.api import HeaterController
controller = HeaterController(backend=backend, registry=registry)
```

All config files live in `configs/`. To add a new device variant, create a new YAML file (e.g. `kospel_cmi_pro.yaml`) and load it with `load_registry("kospel_cmi_pro")`.

### Async Runtime Note (Home Assistant, asyncio apps)

When called inside a running event loop, `load_registry()` performs blocking file
I/O. Use `async_load_registry()` instead:

```python
from kospel_cmi.controller.registry import async_load_registry

registry = await async_load_registry("kospel_cmi_standard")
```

## YAML Schema

**Simple decoder (no params):**

```yaml
heater_mode:
  register: "0b55"
  decode: heater_mode
  encode: heater_mode
```

**Parameterized decoder (map with enum):**

```yaml
is_water_heater_enabled:
  register: "0b55"
  bit_index: 4
  decode:
    type: map
    true_value: WaterHeaterEnabled.ENABLED
    false_value: WaterHeaterEnabled.DISABLED
  encode:
    type: map
    true_value: WaterHeaterEnabled.ENABLED
    false_value: WaterHeaterEnabled.DISABLED
```

**Read-only (no encode):**

```yaml
pressure:
  register: "0b8a"
  decode: scaled_x100
```

## SettingDefinition Fields

- **`register`** (str): Register address (e.g. `"0b55"`)
- **`decode`** (str or object): Decoder name or `{type: map, true_value, false_value}`
- **`encode`** (optional): Encoder name or map spec; omit for read-only
- **`bit_index`** (optional): Bit index for flag-based settings

## Available Decoders/Encoders

Registered in `registers/decoders.py` and `registers/encoders.py`:

- **heater_mode**: Decode/encode HeaterMode enum (bits 3, 5, 6, 7, 9 for OFF/SUMMER/WINTER/PARTY/VACATION/MANUAL)
- **scaled_x10**: Value ×10 (temperatures, durations, etc.)
- **scaled_x100**: Value ×100 (pressure, flow, etc.)
- **map**: Bit → enum (requires `true_value` and `false_value` as `EnumName.MEMBER`)

## Validation

`load_registry()` validates the YAML with Pydantic. Invalid or incomplete configs
(log errors and) raise `RegistryConfigError`. Fail-fast at load time.

## Usage in HeaterController

The registry is used by:

1. **`HeaterController.from_registers()`**: Decodes settings from fetched register data
2. **`HeaterController.save()`**: Encodes pending writes to register values
3. **`HeaterController.__getattr__` / `__setattr__`**: Dynamic property access for registry settings

## Helper Methods and Mode Coupling

The firmware uses mode registers to select which temperature source is active. The library handles this coupling:

- **CO (heating):** When `heater_mode=MANUAL` is saved, `room_mode` is set to `ROOM_MODE_MANUAL` (64) automatically so the firmware uses `manual_temperature` (0b8d). Use `set_manual_heating(temperature)` or set `heater_mode=MANUAL` before `manual_temperature` and `save()`.
- **CWU (water):** Mode and temperature are separate. Use `set_water_mode(CwuMode)` to switch which temperature is active. Use `set_water_comfort_temperature(temp)` or `set_water_economy_temperature(temp)` to set the respective temperatures. Setting temperature alone does not switch mode.

**Helper methods:**

- `set_manual_heating(temperature)` — manual mode + target temperature
- `set_water_mode(mode: CwuMode)` — CWU mode (ECONOMY, ANTI_FREEZE, COMFORT)
- `set_water_comfort_temperature(temperature)` — CWU comfort temp only
- `set_water_economy_temperature(temperature)` — CWU economy temp only
