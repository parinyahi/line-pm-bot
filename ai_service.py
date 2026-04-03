"""
AI service – uses OpenRouter (OpenAI-compatible API) to parse natural language
messages into structured project-management intents via function calling.
"""
import json
import logging
from typing import Any

from openai import OpenAI

from config import config
from models import Intent, ParsedIntent

logger = logging.getLogger(__name__)

# ── Tool definitions (OpenAI function-calling format) ─────────────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "update_project_status",
            "description": "Update the status of a project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Name of the project"},
                    "status": {
                        "type": "string",
                        "enum": ["Not Started", "In Progress", "On Hold", "Completed", "Cancelled"],
                        "description": "New status for the project",
                    },
                    "note": {"type": "string", "description": "Optional note to attach to this update"},
                },
                "required": ["project_name", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Add a new task to a project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "task_name": {"type": "string"},
                    "assignee": {"type": "string", "description": "Person responsible for the task"},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                    "note": {"type": "string", "description": "Optional description / note"},
                },
                "required": ["project_name", "task_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task_status",
            "description": "Update the status of a specific task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "task_name": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["Todo", "In Progress", "In Review", "Done", "Blocked"],
                    },
                    "note": {"type": "string"},
                },
                "required": ["task_name", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Add a general note or update log entry for a project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "note": {"type": "string", "description": "The note content"},
                },
                "required": ["project_name", "note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_project",
            "description": "Query the status and details of a project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                },
                "required": ["project_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_task",
            "description": "Query the status and details of a specific task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "task_name": {"type": "string"},
                },
                "required": ["task_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "List all projects, optionally filtered by status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "type": "string",
                        "enum": ["Not Started", "In Progress", "On Hold", "Completed", "Cancelled", "all"],
                        "description": "Filter by status, or 'all' for all projects",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List tasks for a project, optionally filtered by status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "status_filter": {
                        "type": "string",
                        "enum": ["Todo", "In Progress", "In Review", "Done", "Blocked", "all"],
                    },
                },
                "required": [],
            },
        },
    },
]


SYSTEM_PROMPT = """You are an AI assistant for a project management bot on LINE.
Your job is to understand team members' natural language messages and call the
appropriate function to record or retrieve project information.

Guidelines:
- Always call exactly one function that best matches the user's intent.
- If you cannot determine the intent clearly, call 'query_project' or 'list_projects'.
- Extract project names and task names as they appear in the message.
- Infer status from keywords: "done/finished/complete" → Done/Completed,
  "started/working on/in progress" → In Progress, "blocked/stuck" → Blocked,
  "on hold/paused" → On Hold.
- Dates: convert relative terms like "tomorrow", "next Friday" to YYYY-MM-DD
  (use today = {today}).
- Keep note content concise and informative.
- The reporter field comes from the user's display name, passed separately.
"""


class AIService:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    def parse_intent(self, message: str, reporter: str = "Unknown", today: str = "") -> ParsedIntent:
        """Parse a LINE message into a structured ParsedIntent."""
        system = SYSTEM_PROMPT.replace("{today}", today or "unknown")

        try:
            response = self.client.chat.completions.create(
                model=config.OPENROUTER_MODEL,
                tools=TOOLS,
                tool_choice="required",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Reporter: {reporter}\nMessage: {message}"},
                ],
            )
        except Exception as exc:
            logger.error("OpenRouter API error: %s", exc)
            return ParsedIntent(intent=Intent.UNKNOWN, raw_message=message, reporter=reporter)

        # Extract tool call from response
        choice = response.choices[0]
        tool_calls = getattr(choice.message, "tool_calls", None)

        if not tool_calls:
            logger.warning("No function call returned for message: %s", message)
            return ParsedIntent(intent=Intent.UNKNOWN, raw_message=message, reporter=reporter)

        tool_call = tool_calls[0]
        tool_name: str = tool_call.function.name
        try:
            inputs: dict = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            logger.error("Failed to parse tool arguments: %s", tool_call.function.arguments)
            return ParsedIntent(intent=Intent.UNKNOWN, raw_message=message, reporter=reporter)

        # Map function name → Intent
        intent_map = {
            "update_project_status": Intent.UPDATE_PROJECT_STATUS,
            "add_task": Intent.ADD_TASK,
            "update_task_status": Intent.UPDATE_TASK_STATUS,
            "add_note": Intent.ADD_NOTE,
            "query_project": Intent.QUERY_PROJECT,
            "query_task": Intent.QUERY_TASK,
            "list_projects": Intent.LIST_PROJECTS,
            "list_tasks": Intent.LIST_TASKS,
        }
        intent = intent_map.get(tool_name, Intent.UNKNOWN)

        return ParsedIntent(
            intent=intent,
            project_name=inputs.get("project_name"),
            task_name=inputs.get("task_name"),
            status=inputs.get("status") or inputs.get("status_filter"),
            note=inputs.get("note"),
            assignee=inputs.get("assignee"),
            due_date=inputs.get("due_date"),
            reporter=reporter,
            raw_message=message,
        )


# Singleton
ai_service = AIService()
