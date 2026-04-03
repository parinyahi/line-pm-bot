"""
Notion service – all CRUD operations against the three PM databases:
  • Projects
  • Tasks
  • Updates (activity log)
"""
import logging
from datetime import datetime
from typing import Optional

from notion_client import Client

from config import config
from models import ParsedIntent, ProjectRecord, TaskRecord, UpdateRecord, Intent

logger = logging.getLogger(__name__)


def _safe_title(page: dict, prop: str = "Name") -> str:
    try:
        return page["properties"][prop]["title"][0]["plain_text"]
    except (KeyError, IndexError):
        return ""


def _safe_select(page: dict, prop: str) -> str:
    try:
        sel = page["properties"][prop]["select"]
        return sel["name"] if sel else ""
    except KeyError:
        return ""


def _safe_rich_text(page: dict, prop: str) -> str:
    try:
        parts = page["properties"][prop]["rich_text"]
        return " ".join(p["plain_text"] for p in parts)
    except KeyError:
        return ""


def _safe_date(page: dict, prop: str) -> str:
    try:
        d = page["properties"][prop]["date"]
        return d["start"] if d else ""
    except KeyError:
        return ""


class NotionService:
    def __init__(self) -> None:
        self.client = Client(auth=config.NOTION_API_KEY)
        self.projects_db = config.NOTION_PROJECTS_DB_ID
        self.tasks_db = config.NOTION_TASKS_DB_ID
        self.updates_db = config.NOTION_UPDATES_DB_ID

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _find_project_page(self, project_name: str) -> Optional[dict]:
        """Return the first Notion page whose title matches project_name (case-insensitive)."""
        results = self.client.databases.query(
            database_id=self.projects_db,
            filter={
                "property": "Name",
                "title": {"contains": project_name},
            },
        ).get("results", [])
        if not results:
            return None
        # Prefer exact match
        for r in results:
            if _safe_title(r).lower() == project_name.lower():
                return r
        return results[0]

    def _find_task_page(self, task_name: str, project_name: Optional[str] = None) -> Optional[dict]:
        filters: list[dict] = [
            {"property": "Name", "title": {"contains": task_name}}
        ]
        if project_name:
            filters.append(
                {"property": "Project", "rich_text": {"contains": project_name}}
            )
        query_filter = (
            {"and": filters} if len(filters) > 1 else filters[0]
        )
        results = self.client.databases.query(
            database_id=self.tasks_db,
            filter=query_filter,
        ).get("results", [])
        if not results:
            return None
        for r in results:
            if _safe_title(r).lower() == task_name.lower():
                return r
        return results[0]

    # ── Projects ──────────────────────────────────────────────────────────────

    def get_project(self, project_name: str) -> Optional[ProjectRecord]:
        page = self._find_project_page(project_name)
        if not page:
            return None
        return ProjectRecord(
            id=page["id"],
            name=_safe_title(page),
            status=_safe_select(page, "Status"),
            owner=_safe_rich_text(page, "Owner"),
            due_date=_safe_date(page, "Due Date"),
            description=_safe_rich_text(page, "Description"),
            url=page.get("url", ""),
        )

    def list_projects(self, status_filter: Optional[str] = None) -> list[ProjectRecord]:
        query: dict = {"database_id": self.projects_db}
        if status_filter and status_filter != "all":
            query["filter"] = {
                "property": "Status",
                "select": {"equals": status_filter},
            }
        results = self.client.databases.query(**query).get("results", [])
        projects = []
        for r in results:
            projects.append(
                ProjectRecord(
                    id=r["id"],
                    name=_safe_title(r),
                    status=_safe_select(r, "Status"),
                    owner=_safe_rich_text(r, "Owner"),
                    due_date=_safe_date(r, "Due Date"),
                    url=r.get("url", ""),
                )
            )
        return projects

    def update_project_status(
        self, project_name: str, status: str, note: Optional[str] = None, reporter: str = ""
    ) -> str:
        page = self._find_project_page(project_name)
        if not page:
            # Create new project
            new_page = self.client.pages.create(
                parent={"database_id": self.projects_db},
                properties={
                    "Name": {"title": [{"text": {"content": project_name}}]},
                    "Status": {"select": {"name": status}},
                },
            )
            msg = f"✅ Created new project **{project_name}** with status **{status}**."
        else:
            self.client.pages.update(
                page_id=page["id"],
                properties={"Status": {"select": {"name": status}}},
            )
            msg = f"✅ Updated **{project_name}** → **{status}**."

        # Log to Updates
        if note:
            self._log_update(project_name, f"Status changed to {status}. Note: {note}", reporter)
        else:
            self._log_update(project_name, f"Status changed to {status}.", reporter)

        return msg

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def get_task(self, task_name: str, project_name: Optional[str] = None) -> Optional[TaskRecord]:
        page = self._find_task_page(task_name, project_name)
        if not page:
            return None
        return TaskRecord(
            id=page["id"],
            name=_safe_title(page),
            status=_safe_select(page, "Status"),
            project_name=_safe_rich_text(page, "Project"),
            assignee=_safe_rich_text(page, "Assignee"),
            due_date=_safe_date(page, "Due Date"),
            notes=_safe_rich_text(page, "Notes"),
            url=page.get("url", ""),
        )

    def list_tasks(
        self, project_name: Optional[str] = None, status_filter: Optional[str] = None
    ) -> list[TaskRecord]:
        filters: list[dict] = []
        if project_name:
            filters.append({"property": "Project", "rich_text": {"contains": project_name}})
        if status_filter and status_filter != "all":
            filters.append({"property": "Status", "select": {"equals": status_filter}})

        query: dict = {"database_id": self.tasks_db}
        if filters:
            query["filter"] = {"and": filters} if len(filters) > 1 else filters[0]

        results = self.client.databases.query(**query).get("results", [])
        tasks = []
        for r in results:
            tasks.append(
                TaskRecord(
                    id=r["id"],
                    name=_safe_title(r),
                    status=_safe_select(r, "Status"),
                    project_name=_safe_rich_text(r, "Project"),
                    assignee=_safe_rich_text(r, "Assignee"),
                    due_date=_safe_date(r, "Due Date"),
                    url=r.get("url", ""),
                )
            )
        return tasks

    def add_task(
        self,
        project_name: str,
        task_name: str,
        assignee: Optional[str] = None,
        due_date: Optional[str] = None,
        note: Optional[str] = None,
        reporter: str = "",
    ) -> str:
        props: dict = {
            "Name": {"title": [{"text": {"content": task_name}}]},
            "Project": {"rich_text": [{"text": {"content": project_name}}]},
            "Status": {"select": {"name": "Todo"}},
        }
        if assignee:
            props["Assignee"] = {"rich_text": [{"text": {"content": assignee}}]}
        if due_date:
            props["Due Date"] = {"date": {"start": due_date}}
        if note:
            props["Notes"] = {"rich_text": [{"text": {"content": note}}]}

        self.client.pages.create(
            parent={"database_id": self.tasks_db},
            properties=props,
        )
        self._log_update(
            project_name,
            f"New task added: '{task_name}'" + (f" (assigned to {assignee})" if assignee else ""),
            reporter,
        )
        return f"✅ Task **{task_name}** added to **{project_name}**."

    def update_task_status(
        self,
        task_name: str,
        status: str,
        project_name: Optional[str] = None,
        note: Optional[str] = None,
        reporter: str = "",
    ) -> str:
        page = self._find_task_page(task_name, project_name)
        proj = project_name or (
            _safe_rich_text(page, "Project") if page else "Unknown Project"
        )

        if not page:
            return f"⚠️ Task **{task_name}** not found. Please check the task name."

        update_props: dict = {"Status": {"select": {"name": status}}}
        if note:
            update_props["Notes"] = {"rich_text": [{"text": {"content": note}}]}

        self.client.pages.update(page_id=page["id"], properties=update_props)
        self._log_update(
            proj,
            f"Task '{task_name}' updated to {status}." + (f" Note: {note}" if note else ""),
            reporter,
        )
        return f"✅ Task **{task_name}** → **{status}**."

    # ── Updates / Activity Log ────────────────────────────────────────────────

    def _log_update(self, project_name: str, content: str, reporter: str = "") -> None:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            title = f"[{timestamp}] {project_name}"
            self.client.pages.create(
                parent={"database_id": self.updates_db},
                properties={
                    "Title": {"title": [{"text": {"content": title}}]},
                    "Project": {"rich_text": [{"text": {"content": project_name}}]},
                    "Content": {"rich_text": [{"text": {"content": content}}]},
                    "Reporter": {"rich_text": [{"text": {"content": reporter}}]},
                    "Timestamp": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
                },
            )
        except Exception as exc:
            logger.warning("Failed to log update: %s", exc)

    def add_note(self, project_name: str, note: str, reporter: str = "") -> str:
        self._log_update(project_name, note, reporter)
        return f"📝 Note added to **{project_name}**."

    def get_recent_updates(self, project_name: str, limit: int = 5) -> list[UpdateRecord]:
        results = self.client.databases.query(
            database_id=self.updates_db,
            filter={"property": "Project", "rich_text": {"contains": project_name}},
            sorts=[{"property": "Timestamp", "direction": "descending"}],
            page_size=limit,
        ).get("results", [])
        updates = []
        for r in results:
            updates.append(
                UpdateRecord(
                    id=r["id"],
                    title=_safe_title(r, "Title"),
                    project_name=_safe_rich_text(r, "Project"),
                    content=_safe_rich_text(r, "Content"),
                    reporter=_safe_rich_text(r, "Reporter"),
                    url=r.get("url", ""),
                )
            )
        return updates

    # ── Dispatcher ────────────────────────────────────────────────────────────

    def handle_intent(self, parsed: ParsedIntent) -> str:
        """Route a ParsedIntent to the correct Notion operation and return a text result."""
        intent = parsed.intent
        reporter = parsed.reporter or "Unknown"

        if intent == Intent.UPDATE_PROJECT_STATUS:
            return self.update_project_status(
                parsed.project_name or "Unknown Project",
                parsed.status or "In Progress",
                parsed.note,
                reporter,
            )

        elif intent == Intent.ADD_TASK:
            return self.add_task(
                parsed.project_name or "Unknown Project",
                parsed.task_name or "Unnamed Task",
                parsed.assignee,
                parsed.due_date,
                parsed.note,
                reporter,
            )

        elif intent == Intent.UPDATE_TASK_STATUS:
            return self.update_task_status(
                parsed.task_name or "Unknown Task",
                parsed.status or "In Progress",
                parsed.project_name,
                parsed.note,
                reporter,
            )

        elif intent == Intent.ADD_NOTE:
            return self.add_note(
                parsed.project_name or "Unknown Project",
                parsed.note or parsed.raw_message,
                reporter,
            )

        elif intent == Intent.QUERY_PROJECT:
            project = self.get_project(parsed.project_name or "")
            if not project:
                return f"❌ Project **{parsed.project_name}** not found."
            tasks = self.list_tasks(project_name=project.name)
            task_lines = "\n".join(
                f"  • {t.name} [{t.status}]" + (f" – {t.assignee}" if t.assignee else "")
                for t in tasks
            )
            updates = self.get_recent_updates(project.name, limit=3)
            update_lines = "\n".join(f"  • {u.content}" for u in updates)
            parts = [
                f"📂 **{project.name}**",
                f"Status: {project.status}",
            ]
            if project.owner:
                parts.append(f"Owner: {project.owner}")
            if project.due_date:
                parts.append(f"Due: {project.due_date}")
            if task_lines:
                parts.append(f"\nTasks:\n{task_lines}")
            if update_lines:
                parts.append(f"\nRecent updates:\n{update_lines}")
            return "\n".join(parts)

        elif intent == Intent.QUERY_TASK:
            task = self.get_task(
                parsed.task_name or "", parsed.project_name
            )
            if not task:
                return f"❌ Task **{parsed.task_name}** not found."
            parts = [f"📌 **{task.name}**", f"Status: {task.status}"]
            if task.project_name:
                parts.append(f"Project: {task.project_name}")
            if task.assignee:
                parts.append(f"Assignee: {task.assignee}")
            if task.due_date:
                parts.append(f"Due: {task.due_date}")
            if task.notes:
                parts.append(f"Notes: {task.notes}")
            return "\n".join(parts)

        elif intent == Intent.LIST_PROJECTS:
            projects = self.list_projects(parsed.status)
            if not projects:
                return "No projects found."
            lines = [f"📋 Projects ({len(projects)}):"]
            for p in projects:
                line = f"  • {p.name} [{p.status}]"
                if p.owner:
                    line += f" – {p.owner}"
                lines.append(line)
            return "\n".join(lines)

        elif intent == Intent.LIST_TASKS:
            tasks = self.list_tasks(parsed.project_name, parsed.status)
            if not tasks:
                label = f" in **{parsed.project_name}**" if parsed.project_name else ""
                return f"No tasks found{label}."
            lines = [f"✅ Tasks ({len(tasks)}):"]
            for t in tasks:
                line = f"  • {t.name} [{t.status}]"
                if t.assignee:
                    line += f" – {t.assignee}"
                lines.append(line)
            return "\n".join(lines)

        else:
            return (
                "\U0001f914 I'm not sure what you mean. Try asking like:\n"
                '• "Update project Alpha to In Progress"\n'
                '• "Add task: design review to Beta project"\n'
                '• "What\'s the status of Alpha project?"\n'
                '• "List all ongoing projects"'
            )


# Singleton
notion_service = NotionService()
