"""Unit tests for Ekco_M3 with mock RegisterBackend."""

import pytest

from kospel_cmi.controller.device import Ekco_M3
from kospel_cmi.registers.enums import CwuMode, HeaterMode, HeatingStatus


class MockRegisterBackend:
    """Mock backend that returns fixed register data."""

    def __init__(self, registers: dict[str, str] | None = None) -> None:
        self.registers = registers or {}
        self.writes: list[tuple[str, str]] = []

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
        self.writes.append((register, hex_value))
        self.registers[register] = hex_value
        return True


class TestEkco_M3:
    """Ekco_M3 using MockRegisterBackend."""

    @pytest.mark.asyncio
    async def test_refresh_populates_registers_from_backend(self) -> None:
        """refresh() calls backend.read_registers and populates _registers."""
        backend = MockRegisterBackend({"0b55": "d700"})
        controller = Ekco_M3(backend=backend)
        await controller.refresh()
        assert controller.heater_mode is not None

    @pytest.mark.asyncio
    async def test_from_registers_loads_data(self) -> None:
        """from_registers loads register data into cache."""
        backend = MockRegisterBackend()
        controller = Ekco_M3(backend=backend)
        registers = {"0b55": "d700"}
        controller.from_registers(registers)
        assert "0b55" in controller._registers
        assert controller._registers["0b55"] == "d700"
        assert controller.heater_mode is not None

    @pytest.mark.asyncio
    async def test_set_heater_mode_writes_immediately(self) -> None:
        """set_heater_mode writes to backend immediately."""
        backend = MockRegisterBackend({"0b55": "d700"})
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        success = await controller.set_heater_mode(HeaterMode.WINTER)
        assert success is True
        assert backend.registers.get("0b55") is not None

    @pytest.mark.asyncio
    async def test_aclose_calls_backend_aclose_when_present(self) -> None:
        """aclose() calls backend.aclose() when backend has aclose method."""

        class BackendWithAclose(MockRegisterBackend):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.aclose_called = False

            async def aclose(self) -> None:
                self.aclose_called = True

        backend = BackendWithAclose()
        controller = Ekco_M3(backend=backend)
        await controller.aclose()
        assert backend.aclose_called is True

    @pytest.mark.asyncio
    async def test_aclose_no_op_when_backend_has_no_aclose(self) -> None:
        """aclose() does not raise when backend has no aclose method."""
        backend = MockRegisterBackend()
        controller = Ekco_M3(backend=backend)
        await controller.aclose()  # Should not raise

    @pytest.mark.asyncio
    async def test_context_manager_returns_self_and_calls_aclose_on_exit(
        self,
    ) -> None:
        """async with Ekco_M3(...) returns self and calls aclose on exit."""

        class BackendWithAclose(MockRegisterBackend):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.aclose_called = False

            async def aclose(self) -> None:
                self.aclose_called = True

        backend = BackendWithAclose()
        controller = Ekco_M3(backend=backend)
        async with controller as ctrl:
            assert ctrl is controller
            assert not backend.aclose_called
        assert backend.aclose_called

    @pytest.mark.asyncio
    async def test_set_heater_mode_manual_writes_room_mode(self) -> None:
        """When set_heater_mode(MANUAL), write_register is called for 0b55 and 0b32."""
        backend = MockRegisterBackend({"0b55": "d700", "0b32": "0100"})
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        success = await controller.set_heater_mode(HeaterMode.MANUAL)
        assert success is True
        written_registers = {r for r, _ in backend.writes}
        assert "0b55" in written_registers
        assert "0b32" in written_registers
        assert backend.registers["0b32"] == "4000"  # 64 in little-endian

    @pytest.mark.asyncio
    async def test_set_heater_mode_manual_returns_false_when_room_mode_write_fails(
        self,
    ) -> None:
        """When set_heater_mode(MANUAL) and set_room_mode fails, return False."""
        backend = MockRegisterBackend({"0b55": "d700", "0b32": "0100"})

        async def write_register(register: str, hex_value: str) -> bool:
            if register == "0b32":
                return False
            backend.registers[register] = hex_value
            backend.writes.append((register, hex_value))
            return True

        backend.write_register = write_register  # type: ignore[method-assign]
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        success = await controller.set_heater_mode(HeaterMode.MANUAL)
        assert success is False

    @pytest.mark.asyncio
    async def test_set_manual_temperature_writes_only(self) -> None:
        """set_manual_temperature writes only 0b8d."""
        backend = MockRegisterBackend({"0b8d": "c800", "0b32": "0100"})
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        success = await controller.set_manual_temperature(23.0)
        assert success is True
        written_registers = {r for r, _ in backend.writes}
        assert "0b8d" in written_registers
        assert "0b32" not in written_registers

    @pytest.mark.asyncio
    async def test_set_manual_heating_writes_mode_and_temp_registers(
        self,
    ) -> None:
        """set_manual_heating sets heater_mode, manual_temperature, room_mode."""
        backend = MockRegisterBackend({"0b55": "d700", "0b8d": "c800", "0b32": "0100"})
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        success = await controller.set_manual_heating(22.0)
        assert success is True
        written_registers = {r for r, _ in backend.writes}
        assert "0b55" in written_registers
        assert "0b8d" in written_registers
        assert "0b32" in written_registers
        assert backend.registers["0b32"] == "4000"

    @pytest.mark.asyncio
    async def test_set_water_mode_writes_mode_only(
        self,
    ) -> None:
        """set_water_mode sets cwu_mode only (0b30)."""
        backend = MockRegisterBackend({"0b30": "0100"})
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        success = await controller.set_water_mode(CwuMode.COMFORT)
        assert success is True
        written_registers = {r for r, _ in backend.writes}
        assert written_registers == {"0b30"}
        assert backend.registers["0b30"] == "0200"  # 2 in little-endian

    @pytest.mark.asyncio
    async def test_set_water_mode_raises_on_invalid_type(self) -> None:
        """set_water_mode raises TypeError when mode is not CwuMode."""
        backend = MockRegisterBackend({"0b30": "0100"})
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        with pytest.raises(TypeError, match="mode must be CwuMode"):
            await controller.set_water_mode(2)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_set_water_comfort_temperature_writes_temp_only(
        self,
    ) -> None:
        """set_water_comfort_temperature sets cwu_temperature_comfort only (0b67)."""
        backend = MockRegisterBackend({"0b30": "0200", "0b67": "6801"})
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        success = await controller.set_water_comfort_temperature(38.0)
        assert success is True
        written_registers = {r for r, _ in backend.writes}
        assert written_registers == {"0b67"}
        assert backend.registers["0b67"] == "7c01"  # 38.0 in little-endian

    @pytest.mark.asyncio
    async def test_set_water_economy_temperature_writes_temp_only(
        self,
    ) -> None:
        """set_water_economy_temperature sets cwu_temperature_economy only (0b66)."""
        backend = MockRegisterBackend({"0b30": "0000", "0b66": "6801"})
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        success = await controller.set_water_economy_temperature(35.0)
        assert success is True
        written_registers = {r for r, _ in backend.writes}
        assert written_registers == {"0b66"}
        assert backend.registers["0b66"] == "5e01"  # 35.0 in little-endian

    @pytest.mark.asyncio
    async def test_co_heating_status_summer_disabled(self) -> None:
        """In summer mode, CO is always DISABLED."""
        backend = MockRegisterBackend(
            {"0b55": "0800", "0b51": "0000", "0b46": "0000"}
        )
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        assert controller.co_heating_status == HeatingStatus.DISABLED

    @pytest.mark.asyncio
    async def test_co_heating_status_winter_running(self) -> None:
        """In winter mode with co=1 and power>0, CO is RUNNING."""
        backend = MockRegisterBackend(
            {"0b55": "2000", "0b51": "8000", "0b46": "5000"}
        )
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        assert controller.co_heating_status == HeatingStatus.RUNNING

    @pytest.mark.asyncio
    async def test_co_heating_status_winter_idle(self) -> None:
        """In winter mode with co=1 and power=0, CO is IDLE."""
        backend = MockRegisterBackend(
            {"0b55": "2000", "0b51": "8000", "0b46": "0000"}
        )
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        assert controller.co_heating_status == HeatingStatus.IDLE

    @pytest.mark.asyncio
    async def test_cwu_heating_status_summer_running(self) -> None:
        """In summer mode with cwu=1, CWU is RUNNING (no power check)."""
        backend = MockRegisterBackend(
            {"0b55": "0800", "0b51": "0001", "0b46": "0000"}
        )
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        assert controller.cwu_heating_status == HeatingStatus.RUNNING

    @pytest.mark.asyncio
    async def test_cwu_heating_status_summer_idle(self) -> None:
        """In summer mode with cwu=0, CWU is IDLE."""
        backend = MockRegisterBackend(
            {"0b55": "0800", "0b51": "0000", "0b46": "0000"}
        )
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        assert controller.cwu_heating_status == HeatingStatus.IDLE

    @pytest.mark.asyncio
    async def test_cwu_heating_status_winter_running(self) -> None:
        """In winter with water enabled, cwu=1, power>0, CWU is RUNNING."""
        backend = MockRegisterBackend(
            {"0b55": "3000", "0b51": "0001", "0b46": "5000"}
        )
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        assert controller.cwu_heating_status == HeatingStatus.RUNNING

    @pytest.mark.asyncio
    async def test_cwu_heating_status_winter_disabled_when_water_off(self) -> None:
        """In winter with water disabled, CWU is DISABLED."""
        backend = MockRegisterBackend(
            {"0b55": "2000", "0b51": "0001", "0b46": "5000"}
        )
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        assert controller.cwu_heating_status == HeatingStatus.DISABLED

    @pytest.mark.asyncio
    async def test_co_cwu_heating_status_other_modes_disabled(self) -> None:
        """In OFF/PARTY/VACATION/MANUAL, both CO and CWU are DISABLED."""
        backend = MockRegisterBackend(
            {"0b55": "0000", "0b51": "8001", "0b46": "5000"}
        )
        controller = Ekco_M3(backend=backend)
        controller.from_registers(await backend.read_registers("0b00", 256))
        assert controller.co_heating_status == HeatingStatus.DISABLED
        assert controller.cwu_heating_status == HeatingStatus.DISABLED
