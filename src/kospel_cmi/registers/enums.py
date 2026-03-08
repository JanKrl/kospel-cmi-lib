from enum import Enum


class HeaterMode(Enum):
    """Heater operating mode.

    All six modes are mutually exclusive per the manufacturer UI.
    Stored in register 0b55: bit 3=SUMMER, bit 5=WINTER, bit 6=PARTY,
    bit 7=VACATION, bit 9=MANUAL. OFF = all mode bits cleared.
    """

    OFF = "off"
    SUMMER = "summer"  # Water only
    WINTER = "winter"  # Water + radiators
    PARTY = "party"  # Temporary comfort boost
    VACATION = "vacation"  # Reduced heating when away
    MANUAL = "manual"  # Manual temperature override


class WaterHeaterEnabled(Enum):
    """Water heater enabled."""

    ENABLED = "Water heater enabled"  # Water heater is enabled
    DISABLED = "Water heater disabled"  # Water heater is disabled


class ValvePosition(Enum):
    """Valve position."""

    DHW = "DHW"  # Domestic Hot Water
    CO = "CO"  # Central Heating


class PumpStatus(Enum):
    """Pump status."""

    RUNNING = "Running"
    IDLE = "Idle"


# Registry for resolving enum paths from YAML (e.g. "WaterHeaterEnabled.ENABLED" -> WaterHeaterEnabled.ENABLED)
ENUM_REGISTRY: dict[str, type[Enum]] = {
    "HeaterMode": HeaterMode,
    "WaterHeaterEnabled": WaterHeaterEnabled,
    "ValvePosition": ValvePosition,
    "PumpStatus": PumpStatus,
}
