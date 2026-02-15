"""Unit tests for HeaterController with mock RegisterBackend."""

import pytest

from kospel_cmi.controller.api import HeaterController
from kospel_cmi.controller.registry import load_registry
from kospel_cmi.registers.enums import HeaterMode

REGISTRY = load_registry("kospel_cmi_standard")


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
        controller = HeaterController(backend=backend, registry=REGISTRY)
        await controller.refresh()
        assert controller.get_setting("heater_mode") is not None

    @pytest.mark.asyncio
    async def test_from_registers_decodes_registry_settings(self) -> None:
        """from_registers decodes only registry registers and fills cache."""
        backend = MockRegisterBackend()
        controller = HeaterController(backend=backend, registry=REGISTRY)
        registers = {"0b55": "d700"}
        controller.from_registers(registers)
        assert "0b55" in controller._register_cache
        assert controller._register_cache["0b55"] == "d700"
        assert controller.get_setting("heater_mode") is not None

    @pytest.mark.asyncio
    async def test_save_writes_modified_register_via_backend(self) -> None:
        """save() encodes pending writes and calls backend.write_register."""
        backend = MockRegisterBackend({"0b55": "d700"})
        controller = HeaterController(backend=backend, registry=REGISTRY)
        controller.from_registers(await backend.read_registers("0b00", 256))
        controller.set_setting("heater_mode", HeaterMode.WINTER)
        success = await controller.save()
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
        controller = HeaterController(backend=backend, registry=REGISTRY)
        await controller.aclose()
        assert backend.aclose_called is True

    @pytest.mark.asyncio
    async def test_aclose_no_op_when_backend_has_no_aclose(self) -> None:
        """aclose() does not raise when backend has no aclose method."""
        backend = MockRegisterBackend()
        controller = HeaterController(backend=backend, registry=REGISTRY)
        await controller.aclose()  # Should not raise

    @pytest.mark.asyncio
    async def test_aclose_idempotent(self) -> None:
        """Calling aclose() multiple times does not raise."""

        class BackendWithAclose(MockRegisterBackend):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.aclose_count = 0

            async def aclose(self) -> None:
                self.aclose_count += 1

        backend = BackendWithAclose()
        controller = HeaterController(backend=backend, registry=REGISTRY)
        await controller.aclose()
        await controller.aclose()
        assert backend.aclose_count == 2  # Both calls forwarded (backend decides idempotency)

    @pytest.mark.asyncio
    async def test_context_manager_returns_self_and_calls_aclose_on_exit(
        self,
    ) -> None:
        """async with HeaterController(...) returns self and calls aclose on exit."""

        class BackendWithAclose(MockRegisterBackend):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.aclose_called = False

            async def aclose(self) -> None:
                self.aclose_called = True

        backend = BackendWithAclose()
        controller = HeaterController(backend=backend, registry=REGISTRY)
        async with controller as ctrl:
            assert ctrl is controller
            assert not backend.aclose_called
        assert backend.aclose_called
