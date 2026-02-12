# Development Guide

This guide is for contributors and developers working on the kospel-cmi-lib project.

## Adding New Settings

To add a new setting to the heater controller:

### 1. Add to `SETTINGS_REGISTRY`

Add the setting definition to `src/kospel_cmi/controller/registry.py`:

```python
"new_setting": SettingDefinition(
    register="0bXX",
    bit_index=Y,  # If it's a flag bit (omit for full register values)
    decode_function=decode_new_setting_from_reg,
    encode_function=encode_new_setting_to_reg  # Omit for read-only
)
```

### 2. Create decode function

Create a decode function in `src/kospel_cmi/registers/decoders.py` (if needed):

```python
def decode_new_setting_from_reg(reg_hex: str, bit_index: Optional[int] = None) -> Optional[Type]:
    """Decode the setting value from a register hex string."""
    # For flag bits, use decode_bit_boolean or decode_map
    # For full register values, use decode_scaled_temp, decode_scaled_pressure, etc.
```

### 3. Create encode function

Create an encode function in `src/kospel_cmi/registers/encoders.py` (if writable):

```python
def encode_new_setting_to_reg(value: Type, bit_index: Optional[int], current_hex: Optional[str]) -> Optional[str]:
    """Encode the setting value to a register hex string.
    
    Args:
        value: The value to encode (enum, bool, float, etc.)
        bit_index: Bit index if it's a flag bit (None for full register values)
        current_hex: Current hex value of the register (required for read-modify-write)
    """
    # For flag bits: use encode_bit_boolean() or encode_map()
    # For full register values: use int_to_reg() directly
```

### 4. Add enum

Add an enum in `src/kospel_cmi/registers/enums.py` (if needed):

```python
class NewSetting(Enum):
    VALUE1 = "Value 1"
    VALUE2 = "Value 2"
```

**Note**: Once added to `SETTINGS_REGISTRY`, the setting will automatically be available as a dynamic property on `HeaterController`!

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
