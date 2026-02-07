"""Unit tests for registers.decoders."""

import pytest

from kospel_cmi.registers.decoders import (
    decode_heater_mode,
    decode_bit_boolean,
    decode_map,
    decode_scaled_temp,
    decode_scaled_pressure,
)
from kospel_cmi.registers.enums import HeaterMode, ManualMode


class TestDecodeHeaterMode:
    """Tests for decode_heater_mode (register 0b55, bits 3 and 5)."""

    @pytest.mark.parametrize(
        ("hex_val", "expected"),
        [
            # Summer: bit 3=1, bit 5=0. Value with bit 3 set: 1<<3 = 8. "0800" = 8 in LE
            ("0800", HeaterMode.SUMMER),
            # Winter: bit 3=0, bit 5=1. 1<<5 = 32. "2000" = 32 in LE
            ("2000", HeaterMode.WINTER),
            # Off: bits 3 and 5 both 0
            ("0000", HeaterMode.OFF),
            ("d700", HeaterMode.OFF),  # 215 has no bits 3 or 5 set
        ],
    )
    def test_valid_hex_returns_heater_mode(
        self, hex_val: str, expected: HeaterMode
    ) -> None:
        """Valid 4-char hex decodes to correct HeaterMode."""
        assert decode_heater_mode(hex_val) == expected

    @pytest.mark.parametrize(
        "invalid",
        [None, "", "00", "00000", "ghij"],
    )
    def test_invalid_hex_returns_none(self, invalid: str) -> None:
        """None, wrong length, or non-hex returns None."""
        assert decode_heater_mode(invalid) is None


class TestDecodeBitBoolean:
    """Tests for decode_bit_boolean (single bit to bool)."""

    def test_requires_bit_index(self) -> None:
        """Raises ValueError when bit_index is None."""
        with pytest.raises(ValueError, match="Bit index is required"):
            decode_bit_boolean("0000", bit_index=None)

    @pytest.mark.parametrize(
        ("hex_val", "bit_index", "expected"),
        [
            ("0100", 0, True),   # bit 0 set in LE "0100" -> 1
            ("0000", 0, False),
            ("0200", 1, True),  # bit 1 set
            ("0000", 1, False),
            ("ffff", 0, True),
            ("ffff", 15, True),
        ],
    )
    def test_valid_hex_returns_bool(
        self, hex_val: str, bit_index: int, expected: bool
    ) -> None:
        """Valid 4-char hex and bit_index return correct bool."""
        assert decode_bit_boolean(hex_val, bit_index) == expected

    @pytest.mark.parametrize(
        "invalid",
        [None, "", "00", "00000", "zzzz"],
    )
    def test_invalid_hex_returns_none(self, invalid: str) -> None:
        """Invalid hex returns None."""
        assert decode_bit_boolean(invalid, 0) is None


class TestDecodeMap:
    """Tests for decode_map (bit to enum true/false)."""

    def test_returns_decoder_callable(self) -> None:
        """decode_map returns a callable that accepts hex_val and bit_index."""
        decoder = decode_map(
            true_value=ManualMode.ENABLED,
            false_value=ManualMode.DISABLED,
        )
        assert callable(decoder)
        # Bit 0 set -> True -> ENABLED
        assert decoder("0100", 0) == ManualMode.ENABLED
        # Bit 0 clear -> False -> DISABLED
        assert decoder("0000", 0) == ManualMode.DISABLED

    def test_invalid_hex_returns_none(self) -> None:
        """When decode_bit_boolean returns None, decode_map returns None."""
        decoder = decode_map(
            true_value=ManualMode.ENABLED,
            false_value=ManualMode.DISABLED,
        )
        assert decoder("", 0) is None


class TestDecodeScaledTemp:
    """Tests for decode_scaled_temp (value / 10)."""

    @pytest.mark.parametrize(
        ("hex_val", "expected"),
        [
            ("0000", 0.0),
            ("e100", 22.5),   # 225 -> 22.5
            ("6400", 10.0),  # 100 -> 10.0
        ],
    )
    def test_valid_hex_returns_temperature(
        self, hex_val: str, expected: float
    ) -> None:
        """Valid 4-char hex decodes to temperature (value/10)."""
        assert decode_scaled_temp(hex_val) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "invalid",
        [None, "", "00", "00000", "ghij"],
    )
    def test_invalid_hex_returns_none(self, invalid: str) -> None:
        """Invalid hex returns None."""
        assert decode_scaled_temp(invalid) is None


class TestDecodeScaledPressure:
    """Tests for decode_scaled_pressure (value / 100)."""

    @pytest.mark.parametrize(
        ("hex_val", "expected"),
        [
            ("0000", 0.0),
            ("f401", 5.0),   # 500 in LE -> 5.0
            ("6400", 1.0),   # 100 in LE -> 1.0
        ],
    )
    def test_valid_hex_returns_pressure(
        self, hex_val: str, expected: float
    ) -> None:
        """Valid 4-char hex decodes to pressure (value/100)."""
        assert decode_scaled_pressure(hex_val) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "invalid",
        [None, "", "00", "00000", "ghij"],
    )
    def test_invalid_hex_returns_none(self, invalid: str) -> None:
        """Invalid hex returns None."""
        assert decode_scaled_pressure(invalid) is None
