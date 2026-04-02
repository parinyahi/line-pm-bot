"""
Data models for the PM bot.
"""
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


# ── Enumerations ─────────────────────────────────────────────────────────────

class Intent(str, Enum):
    UPDATE_PROJECT_STATUS = "update_project_status"
    ADD_TASK              = "add_task"
    UPDATE_TASK_STATUS    = "update_task_status"
    ADD_NOTE              = "add_note"
    QUERY_PROJECT         = "query_project"
    QUERY_TASK            = "query_task"
    LIST_PROJECTS         = "list_projects"
    LIST_TASKS            = "list_tasks"
    UNKNOWN               = "unknown"


class ProjectStatus(str, Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    ON_HOLD     = "On Hold"
    COMPLETED   = "Completed"
    CANCELLED   = "Cancelled"


class TaskStatus(str, Enum):
    TODO       = "Todo"
    IN_PROGRESS = "In Progress"
    IN_REVIEW  = "In Review"
    DONE       = "Done"
    BLOCKED    = "Blocked"


# ── Parsed intent from AI ─────────────────────────────────────────────────────

@dataclass
class ParsedIntent:
    intent: Intent
    project_name: Optional[str] = None
    task_name: Optional[str]    = None
    status: Optional[str]       = None
    note: Optional[str]         = None
    assignee: Optional[str]     = None
    due_date: Optional[str]     = None   # ISO 8601 string YYYY-MM-DD
    reporter: Optional[str]     = None   # Line display name
    raw_message: str            = ""
    confidence: float           = 1.0


# ── Notion response wrappers ──────────────────────────────────────────────────

@dataclass
class ProjectRecord:
    id: str
    name: str
    status: str
    owner: str        = ""
    due_date: str     = ""
    description: str  = ""
    url: str          = ""


@dataclass
class TaskRecord:
    id: str
    name: str
    status: str
    project_name: str = ""
    assignee: str     = ""
    due_date: str     = ""
    notes: str        = ""
    url: str          = ""


@dataclass
class UpdateRecord:
    id: str
    title: str
    project_name: str
    content: str
    reporter: str = ""
    url: str      = ""
