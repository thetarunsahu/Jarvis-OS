import os

from openai import OpenAI

from providers.ai_provider import AIProvider, ProviderError


class OpenAIProvider(AIProvider):
    name = "openai"
    local = False
    supports_tools = False

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            self.status = "NOT_CONFIGURED"
            self.client = None
        else:
            self.status = "READY"
            self.client = OpenAI(api_key=api_key)

        self.model = os.getenv("OPENAI_MODEL", os.getenv("AI_MODEL", "gpt-5.6"))

    def generate(
        self,
        user_input,
        context=None,
        tools=None,
        executor=None,
    ):
        if self.client is None:
            raise ProviderError("OpenAI API key is not configured.")

        prompt = user_input

        if context:
            prompt = f"Relevant JARVIS context:\n{context}\n\nUser request:\n{user_input}"

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )
        except Exception as error:
            raise ProviderError(f"OpenAI request failed: {error}") from error

        self.status = "READY"
        return response.output_text
