"""Unit tests for kospel.backend (RegisterBackend, YamlRegisterBackend, write_flag_bit)."""

from pathlib import Path

import pytest

from kospel_cmi.kospel.backend import YamlRegisterBackend, write_flag_bit


class TestYamlRegisterBackend:
    """Tests for YamlRegisterBackend with temporary state file."""

    @pytest.mark.asyncio
    async def test_read_register_returns_default_when_empty(
        self, tmp_path: Path
    ) -> None:
        """read_register returns '0000' when register not in state."""
        state_file = str(tmp_path / "state.yaml")
        backend = YamlRegisterBackend(state_file=state_file)
        value = await backend.read_register("0b55")
        assert value == "0000"

    @pytest.mark.asyncio
    async def test_write_and_read_register_roundtrip(self, tmp_path: Path) -> None:
        """write_register persists value; read_register returns it."""
        state_file = str(tmp_path / "state.yaml")
        backend = YamlRegisterBackend(state_file=state_file)
        ok = await backend.write_register("0b55", "d700")
        assert ok is True
        value = await backend.read_register("0b55")
        assert value == "d700"

    @pytest.mark.asyncio
    async def test_read_registers_returns_range(
        self, tmp_path: Path
    ) -> None:
        """read_registers returns dict for start_register and count."""
        state_file = str(tmp_path / "state.yaml")
        backend = YamlRegisterBackend(state_file=state_file)
        await backend.write_register("0b00", "0100")
        await backend.write_register("0b01", "0200")
        regs = await backend.read_registers("0b00", 3)
        assert regs.get("0b00") == "0100"
        assert regs.get("0b01") == "0200"
        assert "0b02" in regs
        assert regs["0b02"] == "0000"


class TestWriteFlagBit:
    """Tests for write_flag_bit with mock backend."""

    @pytest.mark.asyncio
    async def test_write_flag_bit_returns_false_when_read_fails(self) -> None:
        """write_flag_bit returns False when backend.read_register returns None."""

        class FailingBackend:
            async def read_register(self, register: str):  # noqa: ANN201
                return None

            async def read_registers(self, start: str, count: int):  # noqa: ANN201
                return {}

            async def write_register(self, register: str, hex_value: str):  # noqa: ANN201
                return True

        result = await write_flag_bit(FailingBackend(), "0b55", 9, True)
        assert result is False

    @pytest.mark.asyncio
    async def test_write_flag_bit_sets_bit_and_writes(self) -> None:
        """write_flag_bit reads, sets bit, writes back; returns True."""

        class RecordingBackend:
            def __init__(self) -> None:
                self.read_register_called: list[str] = []
                self.write_register_called: list[tuple[str, str]] = []

            async def read_register(self, register: str) -> str | None:
                self.read_register_called.append(register)
                return "0000"  # bit 9 = 0

            async def read_registers(self, start: str, count: int) -> dict:
                return {}

            async def write_register(self, register: str, hex_value: str) -> bool:
                self.write_register_called.append((register, hex_value))
                return True

        backend = RecordingBackend()
        result = await write_flag_bit(backend, "0b55", 9, True)
        assert result is True
        assert backend.read_register_called == ["0b55"]
        assert len(backend.write_register_called) == 1
        reg, hex_val = backend.write_register_called[0]
        assert reg == "0b55"
        # 0x0000 with bit 9 set = 0x0200 -> little-endian "0002"
        assert hex_val == "0002"

    @pytest.mark.asyncio
    async def test_write_flag_bit_skips_write_when_bit_unchanged(self) -> None:
        """When bit already in desired state, write_register is not called."""

        class RecordingBackend:
            def __init__(self) -> None:
                self.write_register_called: list[tuple[str, str]] = []

            async def read_register(self, register: str) -> str | None:
                return "0002"  # bit 9 already set

            async def read_registers(self, start: str, count: int) -> dict:
                return {}

            async def write_register(self, register: str, hex_value: str) -> bool:
                self.write_register_called.append((register, hex_value))
                return True

        backend = RecordingBackend()
        result = await write_flag_bit(backend, "0b55", 9, True)
        assert result is True
        assert backend.write_register_called == []
