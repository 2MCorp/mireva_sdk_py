"""Client-side exceptions for MIREVA SDK."""


class MirevaException(Exception):
    """Base error for SDK operations."""


class MirevaConnectionError(MirevaException):
    """Cannot reach mireva_serve."""


class MirevaAuthenticationError(MirevaException):
    """Invalid or missing API key."""


class MirevaValidationError(MirevaException):
    """Server rejected input schema or preprocessing."""

    def __init__(self, message: str, detail: object | None = None) -> None:
        super().__init__(message)
        self.detail = detail


class MirevaTimeoutError(MirevaException):
    """Request exceeded timeout."""


class MirevaModelError(MirevaException):
    """Inference failed or unknown model version on the server."""
