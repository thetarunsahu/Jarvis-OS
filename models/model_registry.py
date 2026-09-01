from providers.ollama_provider import OllamaProvider
from providers.openai_provider import OpenAIProvider


class ModelRegistry:
    """Lazy registry for AI providers used by JARVIS.

    The rest of the application talks to provider names through this
    registry instead of instantiating model clients directly.
    """

    def __init__(self):
        self._factories = {
            "ollama": OllamaProvider,
            "openai": OpenAIProvider,
        }
        self._instances = {}

    def register(self, name, provider_factory):
        key = name.lower().strip()
        self._factories[key] = provider_factory
        self._instances.pop(key, None)

    def get(self, name):
        key = name.lower().strip()

        if key not in self._factories:
            raise KeyError(f"Unknown AI provider: {name}")

        if key not in self._instances:
            self._instances[key] = self._factories[key]()

        return self._instances[key]

    def names(self):
        return list(self._factories.keys())

    def configured(self):
        providers = []

        for name in self.names():
            provider = self.get(name)
            if provider.is_available:
                providers.append(name)

        return providers
