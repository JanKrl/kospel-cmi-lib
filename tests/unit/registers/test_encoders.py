"""Unit tests for registers.encoders."""

import pytest

from kospel_cmi.registers.decoders import decode_heater_mode
from kospel_cmi.registers.encoders import (
    encode_heater_mode,
    encode_bit_boolean,
    encode_map,
    encode_scaled_temp,
    encode_scaled_pressure,
)
from kospel_cmi.registers.enums import HeaterMode, ManualMode, WaterHeaterEnabled
from kospel_cmi.registers.utils import reg_to_int, get_bit


class TestEncodeHeaterMode:
    """Tests for encode_heater_mode (read-modify-write bits 3 and 5)."""

    def test_requires_current_hex(self) -> None:
        """Returns None when current_hex is None."""
        assert encode_heater_mode(HeaterMode.SUMMER, current_hex=None) is None

    def test_invalid_current_hex_returns_none(self) -> None:
        """Returns None when current_hex has wrong length or non-hex."""
        assert encode_heater_mode(HeaterMode.SUMMER, current_hex="") is None
        assert encode_heater_mode(HeaterMode.SUMMER, current_hex="00") is None
        assert encode_heater_mode(HeaterMode.SUMMER, current_hex="ghij") is None

    @pytest.mark.parametrize(
        ("value", "current_hex"),
        [
            (HeaterMode.SUMMER, "0000"),
            (HeaterMode.WINTER, "0000"),
            (HeaterMode.OFF, "0000"),
            (HeaterMode.SUMMER, "2000"),  # overwrite winter
            (HeaterMode.WINTER, "0800"),  # overwrite summer
        ],
    )
    def test_encodes_mode_bits(self, value: HeaterMode, current_hex: str) -> None:
        """Encoded hex decodes back to the same HeaterMode (round-trip)."""
        result = encode_heater_mode(value, current_hex=current_hex)
        assert result is not None
        assert decode_heater_mode(result) == value

    def test_preserves_other_bits(self) -> None:
        """Encoding Summer preserves other bits (e.g. bit 9) from current_hex."""
        # Set bit 9 in current: 512 = 1<<9, LE "0002". Encode Summer (bits 3 and 5).
        current = "0002"
        result = encode_heater_mode(HeaterMode.SUMMER, current_hex=current)
        assert result is not None
        assert decode_heater_mode(result) == HeaterMode.SUMMER
        # Bit 9 should still be set (manual mode preserved)
        decoded_int = reg_to_int(result)
        assert get_bit(decoded_int, 9) is True


class TestEncodeBitBoolean:
    """Tests for encode_bit_boolean (single bit read-modify-write)."""

    def test_requires_bit_index(self) -> None:
        """Returns None when bit_index is None."""
        assert encode_bit_boolean(True, bit_index=None, current_hex="0000") is None

    def test_requires_current_hex(self) -> None:
        """Returns None when current_hex is None."""
        assert encode_bit_boolean(True, bit_index=0, current_hex=None) is None

    def test_invalid_current_hex_returns_none(self) -> None:
        """Returns None when current_hex is invalid."""
        assert encode_bit_boolean(True, bit_index=0, current_hex="") is None
        assert encode_bit_boolean(True, bit_index=0, current_hex="ghij") is None

    @pytest.mark.parametrize(
        ("value", "bit_index", "current_hex", "expected_bit"),
        [
            (True, 0, "0000", True),
            (False, 0, "0100", False),
            (True, 5, "0000", True),
            (False, 5, "2000", False),
        ],
    )
    def test_encodes_bit(
        self,
        value: bool,
        bit_index: int,
        current_hex: str,
        expected_bit: bool,
    ) -> None:
        """Encoded hex has correct bit set/clear."""
        result = encode_bit_boolean(value, bit_index=bit_index, current_hex=current_hex)
        assert result is not None
        decoded = reg_to_int(result)
        assert get_bit(decoded, bit_index) == expected_bit


class TestEncodeMap:
    """Tests for encode_map (enum/bool to bit encoder factory)."""

    def test_requires_bit_index(self) -> None:
        """Returns None when bit_index is None."""
        encoder = encode_map(
            true_value=ManualMode.ENABLED,
            false_value=ManualMode.DISABLED,
        )
        assert encoder(ManualMode.ENABLED, bit_index=None, current_hex="0000") is None

    def test_requires_current_hex(self) -> None:
        """Returns None when current_hex is None."""
        encoder = encode_map(
            true_value=ManualMode.ENABLED,
            false_value=ManualMode.DISABLED,
        )
        assert encoder(ManualMode.ENABLED, bit_index=0, current_hex=None) is None

    @pytest.mark.parametrize(
        ("value", "expected_bit"),
        [
            (ManualMode.ENABLED, True),
            (ManualMode.DISABLED, False),
        ],
    )
    def test_enum_to_bit(self, value: ManualMode, expected_bit: bool) -> None:
        """Enum value encodes to correct bit."""
        encoder = encode_map(
            true_value=ManualMode.ENABLED,
            false_value=ManualMode.DISABLED,
        )
        result = encoder(value, bit_index=9, current_hex="0000")
        assert result is not None
        decoded = reg_to_int(result)
        assert get_bit(decoded, 9) == expected_bit

    def test_bool_accepted(self) -> None:
        """Bool value is accepted and encoded."""
        encoder = encode_map(
            true_value=WaterHeaterEnabled.ENABLED,
            false_value=WaterHeaterEnabled.DISABLED,
        )
        result = encoder(True, bit_index=4, current_hex="0000")
        assert result is not None
        decoded = reg_to_int(result)
        assert get_bit(decoded, 4) is True

    def test_unsupported_value_returns_none(self) -> None:
        """Value that is neither enum nor bool returns None."""
        encoder = encode_map(
            true_value=ManualMode.ENABLED,
            false_value=ManualMode.DISABLED,
        )
        assert encoder("invalid", bit_index=0, current_hex="0000") is None


class TestEncodeScaledTemp:
    """Tests for encode_scaled_temp (value * 10)."""

    @pytest.mark.parametrize(
        ("value", "expected_hex_int"),
        [
            (0.0, 0),
            (22.5, 225),
            (10.0, 100),
        ],
    )
    def test_encodes_temperature(self, value: float, expected_hex_int: int) -> None:
        """Temperature is scaled by 10 and encoded as register value."""
        result = encode_scaled_temp(value, bit_index=0)  # bit_index ignored
        assert result is not None
        assert reg_to_int(result) == expected_hex_int

    def test_invalid_returns_none(self) -> None:
        """Non-numeric value returns None."""
        # value * 10 will raise for non-numeric; encoder catches Exception
        assert encode_scaled_temp("not a number", bit_index=0) is None  # type: ignore[arg-type]


class TestEncodeScaledPressure:
    """Tests for encode_scaled_pressure (value * 100)."""

    @pytest.mark.parametrize(
        ("value", "expected_hex_int"),
        [
            (0.0, 0),
            (5.0, 500),
            (1.0, 100),
        ],
    )
    def test_encodes_pressure(self, value: float, expected_hex_int: int) -> None:
        """Pressure is scaled by 100 and encoded as register value."""
        result = encode_scaled_pressure(value, bit_index=0)  # bit_index ignored
        assert result is not None
        assert reg_to_int(result) == expected_hex_int

    def test_invalid_returns_none(self) -> None:
        """Non-numeric value returns None."""
        assert encode_scaled_pressure("not a number", bit_index=0) is None  # type: ignore[arg-type]
