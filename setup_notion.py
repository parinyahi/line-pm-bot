"""
One-time setup script to create the three Notion databases needed by the PM bot.

Run ONCE after cloning the project:
    python setup_notion.py

It will print the three database IDs – copy them into your .env file.
"""
import os
import sys

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")  # ID of a page to put DBs under

if not NOTION_API_KEY:
    sys.exit("❌  NOTION_API_KEY not set in .env")
if not NOTION_PARENT_PAGE_ID:
    sys.exit(
        "❌  NOTION_PARENT_PAGE_ID not set in .env\n"
        "    Open any Notion page, copy its URL, and take the ID portion\n"
        "    e.g. https://www.notion.so/My-Workspace-<ID>?..."
    )

client = Client(auth=NOTION_API_KEY)


def create_projects_db(parent_id: str) -> str:
    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[{"type": "text", "text": {"content": "📂 Projects"}}],
        properties={
            "Name": {"title": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Not Started", "color": "gray"},
                        {"name": "In Progress", "color": "blue"},
                        {"name": "On Hold",     "color": "yellow"},
                        {"name": "Completed",   "color": "green"},
                        {"name": "Cancelled",   "color": "red"},
                    ]
                }
            },
            "Owner":       {"rich_text": {}},
            "Due Date":    {"date": {}},
            "Description": {"rich_text": {}},
        },
    )
    return db["id"]


def create_tasks_db(parent_id: str) -> str:
    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[{"type": "text", "text": {"content": "✅ Tasks"}}],
        properties={
            "Name": {"title": {}},
            "Project": {"rich_text": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Todo",        "color": "gray"},
                        {"name": "In Progress", "color": "blue"},
                        {"name": "In Review",   "color": "purple"},
                        {"name": "Done",        "color": "green"},
                        {"name": "Blocked",     "color": "red"},
                    ]
                }
            },
            "Assignee": {"rich_text": {}},
            "Due Date": {"date": {}},
            "Notes":    {"rich_text": {}},
        },
    )
    return db["id"]


def create_updates_db(parent_id: str) -> str:
    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_id},
        title=[{"type": "text", "text": {"content": "📋 Updates Log"}}],
        properties={
            "Title":     {"title": {}},
            "Project":   {"rich_text": {}},
            "Content":   {"rich_text": {}},
            "Reporter":  {"rich_text": {}},
            "Timestamp": {"date": {}},
        },
    )
    return db["id"]


if __name__ == "__main__":
    print("Creating Notion databases …\n")

    projects_id = create_projects_db(NOTION_PARENT_PAGE_ID)
    print(f"✅  Projects DB  → NOTION_PROJECTS_DB_ID={projects_id}")

    tasks_id = create_tasks_db(NOTION_PARENT_PAGE_ID)
    print(f"✅  Tasks DB     → NOTION_TASKS_DB_ID={tasks_id}")

    updates_id = create_updates_db(NOTION_PARENT_PAGE_ID)
    print(f"✅  Updates DB   → NOTION_UPDATES_DB_ID={updates_id}")

    print(
        "\nAdd these three lines to your .env file:\n"
        f"NOTION_PROJECTS_DB_ID={projects_id}\n"
        f"NOTION_TASKS_DB_ID={tasks_id}\n"
        f"NOTION_UPDATES_DB_ID={updates_id}\n"
    )
