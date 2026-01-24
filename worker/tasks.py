"""Background task handlers for webhook processing."""

import time

from agent.core import agent
from clients.jira import jira
from clients.slack import slack
from config import config
from utils.logger import logger
from utils.slack_formatter import format_for_slack


def handle_slack_mention(
    channel: str,
    thread_ts: str,
    user_message: str,
    user_id: str,
    thread_context: list | None = None,
):
    """
    Handle a Slack mention.

    Phase 2.5: Real investigation with logging + thread context.
    Phase 3: Add signature verification.
    """
    print("\n" + "=" * 80)
    print("🤖 STARTING INVESTIGATION (SLACK)")
    print("=" * 80)
    print(f"📺 Channel: {channel}")
    print(f"🧵 Thread: {thread_ts}")
    print(f"👤 User: {user_id}")
    print(f"💬 Request: {user_message[:100]}...")
    print(f"📜 Thread context: {len(thread_context) if thread_context else 0} messages")
    print(f"📤 Will post to Slack: {config.ENABLE_SLACK_POSTING}")
    print("-" * 80)

    start_time = time.time()

    try:
        # Build context from thread if available
        context = ""
        if thread_context:
            print("📜 Building context from thread history...")
            print(f"📝 Thread contains {len(thread_context)} total messages")
            context_parts = ["## Slack Thread Context\n"]
            for i, msg in enumerate(thread_context[:-1]):  # Exclude the current @mention
                user = msg.get("user", "Unknown")
                text = msg.get("text", "")
                context_parts.append(f"**{user}**: {text}\n")
                # Log first message for debugging
                if i == 0:
                    print(f"📨 First message preview: {text[:200]}...")
            context = "\n".join(context_parts)
            print(f"✅ Added {len(thread_context) - 1} previous messages as context")

        print("🧠 Calling agent...")
        # Real agent investigation with thread context
        response = agent.investigate(user_message, context=context)
        print(f"✅ Investigation complete ({len(response)} chars)")
        print("-" * 80)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Always log (for monitoring/debugging)
        print("📝 Logging response...")
        logger.log_response(
            source="slack",
            response=response,
            metadata={
                "channel": channel,
                "thread_ts": thread_ts,
                "user_message": user_message,
                "user_id": user_id,
                "posted_to_slack": config.ENABLE_SLACK_POSTING,
            },
            investigation_duration_ms=duration_ms,
        )

        # Post to Slack if enabled
        if config.ENABLE_SLACK_POSTING:
            print(f"📤 Posting message to channel {channel} (thread {thread_ts})...")
            # Format response for Slack (convert markdown to mrkdwn)
            slack_formatted = format_for_slack(response)
            result = slack.post_message(channel, slack_formatted, thread_ts)
            if result.get("success"):
                print(f"✅ Successfully posted to Slack")
                print(f"🔗 Message timestamp: {result.get('ts')}")
            else:
                print(f"❌ Failed to post to Slack: {result.get('error')}")
        else:
            print("⏭️  Skipping Slack post (ENABLE_SLACK_POSTING=false)")

        print("=" * 80)
        print(f"✨ INVESTIGATION COMPLETE - {duration_ms:.0f}ms")
        print("=" * 80 + "\n")

    except Exception as e:
        # Log error response
        error_response = f"Sorry, I encountered an error: {str(e)}"

        print(f"❌ ERROR during investigation: {str(e)}")
        print("-" * 80)

        logger.log_response(
            source="slack",
            response=error_response,
            metadata={
                "channel": channel,
                "thread_ts": thread_ts,
                "user_message": user_message,
                "user_id": user_id,
                "error": str(e),
            },
        )

        # Post error to Slack if enabled
        if config.ENABLE_SLACK_POSTING:
            print(f"📤 Posting error to channel {channel}...")
            slack_formatted = format_for_slack(error_response)
            result = slack.post_message(channel, slack_formatted, thread_ts)
            if result.get("success"):
                print(f"✅ Error posted to Slack")
            else:
                print(f"❌ Failed to post error: {result.get('error')}")

        print("=" * 80 + "\n")


def handle_jira_mention(
    issue_key: str,
    comment_body: str,
    author: str,
):
    """
    Handle a Jira mention.

    Phase 2.5: Post to Jira if ENABLE_JIRA_POSTING=true.
    Phase 3: Add Slack posting too.
    """
    print("\n" + "=" * 80)
    print("🤖 STARTING INVESTIGATION")
    print("=" * 80)
    print(f"📋 Jira Issue: {issue_key}")
    print(f"👤 Requested by: {author}")
    print(f"💬 Request: {comment_body[:100]}...")
    print(f"📤 Will post to Jira: {config.ENABLE_JIRA_POSTING}")
    print("-" * 80)

    start_time = time.time()

    try:
        # Build context from Jira issue
        context = f"Jira Issue: {issue_key}\nComment from {author}"

        print("🧠 Calling agent...")
        # Real agent investigation
        response = agent.investigate(comment_body, context=context)
        print(f"✅ Investigation complete ({len(response)} chars)")
        print("-" * 80)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Always log (for monitoring/debugging)
        print("📝 Logging response...")
        logger.log_response(
            source="jira",
            response=response,
            metadata={
                "issue_key": issue_key,
                "comment_body": comment_body,
                "author": author,
                "posted_to_jira": config.ENABLE_JIRA_POSTING,
            },
            investigation_duration_ms=duration_ms,
        )

        # Phase 2.5: Post to Jira if enabled
        if config.ENABLE_JIRA_POSTING:
            print(f"📤 Posting comment to {issue_key}...")
            result = jira.add_comment(issue_key, response)
            if result.get("success"):
                print(f"✅ Successfully posted to {issue_key}")
                print(f"🔗 View at: https://taptapsend.atlassian.net/browse/{issue_key}")
            else:
                print(f"❌ Failed to post to Jira: {result.get('error')}")
        else:
            print("⏭️  Skipping Jira post (ENABLE_JIRA_POSTING=false)")

        print("=" * 80)
        print(f"✨ INVESTIGATION COMPLETE - {duration_ms:.0f}ms")
        print("=" * 80 + "\n")

    except Exception as e:
        # Log error response
        error_response = f"Sorry, I encountered an error: {str(e)}"

        print(f"❌ ERROR during investigation: {str(e)}")
        print("-" * 80)

        logger.log_response(
            source="jira",
            response=error_response,
            metadata={
                "issue_key": issue_key,
                "comment_body": comment_body,
                "author": author,
                "error": str(e),
            },
        )

        # Post error to Jira if enabled
        if config.ENABLE_JIRA_POSTING:
            print(f"📤 Posting error to {issue_key}...")
            result = jira.add_comment(issue_key, error_response)
            if result.get("success"):
                print(f"✅ Error posted to {issue_key}")
            else:
                print(f"❌ Failed to post error: {result.get('error')}")

        print("=" * 80 + "\n")
