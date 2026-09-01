import os

from models.model_registry import ModelRegistry
from providers.ai_provider import ProviderError


class ModelRouter:
    """Selects an AI provider without coupling JARVIS core to a model vendor."""

    def __init__(self, registry=None):
        self.registry = registry or ModelRegistry()
        configured_default = os.getenv(
            "JARVIS_PROVIDER",
            os.getenv("AI_PROVIDER", "auto"),
        )
        self.default_provider = configured_default.lower().strip()

    def _candidate_names(self, task, tools=None):
        preferred = task.preferred_provider or self.default_provider
        names = self.registry.names()

        if preferred != "auto":
            ordered = [preferred] + [name for name in names if name != preferred]
        else:
            # Local-first by default. This protects privacy and avoids cloud cost
            # for ordinary requests while preserving cloud fallback.
            ordered = sorted(
                names,
                key=lambda name: (
                    not self.registry.get(name).local,
                    name,
                ),
            )

        # Tool support only changes provider priority when the task actually
        # requires tool execution. Normal conversation still respects the
        # configured provider preference.
        if task.requires_tools and tools:
            ordered = sorted(
                ordered,
                key=lambda name: not self.registry.get(name).supports_tools,
            )

        return ordered

    def generate(self, task, context=None, tools=None, executor=None):
        errors = []

        for name in self._candidate_names(task, tools=tools):
            try:
                provider = self.registry.get(name)
            except Exception as error:
                errors.append(f"{name}: {error}")
                continue

            if not provider.is_available:
                errors.append(f"{name}: not configured")
                continue

            try:
                return provider.generate(
                    user_input=task.raw_input,
                    context=context,
                    tools=tools if provider.supports_tools else None,
                    executor=executor if provider.supports_tools else None,
                )
            except ProviderError as error:
                errors.append(f"{name}: {error}")
            except Exception as error:
                errors.append(f"{name}: unexpected error: {error}")

        details = "; ".join(errors) if errors else "no providers registered"
        return (
            "JARVIS could not reach an AI provider. "
            f"Provider status: {details}"
        )
