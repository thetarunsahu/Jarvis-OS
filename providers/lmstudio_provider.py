import os

from openai import OpenAI

from providers.ai_provider import AIProvider, ProviderError


class LMStudioProvider(AIProvider):
    """Local LM Studio provider through its OpenAI-compatible API."""

    name = "lmstudio"
    local = True
    supports_tools = False

    def __init__(self):
        enabled = os.getenv("LMSTUDIO_ENABLED", "false").lower() == "true"
        self.base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        self.model = os.getenv("LMSTUDIO_MODEL", "local-model")

        if not enabled:
            self.status = "NOT_CONFIGURED"
            self.client = None
            return

        self.status = "READY"
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
        )

    def generate(
        self,
        user_input,
        context=None,
        tools=None,
        executor=None,
    ):
        if self.client is None:
            raise ProviderError("LM Studio provider is not enabled.")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are JARVIS running through a local LM Studio model. "
                    "Do not claim system actions happened unless tool results "
                    "are explicitly present in context."
                ),
            }
        ]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant JARVIS context:\n{context}",
                }
            )

        messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        except Exception as error:
            self.status = "UNAVAILABLE"
            raise ProviderError(f"LM Studio request failed: {error}") from error

        self.status = "READY"
        return response.choices[0].message.content or ""
