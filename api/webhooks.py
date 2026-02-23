"""Webhook endpoints for Slack and Jira."""

import hmac
import hashlib
import json
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from bee.queue import get_queue
from bee.tasks import handle_jira_mention_job, handle_slack_mention_job
from clients.slack import slack
from config import config
from utils.attachment_processor import attachment_processor

router = APIRouter()


def _verify_slack_signature(body: bytes, headers: dict) -> tuple[bool, str | None]:
    if not config.SLACK_VERIFY_SIGNATURE:
        return True, None

    if not config.SLACK_SIGNING_SECRET:
        return False, "SLACK_SIGNING_SECRET not set"

    timestamp = headers.get("X-Slack-Request-Timestamp")
    signature = headers.get("X-Slack-Signature")
    if not timestamp or not signature:
        return False, "Missing Slack signature headers"

    try:
        ts_int = int(timestamp)
    except ValueError:
        return False, "Invalid Slack timestamp"

    if abs(time.time() - ts_int) > 60 * 5:
        return False, "Slack request timestamp too old"

    base = f"v0:{timestamp}:".encode("utf-8") + body
    digest = hmac.new(
        config.SLACK_SIGNING_SECRET.encode("utf-8"), base, hashlib.sha256
    ).hexdigest()
    expected = f"v0={digest}"

    if not hmac.compare_digest(expected, signature):
        return False, "Invalid Slack signature"

    return True, None


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
    files: list | None = None  # Attachments


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

    display_name: str = Field(alias="displayName")


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
):
    """
    Handle Slack app_mention webhook.

    Parses payload, adds emoji reaction, and queues background investigation.
    """
    body = await request.body()
    ok, error = _verify_slack_signature(body, dict(request.headers))
    if not ok:
        return {"ok": False, "error": error}

    payload_dict = json.loads(body.decode("utf-8"))

    # Handle Slack URL verification challenge
    if payload_dict.get("type") == "url_verification":
        print("\n" + "=" * 80)
        print("🔐 SLACK URL VERIFICATION CHALLENGE")
        print("=" * 80)
        print("✅ Responding with challenge token")
        print("=" * 80 + "\n")
        return {"challenge": payload_dict["challenge"]}

    print("\n" + "=" * 80)
    print("💬 SLACK WEBHOOK RECEIVED")
    print("=" * 80)
    print(f"Raw payload keys: {list(payload_dict.keys())}")
    print(f"Event type: {payload_dict.get('type')}")

    # Parse payload
    payload = SlackWebhookPayload(**payload_dict)

    if not payload.event:
        print("❌ No event in payload")
        print("=" * 80 + "\n")
        return {"ok": False, "error": "No event in payload"}

    event = payload.event

    # Ignore bot messages to avoid loops
    if event.bot_id:
        print("🤖 Ignoring bot message (avoiding loops)")
        print("=" * 80 + "\n")
        return {"ok": True, "message": "Ignored bot message"}

    # Extract context
    channel = event.channel
    message_ts = event.ts  # Timestamp of the @mention message
    thread_ts = event.thread_ts or event.ts  # Use thread or message ts
    user_message = event.text
    user_id = event.user

    print(f"📺 Channel: {channel}")
    print(f"👤 User: {user_id}")
    print(f"🧵 Thread: {thread_ts}")
    print(f"💬 Message: {user_message[:100]}...")
    print(f"🔍 Contains @onkaul: {'@onkaul' in user_message.lower()}")

    # Add immediate reaction to acknowledge
    print("👍 Adding :onkaul: reaction to message...")
    reaction_result = slack.add_reaction(channel, message_ts, "onkaul")
    if reaction_result.get("success"):
        print("✅ Reaction added")
    else:
        print(f"⚠️  Failed to add reaction: {reaction_result.get('error')}")

    # Process attachments if present
    attachments = []
    if event.files:
        print(f"📎 Found {len(event.files)} attachment(s)")
        for file_data in event.files:
            print(f"  - {file_data.get('name')} ({file_data.get('filetype')})")
            result = attachment_processor.process_slack_file(file_data, config.SLACK_BOT_TOKEN)
            if result.get("processed"):
                print(f"    ✅ Extracted {len(result.get('extracted_text', ''))} chars")
                attachments.append(result)
            else:
                print(f"    ⚠️  {result.get('message', result.get('error', 'Not processed'))}")

    # Fetch thread context if this is a reply
    thread_context = None
    if thread_ts and thread_ts != event.ts:
        print("📜 Fetching thread history for context...")
        result = slack.get_thread(channel, thread_ts)
        if result.get("success"):
            messages = result.get("messages", [])
            print(f"✅ Found {len(messages)} messages in thread")
            thread_context = messages
        else:
            print(f"⚠️  Failed to fetch thread: {result.get('error')}")

    print("✅ Valid mention - queuing investigation")
    print("=" * 80 + "\n")

    # Queue background investigation
    queue = get_queue()
    queue.enqueue(
        handle_slack_mention_job,
        channel=channel,
        thread_ts=thread_ts,
        user_message=user_message,
        user_id=user_id,
        thread_context=thread_context,
        attachments=attachments,
        job_timeout=config.JOB_TIMEOUT_SECONDS,
    )

    return {"ok": True, "message": "Investigation queued"}


@router.post("/webhook/jira")
async def jira_webhook(
    request: Request,
):
    """
    Handle Jira comment webhook.

    Parses payload and queues background investigation.
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
    queue = get_queue()
    queue.enqueue(
        handle_jira_mention_job,
        issue_key=issue_key,
        comment_body=comment_body,
        author=author,
        job_timeout=config.JOB_TIMEOUT_SECONDS,
    )

    return {"ok": True, "message": "Investigation queued"}
