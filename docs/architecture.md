%% Project Architecture: kospel-cmi-lib
%% Communication layer for Kospel C.MI electric heater module.
%% Direction: Consumer → Controller → RegisterBackend (Protocol) → HTTP or YAML.

%% =============================================================================
%% Diagram 1: Full system — layers, external actors, data flow (primary view)
%% =============================================================================
%% Controller depends only on RegisterBackend. No simulation_mode or env vars
%% in the call chain. YAML path and API URL are constructor parameters of backends.

```mermaid
flowchart TB
    subgraph External["External"]
        Consumer["Consumer\n(Home Assistant / CLI / Tests)"]
        Device["Kospel C.MI Device\n(HTTP API)"]
        YamlFile["YAML state file\n(path passed as param)"]
    end

    subgraph Controller["Layer: Controller (High-level API)"]
        direction TB
        HC["HeaterController\n(backend: RegisterBackend)"]
        Reg["SETTINGS_REGISTRY\n(registry.py)"]
        SD["SettingDefinition\n(register, decode, encode)"]
        HC --> Reg
        Reg --> SD
    end

    subgraph BackendLayer["Layer: Register Backend (Protocol + implementations)"]
        direction TB
        Protocol["RegisterBackend Protocol\nread_register, read_registers\nwrite_register"]
        HttpBackend["HttpRegisterBackend\n(session, api_base_url)"]
        YamlBackend["YamlRegisterBackend\n(state_file: str)"]
        WriteFlagBit["write_flag_bit(backend, ...)\nsingle implementation\nuses read_register + write_register"]
        Protocol -.->|implements| HttpBackend
        Protocol -.->|implements| YamlBackend
        WriteFlagBit --> Protocol
    end

    subgraph KospelHTTP["Kospel HTTP (api.py)"]
        API["read_register, read_registers\nwrite_register\nno write_flag_bit"]
    end

    subgraph Registers["Layer: Registers (Encoding/Decoding)"]
        direction TB
        Dec["decoders.py\nDecoder, decode_*"]
        Enc["encoders.py\nEncoder, encode_*"]
        Utils["utils.py\nreg_to_int, int_to_reg\nset_bit, get_bit"]
        Enums["enums.py\nHeaterMode, ManualMode, ..."]
        Dec --> Utils
        Dec --> Enums
        Enc --> Utils
        Enc --> Enums
    end

    Consumer -->|"refresh(), save(), attr access"| HC
    HC -->|"decode/encode via registry"| Reg
    SD -->|"Decoder, Encoder"| Dec
    SD -->|"Decoder, Encoder"| Enc
    HC -->|"read_registers, read_register, write_register"| Protocol
    HttpBackend --> API
    API -->|"session, api_base_url"| Device
    YamlBackend -->|"load/save state"| YamlFile
    WriteFlagBit --> Utils

    style Controller fill:#e1f5fe
    style BackendLayer fill:#fff3e0
    style Registers fill:#e8f5e9
    style External fill:#f5f5f5
```

%% =============================================================================
%% Diagram 2: Package dependencies (controller → kospel → registers)
%% =============================================================================
```mermaid
flowchart LR
    subgraph L1["controller"]
        api["api.py\nHeaterController"]
        registry["registry.py\nSETTINGS_REGISTRY"]
    end
    subgraph L2["kospel"]
        backend["backend.py\nRegisterBackend, HttpBackend\nYamlBackend, write_flag_bit"]
        kapi["api.py\nHTTP only"]
        state["simulator.py\nread_register, read_registers\nwrite_register\n(state_file)"]
    end
    subgraph L3["registers"]
        dec["decoders"]
        enc["encoders"]
        enums["enums"]
        utils["utils"]
    end
    api --> backend
    api --> registry
    registry --> dec
    registry --> enc
    registry --> enums
    backend --> kapi
    backend --> state
    backend --> utils
    kapi --> utils
    state --> utils
```

%% =============================================================================
%% Design: Register backend abstraction
%% =============================================================================
%%
%% - HeaterController(backend: RegisterBackend, registry=...) — no session, no api_base_url, no simulation_mode.
%% - RegisterBackend Protocol: read_register(register), read_registers(start_register, count), write_register(register, hex_value).
%% - HttpRegisterBackend(session, api_base_url): implements Protocol via kospel.api HTTP calls.
%% - YamlRegisterBackend(state_file: str): implements Protocol via file load/save; state_file is a required parameter (no env var).
%% - write_flag_bit: single implementation (e.g. in backend.py), takes any RegisterBackend and uses read_register + set_bit + write_register; not part of Protocol; not duplicated in HTTP or YAML.
%% - No backward compatibility requirement: API is HeaterController(backend=...) only; consumer builds HttpRegisterBackend or YamlRegisterBackend explicitly.

## Architecture summary (for implementation)

- **Controller** (`controller/api.py`): `HeaterController(backend: RegisterBackend, registry=...)`. No `session`, `api_base_url`, or `simulation_mode`. Uses only `backend.read_register`, `backend.read_registers`, `backend.write_register` (and if needed, a standalone `write_flag_bit(backend, ...)`).
- **RegisterBackend Protocol** (`kospel/backend.py`): methods `read_register(register) -> Optional[str]`, `read_registers(start_register, count) -> Dict[str, str]`, `write_register(register, hex_value) -> bool`. No transport-specific parameters.
- **HttpRegisterBackend** (`kospel/backend.py`): constructor `(session: aiohttp.ClientSession, api_base_url: str)`. Implements Protocol by calling the HTTP-only functions from `kospel/api.py` (no decorators, no `simulation_mode`).
- **YamlRegisterBackend** (`kospel/backend.py`): constructor `(state_file: str)` — path required, no environment variable for file location. Implements Protocol using in-memory state and YAML load/save (logic from current `simulator.py` / `SimulatorRegisterState`).
- **write_flag_bit**: Single implementation only (e.g. in `kospel/backend.py`). Signature: accepts a `RegisterBackend` plus `register`, `bit_index`, `state`; implements read-modify-write via `backend.read_register` and `backend.write_register` using `reg_to_int` / `set_bit` / `int_to_reg`. Not a method of the Protocol; not implemented in `kospel/api.py` or duplicated in backends.
- **kospel/api.py**: Contains only HTTP logic: `read_register(session, api_base_url, register)`, `read_registers(...)`, `write_register(...)`. Remove `@with_simulator`, `simulation_mode` parameter, and `write_flag_bit` from this module.
- **kospel/simulator.py**: Function module: `read_register(state_file, register)`, `read_registers(state_file, ...)`, `write_register(state_file, ...)`. No classes; operations load/save the YAML file. Mirrors the structure of `api.py` (functions with “connection” param first).
- **Configuration**: No environment variables for simulation or YAML path. Consumer passes `api_base_url` for HTTP or `state_file` for YAML when constructing the backend.