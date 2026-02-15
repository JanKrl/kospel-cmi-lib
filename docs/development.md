# Development Guide

This guide is for contributors and developers working on the kospel-cmi-lib project.

## Adding New Settings

To add a new setting to the heater controller:

### 1. Add to YAML config

Add the setting to `src/kospel_cmi/configs/kospel_cmi_standard.yaml` (or the config you use):

**Simple decoder (no params):**
```yaml
new_setting:
  register: "0b8d"
  decode: scaled_temp
  encode: scaled_temp
```

**Map type (bit → enum):**
```yaml
new_flag:
  register: "0b55"
  bit_index: 10
  decode:
    type: map
    true_value: NewEnum.ENABLED
    false_value: NewEnum.DISABLED
  encode:
    type: map
    true_value: NewEnum.ENABLED
    false_value: NewEnum.DISABLED
```

### 2. Register decoder/encoder (if new)

If the setting uses a **new** decode/encode type, add it to the registries in `registers/`:
- `DECODER_REGISTRY` in `registers/decoders.py`
- `ENCODER_REGISTRY` in `registers/encoders.py`
- `ENUM_REGISTRY` in `registers/enums.py` (for new enums)

For existing types (`scaled_temp`, `scaled_pressure`, `heater_mode`, `map`), no code changes needed—just edit the YAML.

### 3. Add enum (if needed)

Add an enum in `src/kospel_cmi/registers/enums.py` and register it in `ENUM_REGISTRY`:

```python
class NewEnum(Enum):
    ENABLED = "Enabled"
    DISABLED = "Disabled"

ENUM_REGISTRY["NewEnum"] = NewEnum
```

**Note**: Once added to the YAML config, the setting will automatically be available as a dynamic property on `HeaterController` when using a registry loaded from that config.

For more details on the registry system, see [`../src/kospel_cmi/controller/README.md`](../src/kospel_cmi/controller/README.md).

## Best Practices

- **Use high-level API**: Prefer `HeaterController` class over direct register manipulation
- **Batch operations**: Use `HeaterController` class when modifying multiple settings
- **Avoid redundant calls**: Use `from_registers()` when you already have register data
- **Error handling**: Check return values and handle `None` results appropriately
- **Simulator mode**: Use YAML backend for development and testing

## Testing

Automated tests are defined using `pytest` framework. After every set of changes, tests must be run to verify that the library works as expected.

### Test Organization

All tests are defined in `tests/` directory.

### Testing Principles

1. **TDD Approach**: Write tests before or alongside implementation
2. **Layer Isolation**: Test each layer independently
3. **Mock External I/O**: Mock HTTP requests/responses
4. **Coverage Target**: ≥80% code coverage
5. **Async Testing**: Use `pytest-asyncio` for async functions

### Test Types

**Unit Tests**:
- Test individual functions in isolation
- Mock external dependencies
- Test edge cases and error conditions

**Integration Tests**:
- Test cross-layer functionality
- Use mock HTTP responses
- Test end-to-end workflows

**Simulator Mode Tests**:
- Simulator tests should only verify if the simulator itself works as expected
- No end-to-end tests should be defined for cases with and without the simulator

### Running Tests

```bash
# Install test dependencies
uv sync --group dev

# Run all tests
pytest

# Run with coverage
pytest --cov=src/kospel_cmi --cov-report=html
```

## Code Style and Standards

See [`technical.md`](technical.md) for detailed coding standards, including:

- Type hinting requirements
- Documentation standards
- Error handling patterns
- Async programming guidelines

## Architecture

See [`architecture.md`](architecture.md) for system architecture and design patterns.
