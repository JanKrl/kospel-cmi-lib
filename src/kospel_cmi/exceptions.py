"""Domain-specific exceptions for the Kospel C.MI library."""


class KospelError(Exception):
    """Base class for all library errors."""


class KospelConnectionError(KospelError):
    """Transport-level failure (network, HTTP, timeout, malformed response)."""


class RegisterReadError(KospelError):
    """Register read succeeded at HTTP level but data is missing or unusable."""


class RegisterMissingError(RegisterReadError):
    """Register key absent from device response, or not loaded in controller cache."""

    def __init__(self, register: str, detail: str | None = None) -> None:
        """Initialize with register id and optional context.

        Args:
            register: Register address (e.g. ``0b55``).
            detail: Extra context (e.g. reason or hint for callers).
        """
        self.register = register
        self.detail = detail
        msg = f"Register {register} is not available"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)


class RegisterValueInvalidError(RegisterReadError):
    """A register value was present but is not a valid 4-character hex string."""


class KospelWriteError(KospelError):
    """Write was rejected by the device or could not be persisted."""


__all__ = [
    "KospelError",
    "KospelConnectionError",
    "RegisterReadError",
    "RegisterMissingError",
    "RegisterValueInvalidError",
    "KospelWriteError",
]
