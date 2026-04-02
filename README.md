# 🤖 Line PM Bot

A **Project Manager bot for LINE** that lets your team send natural language messages to report and query project status — all stored and tracked in Notion.

## Architecture

```
LINE App (team)
     │  message
     ▼
LINE Messaging API  ──webhook──▶  FastAPI (main.py)
                                        │
                                        ▼
                               Claude AI (ai_service.py)
                               (parses intent via tool-use)
                                        │
                                        ▼
                               Notion Service (notion_service.py)
                               ┌────────────────────────┐
                               │  📂 Projects DB         │
                               │  ✅ Tasks DB            │
                               │  📋 Updates Log DB      │
                               └────────────────────────┘
                                        │
                               Reply back to LINE user
```

## Features

| What the team says | What the bot does |
|---|---|
| "Update Alpha project to In Progress" | Updates project status in Notion |
| "Add task: design review to Beta project, assigned to John" | Creates a new task |
| "Mark design review task as done" | Updates task status |
| "What's the status of Alpha project?" | Returns full project summary |
| "List all ongoing projects" | Lists all In Progress projects |
| "Add note to Beta: client approved the mockups" | Logs an update entry |

---

## Setup Guide

### 1. Prerequisites

- Python 3.11+
- A [LINE Developers](https://developers.line.biz) account
- An [Anthropic](https://console.anthropic.com) API key
- A [Notion](https://notion.so) account with an integration token

---

### 2. Clone & Install

```bash
git clone <your-repo>
cd line-pm-bot
pip install -r requirements.txt
```

---

### 3. Configure LINE Channel

1. Go to [LINE Developers Console](https://developers.line.biz/console/)
2. Create a new **Provider** and **Messaging API Channel**
3. Under **Messaging API** tab:
   - Copy **Channel Secret** → `LINE_CHANNEL_SECRET`
   - Issue a **Channel Access Token (Long-lived)** → `LINE_CHANNEL_ACCESS_TOKEN`
   - Enable **Use webhooks**
   - Set Webhook URL to: `https://<your-domain>/webhook`
   - Disable **Auto-reply messages**

---

### 4. Configure Notion Integration

1. Go to [https://www.notion.so/profile/integrations](https://www.notion.so/profile/integrations)
2. Click **New integration** → give it a name (e.g. "PM Bot")
3. Copy the **Internal Integration Secret** → `NOTION_API_KEY`
4. Open your Notion workspace and find the **🤖 Line PM Bot Workspace** page
5. Click `···` → **Connect to** → select your integration
6. Do the same for the three databases inside it (📂 Projects, ✅ Tasks, 📋 Updates Log)

> **The three Notion databases are already created** in your workspace with the correct schema. Their IDs are pre-filled in `.env.example`.

---

### 5. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `ANTHROPIC_API_KEY`
- `NOTION_API_KEY`

The Notion database IDs are already pre-filled from the setup step.

---

### 6. Run Locally (for testing)

```bash
python main.py
```

Expose locally with [ngrok](https://ngrok.com):
```bash
ngrok http 8000
```

Set the ngrok URL as your LINE webhook: `https://xxxx.ngrok.io/webhook`

---

### 7. Deploy to Railway

1. Push code to a GitHub repo
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Add all environment variables from `.env` in the Railway **Variables** tab
4. Railway will auto-deploy; copy the generated URL
5. Set the Railway URL as your LINE webhook: `https://<railway-url>/webhook`

**Alternatively, deploy to Render:**
1. Go to [render.com](https://render.com) → **New Web Service**
2. Connect your GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables and deploy

---

## Example Conversations

```
Team member: "Update Mobile App project to In Progress, we just kicked off the sprint"
Bot: ✅ Updated Mobile App → In Progress.

Team member: "Add task: write unit tests to Mobile App project, assign to Som"
Bot: ✅ Task write unit tests added to Mobile App.

Team member: "What's the status of Mobile App?"
Bot: 📂 Mobile App
     Status: In Progress
     Tasks:
       • write unit tests [Todo] – Som
       • design review [Done]
     Recent updates:
       • Status changed to In Progress. We just kicked off the sprint.

Team member: "List all projects"
Bot: 📋 Projects (3):
       • Mobile App [In Progress] – Paul
       • Website Redesign [Completed]
       • API Integration [Not Started]
```

---

## Project Structure

```
line-pm-bot/
├── main.py              # FastAPI app + LINE webhook handler
├── ai_service.py        # Claude intent parsing (NLU)
├── notion_service.py    # All Notion CRUD operations
├── models.py            # Data models & enums
├── config.py            # Environment variable config
├── setup_notion.py      # (Optional) re-create Notion DBs from scratch
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
└── .gitignore
```

---

## Notion Workspace

Your databases are live at:
- [🤖 Line PM Bot Workspace](https://www.notion.so/336b255de5e781a3ac2dc3595665ddf6)
  - [📂 Projects](https://www.notion.so/2941d03dbd3c4ac19f88434f2622a42d)
  - [✅ Tasks](https://www.notion.so/ce1b0cebe1734ea7a52bf678755107e5)
  - [📋 Updates Log](https://www.notion.so/0351b964009643cd990b303a0160bbc0)

---

## Adding the Bot to a LINE Group

1. Go to LINE Developers Console → your channel → **Basic settings**
2. Under **Bot information**, scan the QR code to add the bot as a friend
3. Add the bot to your team's LINE group chat
4. The bot will respond to every message in the group

> The bot identifies who sent each message by their LINE display name (the "Reporter" field in updates).
