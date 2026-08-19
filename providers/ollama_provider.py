import ollama


class OllamaProvider:

    def __init__(self):
        self.model = "qwen3:8b"

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
        tools=None,
        executor=None
    ):

        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": "/no_think\n" + user_input
            }
        ]

        response = ollama.chat(
            model=self.model,
            messages=messages,
            tools=tools or []
        )

        # -----------------------------------------
        # NO TOOL CALL
        # -----------------------------------------

        if not response.message.tool_calls:
            return response.message.content

        # -----------------------------------------
        # TOOL CALL
        # -----------------------------------------

        messages.append(response.message)

        for tool_call in response.message.tool_calls:

            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments or {}

            print(
                f"JARVIS TOOL: {tool_name}"
            )

            print(
                f"ARGUMENTS: {arguments}"
            )

            if executor:

                result = executor(
                    tool_name,
                    arguments
                )

            else:

                result = (
                    "Tool executor is unavailable."
                )

            print(
                f"TOOL RESULT: {result}"
            )

            messages.append(
                {
                    "role": "tool",
                    "content": str(result),
                }
            )

        # -----------------------------------------
        # ASK QWEN FOR FINAL RESPONSE
        # -----------------------------------------

        final_response = ollama.chat(
            model=self.model,
            messages=messages
        )

        return final_response.message.content