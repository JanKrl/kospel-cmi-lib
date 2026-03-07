"""Unit tests for kospel-discover CLI."""

import pytest

from kospel_cmi.kospel.discovery import KospelDeviceInfo
from kospel_cmi.tools.discover import _format_devices


class TestFormatDevices:
    """Tests for _format_devices output."""

    def test_empty_list_returns_no_devices_message(self) -> None:
        """_format_devices returns message when no devices."""
        result = _format_devices([])
        assert "No Kospel" in result
        assert "found" in result

    def test_single_device_formatted(self) -> None:
        """_format_devices formats single device with host, serial, model, url."""
        from kospel_cmi.kospel.discovery import DeviceDetail

        devices = [
            KospelDeviceInfo(
                host="192.168.101.49",
                device_ids=[65],
                serial_number="mi01_00006047",
                api_base_url="http://192.168.101.49/api/dev/65",
                devices=[
                    DeviceDetail(
                        device_id=65,
                        model_id=19,
                        model_name="EKCO.M3",
                        module_id="65",
                    )
                ],
            )
        ]
        result = _format_devices(devices)
        assert "192.168.101.49" in result
        assert "mi01_00006047" in result
        assert "EKCO.M3" in result
        assert "http://192.168.101.49/api/dev/65" in result
        assert "Found 1" in result
