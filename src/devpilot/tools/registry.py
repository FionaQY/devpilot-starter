import json
from typing import Any

from devpilot.tools.filesystem import RepositoryFiles, WorkspaceError


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List files in the selected repository or a subdirectory. Use this to explore the project structure.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Relative directory path, or '.' for the repository root."},
                "limit": {"type": "integer", "description": "Maximum number of files to return (1-500)."},
            },
            "required": ["directory", "limit"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a text file from the selected repository. Paths must be relative to the repository root.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to the file."},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_files",
        "description": "Search for a literal text string inside repository files.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search for."},
                "limit": {"type": "integer", "description": "Maximum number of matching lines (1-100)."},
            },
            "required": ["query", "limit"],
            "additionalProperties": False,
        },
    },
]


class ToolRegistry:
    def __init__(self, files: RepositoryFiles) -> None:
        self.files = files

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            if name == "list_files":
                return self.files.list_files(**arguments)
            if name == "read_file":
                return self.files.read_file(**arguments)
            if name == "search_files":
                return self.files.search_files(**arguments)
            return f"Tool error: unknown tool '{name}'."
        except (WorkspaceError, OSError, UnicodeError, TypeError) as exc:
            return f"Tool error: {exc}"
