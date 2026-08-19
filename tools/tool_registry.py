from tools.file_tools import FileTools
from tools.system_tools import SystemTools


class ToolRegistry:

    def __init__(self):
        self.tools = {
            "list_files": self.list_files,
            "system_info": self.system_info,
            "current_time": self.current_time,
        }

    def list_files(self):
        return FileTools.list_files()

    def system_info(self):
        return SystemTools.get_system_info()

    def current_time(self):
        return SystemTools.get_time()

    def execute(self, tool_name, arguments=None):
        tool = self.tools.get(tool_name)

        if tool is None:
            return f"Unknown tool: {tool_name}"

        try:
            arguments = arguments or {}
            return tool(**arguments)

        except TypeError:
            return tool()

        except Exception as error:
            return f"Tool execution failed: {error}"

    def get_tool_definitions(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": (
                        "List files and directories "
                        "in the current JARVIS project directory."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "system_info",
                    "description": (
                        "Get information about the computer "
                        "operating system and hardware."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "current_time",
                    "description": (
                        "Get the current local time."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
        ]

    def get_tool_names(self):
        return list(self.tools.keys())