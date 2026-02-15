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
is_manual_mode_enabled:
  register: "0b55"
  bit_index: 9
  decode:
    type: map
    true_value: ManualMode.ENABLED
    false_value: ManualMode.DISABLED
  encode:
    type: map
    true_value: ManualMode.ENABLED
    false_value: ManualMode.DISABLED
```

**Read-only (no encode):**

```yaml
pressure:
  register: "0b8a"
  decode: scaled_pressure
```

## SettingDefinition Fields

- **`register`** (str): Register address (e.g. `"0b55"`)
- **`decode`** (str or object): Decoder name or `{type: map, true_value, false_value}`
- **`encode`** (optional): Encoder name or map spec; omit for read-only
- **`bit_index`** (optional): Bit index for flag-based settings

## Available Decoders/Encoders

Registered in `registers/decoders.py` and `registers/encoders.py`:

- **heater_mode**: Decode/encode HeaterMode enum (bits 3, 5)
- **scaled_temp**: Temperature ×10
- **scaled_pressure**: Pressure ×100
- **map**: Bit → enum (requires `true_value` and `false_value` as `EnumName.MEMBER`)

## Validation

`load_registry()` validates the YAML with Pydantic. Invalid or incomplete configs
(log errors and) raise `RegistryConfigError`. Fail-fast at load time.

## Usage in HeaterController

The registry is used by:

1. **`HeaterController.from_registers()`**: Decodes settings from fetched register data
2. **`HeaterController.save()`**: Encodes pending writes to register values
3. **`HeaterController.__getattr__` / `__setattr__`**: Dynamic property access for registry settings
