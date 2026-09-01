import json
import os

from openai import OpenAI

from providers.ai_provider import AIProvider, ProviderError


class OpenAIProvider(AIProvider):
    """OpenAI Responses API provider with JARVIS tool execution support."""

    name = "openai"
    local = False
    supports_tools = True

    def __init__(self, client=None):
        self.model = os.getenv("OPENAI_MODEL", os.getenv("AI_MODEL", "gpt-5.6"))
        self.max_tool_rounds = max(
            1,
            int(os.getenv("OPENAI_MAX_TOOL_ROUNDS", "8")),
        )

        if client is not None:
            self.client = client
            self.status = "READY"
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.status = "NOT_CONFIGURED"
            self.client = None
        else:
            self.status = "READY"
            self.client = OpenAI(api_key=api_key)

    @staticmethod
    def _convert_tools(tools):
        """Convert JARVIS/Ollama-style function schemas to Responses tools."""
        converted = []

        for tool in tools or []:
            if tool.get("type") != "function":
                continue

            function = tool.get("function", {})
            name = function.get("name")
            if not name:
                continue

            converted.append(
                {
                    "type": "function",
                    "name": name,
                    "description": function.get("description", ""),
                    "parameters": function.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                    # JARVIS tools are still evolving, so strict mode stays
                    # off until every internal schema is strict-compatible.
                    "strict": False,
                }
            )

        return converted

    @staticmethod
    def _tool_result_to_string(result):
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return str(result)

    def _create_response(self, **kwargs):
        try:
            return self.client.responses.create(**kwargs)
        except Exception as error:
            self.status = "UNAVAILABLE"
            raise ProviderError(f"OpenAI request failed: {error}") from error

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
            prompt = (
                f"Relevant JARVIS context:\n{context}\n\n"
                f"User request:\n{user_input}"
            )

        openai_tools = self._convert_tools(tools)
        request = {
            "model": self.model,
            "input": prompt,
        }
        if openai_tools:
            request["tools"] = openai_tools
            request["tool_choice"] = "auto"

        response = self._create_response(**request)

        for _ in range(self.max_tool_rounds):
            function_calls = [
                item
                for item in (getattr(response, "output", None) or [])
                if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                self.status = "READY"
                return getattr(response, "output_text", "") or ""

            tool_outputs = []
            for call in function_calls:
                try:
                    arguments = json.loads(getattr(call, "arguments", "{}") or "{}")
                except json.JSONDecodeError as error:
                    result = f"Invalid tool arguments: {error}"
                else:
                    if executor is None:
                        result = "Tool executor is unavailable."
                    else:
                        try:
                            result = executor(call.name, arguments)
                        except Exception as error:
                            result = f"Tool execution failed: {error}"

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": self._tool_result_to_string(result),
                    }
                )

            follow_up = {
                "model": self.model,
                "previous_response_id": response.id,
                "input": tool_outputs,
            }
            if openai_tools:
                follow_up["tools"] = openai_tools
                follow_up["tool_choice"] = "auto"

            response = self._create_response(**follow_up)

        raise ProviderError(
            "OpenAI tool execution exceeded the configured tool-call limit."
        )
