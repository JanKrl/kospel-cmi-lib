# Status

- Package restructured to single `kospel_cmi` module; users import via
  `from kospel_cmi.controller.api import HeaterController`
- PyPI publishing ready: uv build backend, Apache-2.0 license, src layout,
  repository URL set to https://github.com/JanKrl/kospel-cmi-lib. Version
  `0.1.0a1` for alpha (PEP 440). Publish with: `uv build` then `uv publish`.
- Pytest testing is set up with unit tests for:
  - `kospel_cmi.registers.utils` (encoding/decoding, bit utilities)
  - `kospel_cmi.registers.decoders` (heater mode, bit boolean, map, scaled temp/pressure)
  - `kospel_cmi.registers.encoders` (heater mode, bit boolean, map, scaled temp/pressure)
  - `kospel_cmi.controller.registry` (SettingDefinition)
