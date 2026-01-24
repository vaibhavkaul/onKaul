"""Webhook endpoints for Slack and Jira."""

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel, Field

from worker.tasks import handle_jira_mention, handle_slack_mention

router = APIRouter()


# Pydantic models for request validation
class SlackEvent(BaseModel):
    """Slack app_mention event."""

    type: str
    channel: str
    ts: str
    thread_ts: str | None = None
    text: str
    user: str
    bot_id: str | None = None


class SlackWebhookPayload(BaseModel):
    """Slack webhook payload."""

    type: str | None = None  # For URL verification
    challenge: str | None = None  # For URL verification
    event: SlackEvent | None = None


class JiraIssue(BaseModel):
    """Jira issue."""

    key: str


class JiraCommentAuthor(BaseModel):
    """Jira comment author."""

    displayName: str = Field(alias="displayName")


class JiraComment(BaseModel):
    """Jira comment."""

    body: str
    author: JiraCommentAuthor


class JiraWebhookPayload(BaseModel):
    """Jira webhook payload."""

    issue: JiraIssue
    comment: JiraComment


@router.post("/webhook/slack")
async def slack_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle Slack app_mention webhook.

    Phase 1: No authentication, just parse and queue investigation.
    Phase 3: Add signature verification.
    """
    payload_dict = await request.json()

    # Handle Slack URL verification challenge
    if payload_dict.get("type") == "url_verification":
        return {"challenge": payload_dict["challenge"]}

    # Parse payload
    payload = SlackWebhookPayload(**payload_dict)

    if not payload.event:
        return {"ok": False, "error": "No event in payload"}

    event = payload.event

    # Ignore bot messages to avoid loops
    if event.bot_id:
        return {"ok": True, "message": "Ignored bot message"}

    # Extract context
    channel = event.channel
    thread_ts = event.thread_ts or event.ts  # Use thread or message ts
    user_message = event.text
    user_id = event.user

    # Queue background investigation
    background_tasks.add_task(
        handle_slack_mention,
        channel=channel,
        thread_ts=thread_ts,
        user_message=user_message,
        user_id=user_id,
    )

    return {"ok": True, "message": "Investigation queued"}


@router.post("/webhook/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle Jira comment webhook.

    Phase 1: No authentication, just parse and queue investigation.
    Phase 3: Add proper authentication.
    """
    payload_dict = await request.json()

    print("\n" + "=" * 80)
    print("🎫 JIRA WEBHOOK RECEIVED")
    print("=" * 80)
    print(f"Raw payload keys: {list(payload_dict.keys())}")

    # Parse payload
    payload = JiraWebhookPayload(**payload_dict)

    issue_key = payload.issue.key
    comment_body = payload.comment.body
    author = payload.comment.author.displayName

    print(f"📋 Issue: {issue_key}")
    print(f"👤 Author: {author}")
    print(f"💬 Comment: {comment_body[:100]}...")
    print(f"🔍 Contains @onkaul: {'@onkaul' in comment_body.lower()}")

    # Only process if @onkaul is mentioned (case-insensitive)
    if "@onkaul" not in comment_body.lower():
        print("⏭️  Skipping - no @onkaul mention")
        print("=" * 80 + "\n")
        return {"ok": True, "message": "No mention, ignored"}

    print("✅ Valid mention - queuing investigation")
    print("=" * 80 + "\n")

    # Queue background investigation
    background_tasks.add_task(
        handle_jira_mention,
        issue_key=issue_key,
        comment_body=comment_body,
        author=author,
    )

    return {"ok": True, "message": "Investigation queued"}
