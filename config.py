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

    # ── OpenRouter ──────────────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "stepfun/step-3.5-flash:free")

    # ── Notion ──────────────────────────────────────────────────────────────
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    NOTION_PARENT_PAGE_ID: str = os.getenv("NOTION_PARENT_PAGE_ID", "")
    NOTION_PROJECTS_DB_ID: str = os.getenv("NOTION_PROJECTS_DB_ID", "")
    NOTION_TASKS_DB_ID: str = os.getenv("NOTION_TASKS_DB_ID", "")
    NOTION_UPDATES_DB_ID: str = os.getenv("NOTION_UPDATES_DB_ID", "")

    # ── App ─────────────────────────────────────────────────────────────────
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


config = Config()
