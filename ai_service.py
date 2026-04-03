"""
AI service – uses OpenRouter to parse natural language messages into
structured project-management intents via JSON text output.
"""
import json
import logging
import re

from openai import OpenAI

from config import config
from models import Intent, ParsedIntent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Parse the message and reply ONLY with a JSON object. No explanation.

JSON fields: intent, project_name, task_name, status, status_filter, assignee, due_date, note
(use null for unused fields)

Intents and when to use them:
- update_project_status: change project status → needs project_name + status (Not Started|In Progress|On Hold|Completed|Cancelled)
- add_task: add task to project → needs project_name + task_name
- update_task_status: change task status → needs task_name + status (Todo|In Progress|In Review|Done|Blocked)
- add_note: log a note → needs project_name + note
- query_project: get project info → needs project_name
- query_task: get task info → needs task_name
- list_projects: list all projects → optional status_filter (Not Started|In Progress|On Hold|Completed|Cancelled|all)
- list_tasks: list tasks → optional project_name + status_filter (Todo|In Progress|In Review|Done|Blocked|all)

Status keywords: done/finished/complete→Done or Completed, started/working on→In Progress, blocked/stuck→Blocked, on hold/paused→On Hold
Today: {today}. Convert relative dates to YYYY-MM-DD.
Default to list_projects if unclear."""


class AIService:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = config.OPENROUTER_MODEL

    def parse_intent(self, message: str, reporter: str = "Unknown", today: str = "") -> ParsedIntent:
        """Parse a LINE message into a structured ParsedIntent via JSON output."""
        system = SYSTEM_PROMPT.replace("{today}", today or "unknown")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Reporter: {reporter}\nMessage: {message}"},
                ],
            )
        except Exception as exc:
            logger.error("OpenRouter API error: %s", exc)
            return ParsedIntent(intent=Intent.UNKNOWN, raw_message=message, reporter=reporter)

        raw = (response.choices[0].message.content or "").strip()
        logger.debug("Raw AI response: %s", raw)

        if not raw:
            logger.warning("Empty response from model for: %s", message)
            return ParsedIntent(intent=Intent.UNKNOWN, raw_message=message, reporter=reporter)

        # Strip markdown code fences if present
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            logger.warning("No JSON found in response: %s", raw)
            return ParsedIntent(intent=Intent.UNKNOWN, raw_message=message, reporter=reporter)

        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON: %s", raw)
            return ParsedIntent(intent=Intent.UNKNOWN, raw_message=message, reporter=reporter)

        intent_map = {
            "update_project_status": Intent.UPDATE_PROJECT_STATUS,
            "add_task":              Intent.ADD_TASK,
            "update_task_status":    Intent.UPDATE_TASK_STATUS,
            "add_note":              Intent.ADD_NOTE,
            "query_project":         Intent.QUERY_PROJECT,
            "query_task":            Intent.QUERY_TASK,
            "list_projects":         Intent.LIST_PROJECTS,
            "list_tasks":            Intent.LIST_TASKS,
        }
        intent = intent_map.get(data.get("intent", ""), Intent.UNKNOWN)
        logger.info("Parsed intent=%s data=%s", intent.value, data)

        return ParsedIntent(
            intent=intent,
            project_name=data.get("project_name"),
            task_name=data.get("task_name"),
            status=data.get("status") or data.get("status_filter"),
            note=data.get("note"),
            assignee=data.get("assignee"),
            due_date=data.get("due_date"),
            reporter=reporter,
            raw_message=message,
        )


# Singleton
ai_service = AIService()
