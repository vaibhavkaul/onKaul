"""Background task handlers for webhook processing."""

import time

from agent.core import agent
from utils.logger import logger


def handle_slack_mention(
    channel: str,
    thread_ts: str,
    user_message: str,
    user_id: str,
):
    """
    Handle a Slack mention.

    Phase 2: Use agent for real investigation.
    Phase 3: Post back to Slack instead of logging.
    """
    start_time = time.time()

    try:
        # Phase 2: Real agent investigation
        response = agent.investigate(user_message)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log instead of posting (still logging in Phase 2!)
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

    Phase 2: Use agent for real investigation.
    Phase 3: Post back to Jira instead of logging.
    """
    start_time = time.time()

    try:
        # Build context from Jira issue
        context = f"Jira Issue: {issue_key}\nComment from {author}"

        # Phase 2: Real agent investigation
        response = agent.investigate(comment_body, context=context)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log instead of posting (still logging in Phase 2!)
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
