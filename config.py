"""
Configuration settings loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Line Messaging API ──────────────────────────────────────────────────
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

    # ── Anthropic (Claude) ──────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")

    # ── Notion ──────────────────────────────────────────────────────────────
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    # IDs of the three Notion databases (set after running setup_notion.py)
    NOTION_PROJECTS_DB_ID: str = os.getenv("NOTION_PROJECTS_DB_ID", "")
    NOTION_TASKS_DB_ID: str = os.getenv("NOTION_TASKS_DB_ID", "")
    NOTION_UPDATES_DB_ID: str = os.getenv("NOTION_UPDATES_DB_ID", "")

    # ── App ─────────────────────────────────────────────────────────────────
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


config = Config()
