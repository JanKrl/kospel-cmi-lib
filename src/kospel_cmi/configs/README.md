# Registry Configs

Config files define the registry: mapping of setting names to register addresses, decode functions, and encode functions.

## Current Config

- **kospel_cmi_standard.yaml** — Device config for Kospel C.MI standard module

## Loading a Config

```python
from kospel_cmi.controller.registry import load_registry

registry = load_registry("kospel_cmi_standard")  # filename without .yaml
```

## Schema and Examples

For YAML schema, `SettingDefinition` fields, and available decoders/encoders, see [controller/README.md](../controller/README.md).
