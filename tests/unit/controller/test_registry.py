"""Unit tests for controller.registry (SettingDefinition and SETTINGS_REGISTRY)."""

import pytest

from kospel_cmi.controller.registry import SettingDefinition
from kospel_cmi.registers.enums import HeaterMode


class TestSettingDefinition:
    """Tests for SettingDefinition dataclass and methods."""

    def test_is_read_only_when_no_encode_function(self) -> None:
        """is_read_only is True when encode_function is None."""
        read_only = SettingDefinition(
            register="0b51",
            decode_function=lambda h, bi=None: True,
            encode_function=None,
        )
        assert read_only.is_read_only is True

    def test_is_read_only_false_when_encode_function_set(self) -> None:
        """is_read_only is False when encode_function is set."""
        writable = SettingDefinition(
            register="0b55",
            decode_function=lambda h, bi=None: HeaterMode.OFF,
            encode_function=lambda v, bi=None, ch=None: "0000",
        )
        assert writable.is_read_only is False

    def test_decode_invokes_decode_function_with_bit_index(self) -> None:
        """decode(hex_val) calls decode_function with hex_val and bit_index."""
        received: list[tuple[str, int | None]] = []

        def capture(hex_val: str, bit_index: int | None = None) -> str:
            received.append((hex_val, bit_index))
            return "decoded"

        setting = SettingDefinition(
            register="0b55",
            decode_function=capture,
            bit_index=9,
        )
        result = setting.decode("0800")
        assert result == "decoded"
        assert received == [("0800", 9)]

    def test_encode_raises_when_read_only(self) -> None:
        """encode raises ValueError when setting is read-only."""
        setting = SettingDefinition(
            register="0b51",
            decode_function=lambda h, bi=None: None,
            encode_function=None,
        )
        with pytest.raises(ValueError, match="read-only"):
            setting.encode(True)

    def test_encode_invokes_encode_function_when_writable(self) -> None:
        """encode(value, current_hex) calls encode_function with value and current_hex."""
        received: list[tuple[str, int | None, str | None]] = []

        def capture(
            value: str,
            bit_index: int | None = None,
            current_hex: str | None = None,
        ) -> str:
            received.append((value, bit_index, current_hex))
            return "f401"

        setting = SettingDefinition(
            register="0b8d",
            decode_function=lambda h, bi=None: 0.0,
            encode_function=capture,
            bit_index=None,
        )
        result = setting.encode(50.0, current_hex="0000")
        assert result == "f401"
        assert received == [(50.0, None, "0000")]
