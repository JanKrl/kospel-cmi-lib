"""Unit tests for HeaterController with mock RegisterBackend."""

import pytest

from kospel_cmi.controller.api import HeaterController
from kospel_cmi.registers.enums import HeaterMode


class MockRegisterBackend:
    """Mock backend that returns fixed register data."""

    def __init__(self, registers: dict[str, str] | None = None) -> None:
        self.registers = registers or {}

    async def read_register(self, register: str) -> str | None:
        return self.registers.get(register, "0000")

    async def read_registers(self, start_register: str, count: int) -> dict[str, str]:
        from kospel_cmi.registers.utils import reg_address_to_int

        result: dict[str, str] = {}
        start_int = reg_address_to_int(start_register)
        prefix = start_register[:2]
        for i in range(count):
            reg_int = start_int + i
            reg_str = f"{prefix}{reg_int:02x}"
            result[reg_str] = self.registers.get(reg_str, "0000")
        return result

    async def write_register(self, register: str, hex_value: str) -> bool:
        self.registers[register] = hex_value
        return True


class TestHeaterControllerWithMockBackend:
    """HeaterController using MockRegisterBackend (no HTTP, no files)."""

    @pytest.mark.asyncio
    async def test_refresh_populates_settings_from_backend(self) -> None:
        """refresh() calls backend.read_registers and decodes into _settings."""
        backend = MockRegisterBackend(
            {"0b55": "d700"}
        )
        controller = HeaterController(backend=backend)
        await controller.refresh()
        assert controller.get_setting("heater_mode") is not None

    @pytest.mark.asyncio
    async def test_from_registers_decodes_registry_settings(self) -> None:
        """from_registers decodes only registry registers and fills cache."""
        backend = MockRegisterBackend()
        controller = HeaterController(backend=backend)
        registers = {"0b55": "d700"}
        controller.from_registers(registers)
        assert "0b55" in controller._register_cache
        assert controller._register_cache["0b55"] == "d700"
        assert controller.get_setting("heater_mode") is not None

    @pytest.mark.asyncio
    async def test_save_writes_modified_register_via_backend(self) -> None:
        """save() encodes pending writes and calls backend.write_register."""
        backend = MockRegisterBackend({"0b55": "d700"})
        controller = HeaterController(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        controller.set_setting("heater_mode", HeaterMode.WINTER)
        success = await controller.save()
        assert success is True
        assert backend.registers.get("0b55") is not None
