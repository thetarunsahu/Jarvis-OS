import os

from openai import OpenAI
from providers.ai_provider import AIProvider


class OpenAIProvider(AIProvider):

    def __init__(self):
        self.name = "OpenAI"

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            self.status = "NOT_CONFIGURED"
            self.client = None
        else:
            self.status = "CONNECTED"
            self.client = OpenAI(api_key=api_key)

        self.model = os.getenv("AI_MODEL", "gpt-5.6")

    def generate(self, user_input, context=None):

        if self.client is None:
            return "OpenAI API key is not configured yet."

        response = self.client.responses.create(
            model=self.model,
            input=user_input
        )

        return response.output_text