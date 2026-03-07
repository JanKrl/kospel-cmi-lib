"""Kospel C.MI electric heater HTTP API client."""

from .kospel.discovery import (
    DeviceDetail,
    KospelDeviceInfo,
    discover_devices,
    probe_device,
)

__all__ = [
    "DeviceDetail",
    "KospelDeviceInfo",
    "discover_devices",
    "probe_device",
]
