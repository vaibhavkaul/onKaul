"""Background task handlers for webhook processing."""

import time

from utils.logger import logger


def handle_slack_mention(
    channel: str,
    thread_ts: str,
    user_message: str,
    user_id: str,
):
    """
    Handle a Slack mention.

    Phase 1: Stub response, just log.
    Phase 2: Call agent for real investigation.
    Phase 3: Post back to Slack instead of logging.
    """
    start_time = time.time()

    try:
        # Phase 1: Stub response
        response = _generate_stub_response("slack", user_message)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log instead of posting
        logger.log_response(
            source="slack",
            response=response,
            metadata={
                "channel": channel,
                "thread_ts": thread_ts,
                "user_message": user_message,
                "user_id": user_id,
            },
            investigation_duration_ms=duration_ms,
        )

    except Exception as e:
        # Log error response
        error_response = f"Sorry, I encountered an error: {str(e)}"
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


def handle_jira_mention(
    issue_key: str,
    comment_body: str,
    author: str,
):
    """
    Handle a Jira mention.

    Phase 1: Stub response, just log.
    Phase 2: Call agent for real investigation.
    Phase 3: Post back to Jira instead of logging.
    """
    start_time = time.time()

    try:
        # Phase 1: Stub response
        response = _generate_stub_response("jira", comment_body)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log instead of posting
        logger.log_response(
            source="jira",
            response=response,
            metadata={
                "issue_key": issue_key,
                "comment_body": comment_body,
                "author": author,
            },
            investigation_duration_ms=duration_ms,
        )

    except Exception as e:
        # Log error response
        error_response = f"Sorry, I encountered an error: {str(e)}"
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


def _generate_stub_response(source: str, user_message: str) -> str:
    """
    Generate a stub response for Phase 1 testing.

    Phase 2: Replace with actual agent investigation.
    """
    return f"""👀 Looking into this...

**[STUB RESPONSE - Phase 1]**

I received your request from {source}:
> {user_message}

In Phase 2, I'll investigate using:
- Sentry error details
- GitHub code search
- Datadog logs
- Jira issue context

And provide:
🔍 Investigation breadcrumbs
📊 Confidence score
⚠️ Impact assessment
📝 Findings with file references
💻 Claude Code prompt for fixes

For now, I'm just logging this response instead of posting back to {source}.
"""
