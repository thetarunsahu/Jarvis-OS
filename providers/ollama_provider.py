import os

import ollama

from providers.ai_provider import AIProvider, ProviderError


class OllamaProvider(AIProvider):
    name = "ollama"
    local = True
    supports_tools = True

    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
        self.fallback_models = [
            item.strip()
            for item in os.getenv(
                "OLLAMA_FALLBACK_MODELS",
                "qwen3:1.7b,qwen3:0.6b",
            ).split(",")
            if item.strip()
        ]
        self.status = "READY"

        self.system_prompt = """
You are JARVIS, a local personal AI assistant.

You have access to tools.

Important rules:
- Use a tool when the user's request requires real system information.
- Never claim that you performed an action unless a tool actually executed it.
- After a tool returns a result, use that result to answer the user.
- For normal conversation, answer directly.
- Keep responses concise unless the user asks for detail.
"""

    @staticmethod
    def _model_name(item):
        if isinstance(item, dict):
            return item.get("model") or item.get("name")
        return getattr(item, "model", None) or getattr(item, "name", None)

    def _installed_models(self):
        try:
            response = ollama.list()
        except Exception:
            return set()

        if isinstance(response, dict):
            models = response.get("models") or []
        else:
            models = getattr(response, "models", None) or []

        result = set()
        for item in models:
            name = self._model_name(item)
            if name:
                result.add(str(name))
        return result

    def _candidate_models(self):
        candidates = []
        for name in [self.model, *self.fallback_models]:
            if name and name not in candidates:
                candidates.append(name)

        installed = self._installed_models()
        if not installed:
            return candidates

        available = [name for name in candidates if name in installed]
        return available or [self.model]

    @staticmethod
    def _is_memory_error(error):
        text = str(error).lower()
        return any(
            marker in text
            for marker in (
                "out of memory",
                "unable to allocate",
                "cuda",
                "memory allocation",
            )
        )

    def _chat_with_fallback(self, messages, tools=None, preferred_model=None):
        candidates = self._candidate_models()
        if preferred_model and preferred_model in candidates:
            candidates.remove(preferred_model)
            candidates.insert(0, preferred_model)

        errors = []
        for model in candidates:
            try:
                response = ollama.chat(
                    model=model,
                    messages=messages,
                    tools=tools or [],
                )
            except Exception as error:
                errors.append((model, error))
                # Memory pressure is exactly where a smaller installed model
                # should be attempted. Other model-specific failures may also
                # recover on the next configured local fallback.
                continue

            self.model = model
            self.status = "READY"
            return response, model

        self.status = "UNAVAILABLE"
        if not errors:
            raise ProviderError("No Ollama model candidates are configured.")

        model, error = errors[-1]
        if any(self._is_memory_error(item[1]) for item in errors):
            raise ProviderError(
                "Ollama models did not fit available memory. "
                "Install or configure a smaller local model such as qwen3:1.7b."
            ) from error
        raise ProviderError(f"Ollama request failed for {model}: {error}") from error

    def generate(
        self,
        user_input,
        context=None,
        tools=None,
        executor=None,
    ):
        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            }
        ]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant JARVIS context:\n{context}",
                }
            )

        messages.append(
            {
                "role": "user",
                "content": "/no_think\n" + user_input,
            }
        )

        response, selected_model = self._chat_with_fallback(
            messages,
            tools=tools or [],
        )

        if not response.message.tool_calls:
            return response.message.content

        messages.append(response.message)

        for tool_call in response.message.tool_calls:
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments or {}

            if executor:
                result = executor(tool_name, arguments)
            else:
                result = "Tool executor is unavailable."

            messages.append(
                {
                    "role": "tool",
                    "content": str(result),
                }
            )

        final_response, _ = self._chat_with_fallback(
            messages,
            preferred_model=selected_model,
        )
        return final_response.message.content
