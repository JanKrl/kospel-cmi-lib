"""Kospel C.MI electric heater HTTP API client."""

from .kospel.discovery import (
    DeviceDetail,
    KospelDeviceInfo,
    MODEL_NAMES,
    discover_devices,
    probe_device,
)

__all__ = [
    "DeviceDetail",
    "KospelDeviceInfo",
    "MODEL_NAMES",
    "discover_devices",
    "probe_device",
]
