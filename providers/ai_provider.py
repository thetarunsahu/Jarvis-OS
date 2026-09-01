class ProviderError(RuntimeError):
    """Raised when an AI provider cannot complete a request."""


class AIProvider:
    """Common contract for every model provider used by JARVIS."""

    name = "unknown"
    status = "NOT_CONFIGURED"
    local = False
    supports_tools = False

    @property
    def is_available(self):
        return self.status not in {"NOT_CONFIGURED", "UNAVAILABLE"}

    def generate(
        self,
        user_input,
        context=None,
        tools=None,
        executor=None,
    ):
        raise NotImplementedError(
            "AI provider is not connected yet."
        )
