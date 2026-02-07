%% Project Architecture: kospel-cmi-lib
%% Communication layer for Kospel C.MI electric heater module.
%% Direction: Consumer → Controller → Kospel (API or Simulator) → Device / Env.

%% =============================================================================
%% Diagram 1: Full system — layers, external actors, data flow (primary view)
%% =============================================================================


```mermaid
flowchart TB
    subgraph External["External"]
        Consumer["Consumer\n(Home Assistant / CLI / Tests)"]
        Device["Kospel C.MI Device\n(HTTP API)"]
        Env["Environment\n(SIMULATION_MODE, SIMULATION_STATE_FILE)"]
    end

    subgraph Controller["Layer: Controller (High-level API)"]
        direction TB
        HC["HeaterController\n(api.py)"]
        Reg["SETTINGS_REGISTRY\n(registry.py)"]
        SD["SettingDefinition\n(register, decode, encode)"]
        HC --> Reg
        Reg --> SD
    end

    subgraph Kospel["Layer: Kospel (Transport & Simulator)"]
        direction TB
        API["api.py\nread_register, read_registers\nwrite_register, write_flag_bit"]
        Sim["simulator.py\nwith_simulator, SimulatorRegisterState\nsimulator_* implementations"]
        API -.->|"simulation_mode"| Sim
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
    HC -->|"read_registers, read_register, write_register"| API
    API -->|"reg_to_int, int_to_reg, set_bit"| Utils
    API -->|"session, api_base_url"| Device
    Sim -->|"persist/load state"| Utils
    Sim --> Env

    style Controller fill:#e1f5fe
    style Kospel fill:#fff3e0
    style Registers fill:#e8f5e9
    style External fill:#f5f5f5
```

%% =============================================================================
%% Diagram 2: Package dependencies only (controller → kospel → registers)
%% =============================================================================
```mermaid
flowchart LR
    subgraph L1["controller"]
        api["api.py\nHeaterController"]
        registry["registry.py\nSETTINGS_REGISTRY"]
    end
    subgraph L2["kospel"]
        kapi["api.py"]
        sim["simulator.py"]
    end
    subgraph L3["registers"]
        dec["decoders"]
        enc["encoders"]
        enums["enums"]
        utils["utils"]
    end
    api --> kapi
    api --> registry
    registry --> dec
    registry --> enc
    registry --> enums
    kapi --> utils
    kapi -.-> sim
    sim --> utils
```