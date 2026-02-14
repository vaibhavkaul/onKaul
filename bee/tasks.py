"""RQ task entrypoints for worker bees."""

from worker.tasks import handle_jira_mention, handle_slack_mention


def handle_slack_mention_job(
    channel: str,
    thread_ts: str,
    user_message: str,
    user_id: str,
    thread_context: list | None = None,
    attachments: list | None = None,
):
    """RQ job wrapper for Slack mentions."""
    return handle_slack_mention(
        channel=channel,
        thread_ts=thread_ts,
        user_message=user_message,
        user_id=user_id,
        thread_context=thread_context,
        attachments=attachments,
    )


def handle_jira_mention_job(
    issue_key: str,
    comment_body: str,
    author: str,
):
    """RQ job wrapper for Jira mentions."""
    return handle_jira_mention(
        issue_key=issue_key,
        comment_body=comment_body,
        author=author,
    )
