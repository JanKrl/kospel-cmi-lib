# Technical Specifications

This document provides a high-level technical understanding of the Kospel Heater Control Library, including architecture patterns, data formats, protocols, and implementation details.

## Overview

The Kospel Heater Control Library is a Python-based system for controlling Kospel electric heaters via their HTTP REST API. The system follows a strict 3-layer architecture that separates concerns between transport, data parsing and service logic.

**Key Characteristics:**
- **Async-first**: Built on `asyncio` and `aiohttp` for non-blocking I/O
- **Type-safe**: Strict type hinting throughout with no `Any` types
- **Registry-driven**: Settings defined declaratively in a central registry
- **Simulator-capable**: Full simulator implementation for offline development and testing
- **Protocol-based**: Uses Python Protocol types for decoder/encoder interfaces

## Architecture Patterns

### Layered Architecture

The system follows a strict 4-layer architecture with clear boundaries:

```
┌─────────────────────────────────────┐
│ Layer 3: Service (Controller)       │ ← High-level business logic
├─────────────────────────────────────┤
│ Layer 2: Data (Parser)              │ ← Data transformation
├─────────────────────────────────────┤
│ Layer 1: Transport (Client)         │ ← HTTP communication
└─────────────────────────────────────┘
```

**Layer Separation Rules:**
- Each layer only communicates with adjacent layers
- No cross-layer dependencies
- Lower layers are unaware of higher layers
- Higher layers depend on lower layers

### Registry Pattern

> **See also**: For complete registry system documentation, see [`../src/kospel_cmi/controller/README.md`](../src/kospel_cmi/controller/README.md).

Settings are defined in YAML config files and loaded via `load_registry(name)`. The registry maps semantic setting names to `SettingDefinition` (register, decode/encode functions). This pattern enables:

- **Declarative Configuration**: Settings defined in YAML; no hardcoded registry in Python
- **Multiple Configs**: One file per device variant (e.g. `kospel_cmi_standard`, `kospel_cmi_pro`)
- **Schema Validation**: Pydantic validates YAML at load time; invalid configs raise `RegistryConfigError`
- **Automatic Property Generation**: Dynamic properties on `HeaterController`
- **Read-only Enforcement**: Settings without `encode` in YAML are read-only

**Usage:**
```python
registry = load_registry("kospel_cmi_standard")
controller = HeaterController(backend=backend, registry=registry)
```

**Example YAML Entry:**
```yaml
heater_mode:
  register: "0b55"
  decode: heater_mode
  encode: heater_mode
```

### Register Backend (Protocol)

Register read/write is abstracted behind a `RegisterBackend` Protocol. The controller depends only on this interface; it does not know whether data comes from HTTP or from a YAML file.

- **Protocol** (`kospel/backend.py`): `read_register(register)`, `read_registers(start_register, count)`, `write_register(register, hex_value)`. No session, URL, or mode parameters.
- **HttpRegisterBackend(session, api_base_url)**: implements the protocol via HTTP calls to the device.
- **YamlRegisterBackend(state_file: str)**: implements the protocol using a YAML state file; the file path is a required constructor parameter (no environment variable).
- **Construction**: The consumer creates backend and registry separately, then passes both: `HeaterController(backend=..., registry=load_registry("kospel_cmi_standard"))`.
- **write_flag_bit**: Single implementation in `kospel/backend.py` as a **function** that takes the backend as first argument: `write_flag_bit(backend, register, bit_index, state)`. It is not a method on the backend; it uses `backend.read_register` and `backend.write_register`. One implementation for all backends.
- **Why Protocol**: The controller and `write_flag_bit` need “something that can read/write registers”. A Protocol lets any object with the right methods be used. Alternatives (e.g. passing three callables) would require the caller to build closures over `session`/`api_base_url` or `state_file`; the Protocol keeps that state inside the backend object and keeps the interface explicit.

This gives:
- **Single responsibility**: Controller logic is independent of transport.
- **Testability**: Tests can use a mock backend or `YamlRegisterBackend` with a temporary file.
- **No env-based routing**: No `simulation_mode` or env vars in the call chain.

### Protocol-based Type System

Python Protocols are used to define interfaces for decoders and encoders:

```python
class Decoder(Protocol[T]):
    def __call__(self, hex_val: str, bit_index: Optional[int] = None) -> Optional[T]: ...
```

This provides:
- **Structural Typing**: Functions that match the signature are compatible
- **Type Safety**: Type checkers can verify compatibility
- **Flexibility**: No inheritance required

## Data Formats

> **See also**: For detailed register encoding/decoding reference, see [`../src/kospel_cmi/registers/README.md`](../src/kospel_cmi/registers/README.md).

### Register Encoding

**Format**: 4-character hexadecimal string in little-endian byte order

**Internal Representation**: Signed 16-bit integer (-32768 to 32767)

**Encoding Process**:
1. Pack signed integer as 16-bit signed short
2. Unpack as unsigned 16-bit integer (handles two's complement)
3. Format as 4-digit lowercase hex string
4. Swap bytes for little-endian transmission

**Example**:
- Value: `215` (0x00D7)
- Packed: `[0xD7, 0x00]` (little-endian)
- Hex string: `"d700"` (transmitted format)
- Decoding: `"d700"` → swap → `"00d7"` → parse → `215`

**Negative Values**:
- Value: `-32080`
- Two's complement: `33456` (0x82B0)
- Hex string: `"b082"` (bytes swapped: `[0xB0, 0x82]`)

### Scaled Values

Temperatures and pressures are stored with scaling factors for precision:

- **Temperatures**: Stored ×10 (e.g., 22.5°C → 225 → `"00e1"`)
- **Pressure**: Stored ×100 (e.g., 5.00 bar → 500 → `"01f4"`)

This provides 0.1°C precision for temperatures and 0.01 bar precision for pressure.

### Flag Registers

Some registers use individual bits as boolean flags. Flags are accessed via bit manipulation:

**Register 0b55 (System Flags)**:
```
Bit 15  14  13  12  11  10  9   8   7   6   5   4   3   2   1   0
┌──────────────────────────────────────────────────────────────────┐
│                    │    │    │    │Win │Wat │Sum │              │
│                    │    │    │    │Ter │Hea │mer │              │
│                    │Man │    │    │(5) │(4) │(3) │              │
│                    │Mod │    │    │    │    │    │              │
│                    │(9) │    │    │    │    │    │              │
└──────────────────────────────────────────────────────────────────┘
```

**Bit Operations**:
- Read: `(value >> bit_index) & 1`
- Set: `value | (1 << bit_index)`
- Clear: `value & ~(1 << bit_index)`

**Read-Modify-Write Pattern**: Flag bits require reading the current register value, modifying the specific bit, and writing back the entire register.

## Communication Protocol

> **See also**: For detailed HTTP API endpoint reference, see [`../src/kospel_cmi/kospel/README.md`](../src/kospel_cmi/kospel/README.md).

### HTTP API

**Base URL Format**: `http://<HEATER_IP>/api/dev/<DEVICE_ID>`

**Endpoints**:

1. **Read Single Register**:
   - `GET /api/dev/<DEVICE_ID>/<register>/1`
   - Response: `{"regs": {"0b55": "d700"}, "sn": "...", "time": "..."}`

2. **Read Multiple Registers**:
   - `GET /api/dev/<DEVICE_ID>/<start_register>/<count>`
   - Example: `GET /api/dev/65/0b00/256`
   - Response: `{"regs": {"0b00": "...", "0b01": "...", ...}}`

3. **Write Register**:
   - `POST /api/dev/<DEVICE_ID>/<register>`
   - Body: Hex string (e.g., `"d700"`)
   - Content-Type: `application/json`
   - Response: `{"status": "0"}` (0 = success)

**Request/Response Format**:
- All values are hex strings (4 characters)
- Little-endian byte order
- JSON encoding for requests and responses

### Error Handling

**Network Errors**:
- Timeout: 5 seconds (configurable)
- Connection errors: Returns `None` or empty dict
- HTTP errors: Logged and returns `None`/`False`

**Data Errors**:
- Invalid hex strings: Return default value (`0` or `"0000"`)
- Missing registers: Use default empty string `"0000"`
- Parsing errors: Logged and return `None`

**Application Errors**:
- Invalid settings: Raise `AttributeError` with helpful message
- Read-only settings: Raise `AttributeError` on write attempt
- Missing settings: Raise `AttributeError` with available options

## Implementation Details

### Async Programming

**Framework**: `asyncio` with `aiohttp`

**Session Management**:
- `aiohttp.ClientSession` passed explicitly (no global state)
- When using `HttpRegisterBackend`, call `HeaterController.aclose()` when done, or use `async with HeaterController(backend=..., registry=...)` to release the session automatically
- Supports connection pooling and keep-alive

**Function Signatures**:
```python
async def read_register(
    session: aiohttp.ClientSession,
    api_base_url: str,
    register: str
) -> Optional[str]:
```

**Best Practices**:
- All I/O operations are async
- Use `async with` for session management
- Timeout all network operations (default 5s)
- Log errors with context

### Type System

**Type Hints**:
- All function parameters and return types explicitly typed
- Use `Optional[T]` for nullable returns
- Use `Protocol` for structural typing
- Avoid `Any` type (enforced by project rules)

**Type Variables**:
```python
T = TypeVar("T")
Decoder(Protocol[T]): ...
```

**Enum Types**:
- All semantic values use Enum classes
- Enums provide string representations via `.value`
- Type-safe comparisons

### State Management

**HeaterController State**:
- `_settings: Dict[str, Any]`: Decoded setting values
- `_pending_writes: Dict[str, Any]`: Modified settings awaiting save
- `_register_cache: Dict[str, str]`: Cached raw register values

**State Flow**:
1. `refresh()` → Fetch registers → Decode → Store in `_settings`
2. Property access → Return from `_settings`
3. Property write → Store in `_settings` and `_pending_writes`
4. `save()` → Encode pending writes → Write registers → Clear `_pending_writes`

### Batch Operations

**Reading**:
- Use `read_registers()` to fetch multiple registers in one API call
- Parse locally using `from_registers()` method
- Reduces network round-trips

**Writing**:
- Group writes by register address
- Read-modify-write pattern for registers with multiple settings
- Only write if value actually changed

### YAML / simulator (function module)

**Layout**: `kospel/simulator.py` is a **function module** like `api.py`: no classes, only async functions that take `state_file` as the first parameter.

- `read_register(state_file, register) -> str`
- `read_registers(state_file, start_register, count) -> Dict[str, str]`
- `write_register(state_file, register, hex_value) -> bool`

Each call loads from or saves to the YAML file. `YamlRegisterBackend` in `backend.py` holds `state_file` and delegates to these functions.

**State persistence**:
- YAML file path is passed explicitly (no environment variable)
- Load on each read; save after each write
- Same contract as HTTP: controller code is identical for both backends


## Import Rules: Relative Imports Only

**Critical Requirement**: All imports within a Home Assistant custom integration **must** use relative imports (with `.` notation). 

**Correct Import Patterns**:

```python
# ✅ CORRECT: Relative imports within integration
from .kospel.backend import HttpRegisterBackend, YamlRegisterBackend
from .controller.api import HeaterController
from .controller.registry import load_registry
from ..logging_config import get_logger

# Registry: load by name, pass to HeaterController
registry = load_registry("kospel_cmi_standard")
controller = HeaterController(backend=..., registry=registry)

# ❌ INCORRECT: Absolute imports
from kospel.backend import HttpRegisterBackend
from controller.api import HeaterController
from controller.registry import load_registry
from logging_config import get_logger
```

**Import Path Rules**:

1. **Same Package**: Use single dot (`.`) for modules in the same directory
   ```python
   from .backend import RegisterBackend  # kospel/backend.py from kospel/api.py
   ```

2. **Parent Package**: Use double dot (`..`) to go up one level
   ```python
   from ..registers.utils import reg_to_int  # registers/utils.py from kospel/api.py
   ```

3. **Sibling Package**: Use `..` to go up, then specify the sibling path
   ```python
   from ..kospel.api import read_registers  # kospel/api.py from controller/api.py
   ```

**Common Mistakes**:

1. **Forgetting relative notation**: `from kospel.backend import ...` instead of `from .backend import ...`
2. **Wrong level of dots**: Using `.` when you need `..` or vice versa
3. **Mixing absolute and relative**: Some files use relative, others use absolute (inconsistent)


## Design Decisions

### Why Registry Pattern?

**Problem**: Traditional approach requires manually defining properties for each setting.

**Solution**: Registry defines settings declaratively, properties generated automatically.

**Benefits**:
- Add new settings without code changes to `HeaterController`
- Single source of truth for register mappings
- Type safety through associated decode/encode functions

### Why Read-Modify-Write for Flags?

**Problem**: Flag bits share a register with other settings. Writing only the flag would overwrite other values.

**Solution**: Read current register value, modify specific bit(s), write back entire register.

**Implementation**: Encoders accept `current_hex` parameter and return modified hex string.

### Why Little-Endian?

**Constraint**: Heater firmware uses little-endian byte order (determined by reverse engineering).

**Impact**: All encoding/decoding must handle byte swapping correctly.

**Solution**: Centralized utilities in `registers/utils.py` handle byte order consistently.

### Why Scaled Values?

**Problem**: Limited precision with integer-only storage.

**Solution**: Store values scaled (temperatures ×10, pressure ×100).

**Benefits**:
- 0.1°C precision for temperatures
- 0.01 bar precision for pressure
- No floating-point storage issues

### Why Register Backend Abstraction?

**Problem**: Development and testing require physical heater hardware; mixing transport and “simulation mode” in the same functions led to complex parameter passing and env checks.

**Solution**: A `RegisterBackend` Protocol with two implementations—`HttpRegisterBackend(session, api_base_url)` and `YamlRegisterBackend(state_file: str)`. The controller receives a backend at construction; no environment variables or `simulation_mode` in the call chain.

**Benefits**:
- Develop without hardware by using `YamlRegisterBackend(state_file="...")`
- Controller logic identical for HTTP and YAML
- Single place for `write_flag_bit` (function using any backend)
- Configuration via constructor parameters only (URL or state file path)

## Dependencies

### Dependency Management

- **Package Manager**: `uv` (modern Python package manager)
- **Lock File**: `uv.lock` (reproducible builds)

## Testing Strategy

Automated tests are defined using `pytest` framework. After every set of changes, tests must be ran to verify that the library works as expected.

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

## Coding Standards

### Type Hinting

- **Strict Typing**: All functions must have complete type hints
- **No Any**: Avoid `Any` type unless absolutely necessary
- **Protocol Types**: Use for structural typing
- **Optional Returns**: Use `Optional[T]` for nullable returns

### Documentation

- **Google-style Docstrings**: All public classes and methods
- **Parameter Documentation**: Document all parameters and return values
- **Example Usage**: Include examples where helpful
- **Comments and docstrings**: Explain *why*, not *what*

### Error Handling

- **Explicit Handling**: Never pass exceptions silently
- **Custom Exceptions**: Create domain-specific exceptions
- **Logging**: Log errors with context
- **Return Values**: Use `None`/`False` for recoverable errors

### Code Style

- **PEP 8**: Follow Python style guide
- **Ruff**: Automated linting and formatting
- **Line Length**: 88 characters (Black-compatible)
- **Import Organization**: Standard library → third-party → local

## Performance Considerations

### Optimization Strategies

1. **Batch Operations**: Read multiple registers in one API call
2. **Caching**: Cache register values to avoid redundant reads
3. **Lazy Loading**: Only fetch registers when needed
4. **Change Detection**: Only write if value actually changed

### API Call Reduction

**Without Optimization**:
- Reading 5 settings = 5 separate API calls

**With Optimization**:
- Reading 5 settings = 1 batch API call + local parsing

**Example**:
```python
# Fetch all registers once
all_registers = await read_registers(session, api_base_url, "0b00", 256)

# Parse locally (no additional API calls)
heater.from_registers(all_registers)
```

### Memory Considerations

- **Register Cache**: Only cache registers in registry (not all 256)
- **State Persistence**: Mock state persisted to disk, not kept in memory indefinitely
- **Session Pooling**: Reuse HTTP connections via `aiohttp.ClientSession`

## Security Considerations

### Current Limitations

- **No Authentication**: Assumes local network access
- **No Encryption**: HTTP (not HTTPS) communication
- **No Input Validation**: Range checking not implemented (future)

### Recommendations

1. **Network Isolation**: Use on local network only
2. **Input Validation**: Add range checking for settings (future)
3. **HTTPS Support**: Implement if heater firmware supports it (future)

## Future Enhancements

### Planned Features

1. **Custom Exceptions**: Domain-specific error types
2. **Input Validation**: Range checking for temperatures, pressures
3. **Connection Pooling**: Optimize HTTP connection reuse
4. **Device type recognition**: Recognize heater device type

### Technical Debt

1. **Error Handling**: More specific exception types needed
2. **Type Hints**: Some areas could use more comprehensive types
3. **Documentation**: API reference could be auto-generated
4. **Testing**: Comprehensive test suite needed (TDD approach)

## References

- **Architecture Diagram**: See [`architecture.md`](architecture.md)
- **User Guide**: See [`../README.md`](../README.md)
- **Development Guide**: See [`development.md`](development.md)

### Module Documentation

Detailed module-specific documentation is co-located with the code:

- **[kospel/](../src/kospel_cmi/kospel/README.md)** - HTTP API endpoints and protocol
- **[registers/](../src/kospel_cmi/registers/README.md)** - Register encoding, decoding, and mappings
- **[controller/](../src/kospel_cmi/controller/README.md)** - YAML registry config and load_registry

