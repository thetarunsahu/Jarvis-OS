import os

from models.model_registry import ModelRegistry
from providers.ai_provider import ProviderError


class ModelRouter:
    """Select an AI provider without coupling JARVIS core to a vendor.

    Routing is capability-safe: a task that requires real tool execution is
    never silently sent to a provider that cannot call JARVIS tools.
    """

    def __init__(self, registry=None):
        self.registry = registry or ModelRegistry()
        configured_default = os.getenv(
            "JARVIS_PROVIDER",
            os.getenv("AI_PROVIDER", "auto"),
        )
        self.default_provider = configured_default.lower().strip()
        self.routing_mode = os.getenv(
            "JARVIS_ROUTING_MODE",
            "local_first",
        ).lower().strip()

    def _candidate_names(self, task, tools=None):
        preferred = task.preferred_provider or self.default_provider
        names = self.registry.names()

        # Actionable tasks must keep a real execution path. Returning a fluent
        # answer from a provider without tool support would create false claims.
        if task.requires_tools and tools:
            names = [
                name
                for name in names
                if self.registry.get(name).supports_tools
            ]

        if preferred != "auto":
            if preferred in names:
                return [preferred] + [name for name in names if name != preferred]
            return names

        if self.routing_mode == "cloud_first":
            return sorted(
                names,
                key=lambda name: (
                    self.registry.get(name).local,
                    name,
                ),
            )

        if self.routing_mode == "balanced" and task.complexity >= 4:
            return sorted(
                names,
                key=lambda name: (
                    self.registry.get(name).local,
                    name,
                ),
            )

        # Default: privacy/cost-friendly local-first routing.
        return sorted(
            names,
            key=lambda name: (
                not self.registry.get(name).local,
                name,
            ),
        )

    def generate(self, task, context=None, tools=None, executor=None):
        errors = []
        attempts = []
        candidates = self._candidate_names(task, tools=tools)

        if task.requires_tools and tools and not candidates:
            task.metadata["routing_attempts"] = []
            return (
                "JARVIS could not find a configured AI provider with tool "
                "calling support for this task."
            )

        for name in candidates:
            try:
                provider = self.registry.get(name)
            except Exception as error:
                message = f"{name}: {error}"
                errors.append(message)
                attempts.append({"provider": name, "status": "registry_error"})
                continue

            if not provider.is_available:
                errors.append(f"{name}: not configured")
                attempts.append({"provider": name, "status": "unavailable"})
                continue

            try:
                result = provider.generate(
                    user_input=task.raw_input,
                    context=context,
                    tools=tools if provider.supports_tools else None,
                    executor=executor if provider.supports_tools else None,
                )
            except ProviderError as error:
                errors.append(f"{name}: {error}")
                attempts.append({"provider": name, "status": "provider_error"})
                continue
            except Exception as error:
                errors.append(f"{name}: unexpected error: {error}")
                attempts.append({"provider": name, "status": "unexpected_error"})
                continue

            attempts.append({"provider": name, "status": "success"})
            task.metadata["provider"] = name
            task.metadata["model"] = getattr(provider, "model", None)
            task.metadata["provider_local"] = bool(provider.local)
            task.metadata["routing_mode"] = self.routing_mode
            task.metadata["routing_attempts"] = attempts
            return result

        task.metadata["routing_attempts"] = attempts
        details = "; ".join(errors) if errors else "no providers registered"
        return (
            "JARVIS could not reach an AI provider. "
            f"Provider status: {details}"
        )
