import os

from models.model_registry import ModelRegistry
from providers.ai_provider import ProviderError


class ModelRouter:
    """Select an AI provider without coupling JARVIS core to a vendor."""

    def __init__(self, registry=None):
        self.registry = registry or ModelRegistry()
        # JARVIS_PROVIDER is the only routing override. Old AI_PROVIDER values
        # from early prototypes should not silently pin modern JARVIS to cloud.
        self.default_provider = os.getenv("JARVIS_PROVIDER", "auto").lower().strip()
        self.routing_mode = os.getenv(
            "JARVIS_ROUTING_MODE",
            "local_first",
        ).lower().strip()
        self.disabled_providers = {
            item.strip().lower()
            for item in os.getenv("JARVIS_DISABLED_PROVIDERS", "").split(",")
            if item.strip()
        }

    def _candidate_names(self, task, tools=None):
        preferred = task.preferred_provider or self.default_provider
        names = [
            name for name in self.registry.names()
            if name not in self.disabled_providers
        ]

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
            return sorted(names, key=lambda name: (self.registry.get(name).local, name))

        if self.routing_mode == "balanced" and task.complexity >= 4:
            return sorted(names, key=lambda name: (self.registry.get(name).local, name))

        return sorted(names, key=lambda name: (not self.registry.get(name).local, name))

    @staticmethod
    def _friendly_provider_error(name, error):
        text = str(error)
        lowered = text.lower()
        if "credit" in lowered or "insufficient_quota" in lowered or "429" in lowered:
            return f"{name}: unavailable (quota/credits)"
        if "out of memory" in lowered or "unable to allocate" in lowered or "cuda" in lowered:
            return f"{name}: local model did not fit available memory"
        if "connection" in lowered or "connect" in lowered:
            return f"{name}: service is not reachable"
        return f"{name}: request failed"

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
                errors.append(f"{name}: registry error")
                attempts.append({"provider": name, "status": "registry_error", "error": str(error)})
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
                errors.append(self._friendly_provider_error(name, error))
                attempts.append({"provider": name, "status": "provider_error", "error": str(error)})
                continue
            except Exception as error:
                errors.append(f"{name}: unexpected error")
                attempts.append({"provider": name, "status": "unexpected_error", "error": str(error)})
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
            "JARVIS could not reach a usable AI model right now. "
            f"{details}. Direct local commands such as time, system info, "
            "workspace and file search still work."
        )
