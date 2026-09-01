import os

import ollama

from providers.ai_provider import AIProvider, ProviderError


class OllamaProvider(AIProvider):
    name = "ollama"
    local = True
    supports_tools = True

    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
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

        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=tools or [],
            )
        except Exception as error:
            self.status = "UNAVAILABLE"
            raise ProviderError(f"Ollama request failed: {error}") from error

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

        try:
            final_response = ollama.chat(
                model=self.model,
                messages=messages,
            )
        except Exception as error:
            self.status = "UNAVAILABLE"
            raise ProviderError(
                f"Ollama final response failed: {error}"
            ) from error

        self.status = "READY"
        return final_response.message.content
