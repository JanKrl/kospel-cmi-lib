# Status

- Package restructured to single `kospel_cmi` module; users import via
  `from kospel_cmi.controller.api import HeaterController` and
  `from kospel_cmi.kospel.backend import HttpRegisterBackend, YamlRegisterBackend`.
- Register backend abstraction: `HeaterController(backend, registry)` depends on
  `RegisterBackend` and a registry from `load_registry(name)`; `HttpRegisterBackend` and
  `YamlRegisterBackend` implement the backend. No simulation_mode or env vars.
- YAML registry configuration: Settings defined in `configs/*.yaml`; loaded via
  `load_registry("kospel_cmi_standard")`. Pydantic schema validation; invalid configs raise
  `RegistryConfigError`. One file per device variant.
- PyPI publishing ready: uv build backend, Apache-2.0 license, src layout,
  repository URL set to https://github.com/JanKrl/kospel-cmi-lib. Version
  `0.1.0a2` for alpha (PEP 440). Publish with: `uv build` then `uv publish`.
- GitHub Actions: `.github/workflows/release-pypi.yml` runs on push of tags
  `v*` (e.g. `v0.1.0`). Sets package version from tag, runs tests, builds with
  uv, and publishes to PyPI. Use PyPI Trusted Publishing (recommended) or
  `PYPI_API_TOKEN` secret.
- Pytest testing is set up with unit tests for:
  - `kospel_cmi.registers.utils` (encoding/decoding, bit utilities)
  - `kospel_cmi.registers.decoders` (heater mode, bit boolean, map, scaled temp/pressure)
  - `kospel_cmi.registers.encoders` (heater mode, bit boolean, map, scaled temp/pressure)
  - `kospel_cmi.controller.registry` (SettingDefinition, load_registry, RegistryConfigError)
  - `kospel_cmi.kospel.backend` (YamlRegisterBackend, write_flag_bit)
  - `kospel_cmi.controller.api` (HeaterController with mock RegisterBackend)
  - Resource lifecycle: `HeaterController.aclose()` and `async with HeaterController(...)`
    close HTTP session via `HttpRegisterBackend.aclose()`. YamlRegisterBackend has no
    closeable resources. Unit tests for aclose and context manager in
    `test_backend.py` and `test_heater_controller.py`.
  - `test_config_loader.py`: load_registry, schema validation, RegistryConfigError.
