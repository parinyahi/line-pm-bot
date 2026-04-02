"""
Line PM Bot – FastAPI application entry point.

Handles:
  • LINE webhook signature verification
  • Text message events → AI intent parsing → Notion CRUD → LINE reply
  • Health-check endpoint
"""
import logging
from datetime import date

from fastapi import FastAPI, Header, HTTPException, Request, Response
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from ai_service import ai_service
from config import config
from notion_service import notion_service

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Line PM Bot", version="1.0.0")

# ── LINE SDK setup ────────────────────────────────────────────────────────────
handler = WebhookHandler(config.LINE_CHANNEL_SECRET)
line_config = Configuration(access_token=config.LINE_CHANNEL_ACCESS_TOKEN)


def reply(reply_token: str, text: str) -> None:
    """Send a text reply via LINE Messaging API."""
    with ApiClient(line_config) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "bot": "Line PM Bot"}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_line_signature: str = Header(alias="X-Line-Signature"),
):
    body = await request.body()
    body_text = body.decode("utf-8")

    try:
        handler.handle(body_text, x_line_signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature received.")
        raise HTTPException(status_code=400, detail="Invalid signature")

    return Response(content="OK", status_code=200)


# ── Event handlers ────────────────────────────────────────────────────────────

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent) -> None:
    user_message: str = event.message.text.strip()
    reply_token: str = event.reply_token

    # Get sender display name (best-effort)
    reporter = "Team Member"
    if event.source:
        src = event.source
        # Group / Room source may have user_id
        user_id = getattr(src, "user_id", None)
        if user_id:
            try:
                with ApiClient(line_config) as api_client:
                    profile = MessagingApi(api_client).get_profile(user_id)
                    reporter = profile.display_name
            except Exception:
                pass  # Non-critical – continue without name

    logger.info("Message from %s: %s", reporter, user_message)

    today_str = date.today().isoformat()

    # 1. Parse intent with Claude
    parsed = ai_service.parse_intent(user_message, reporter=reporter, today=today_str)
    logger.info("Parsed intent: %s | project=%s | task=%s | status=%s",
                parsed.intent, parsed.project_name, parsed.task_name, parsed.status)

    # 2. Execute Notion operation
    result_text = notion_service.handle_intent(parsed)

    # 3. Optionally wrap result in a friendly AI response (for query intents)
    from models import Intent
    if parsed.intent in (Intent.QUERY_PROJECT, Intent.QUERY_TASK,
                         Intent.LIST_PROJECTS, Intent.LIST_TASKS):
        # For queries, the result_text IS the answer – send directly
        final_reply = result_text
    else:
        # For write operations, add friendly acknowledgement
        final_reply = result_text

    logger.info("Replying: %s", final_reply[:120])
    reply(reply_token, final_reply)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=config.DEBUG)
