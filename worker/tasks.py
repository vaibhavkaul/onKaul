"""Background task handlers for webhook processing."""

import time

from agent.core import agent
from clients.jira import jira
from clients.slack import slack
from config import config
from tools.pr_review import (
    is_pr_review_request,
    extract_pr_url,
    review_github_pr,
    post_pr_review_comment,
    generate_review_summary,
)
from utils.jira_formatter import markdown_to_adf
from utils.logger import logger
from utils.slack_formatter import format_for_slack


def handle_slack_mention(
    channel: str,
    thread_ts: str,
    user_message: str,
    user_id: str,
    thread_context: list | None = None,
    attachments: list | None = None,
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
    print(f"📎 Attachments: {len(attachments) if attachments else 0} files")
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

        # Add attachment text to context if available
        if attachments:
            print("📎 Adding attachment text to context...")
            context += "\n\n## Attached Files\n"
            for att in attachments:
                filename = att.get("filename", "unknown")
                extracted = att.get("extracted_text", "")
                if extracted:
                    context += f"\n**{filename}**:\n```\n{extracted[:2000]}\n```\n"
                    print(f"  ✅ Added text from {filename} ({len(extracted)} chars)")
            print(f"✅ Processed {len(attachments)} attachment(s)")

        # Check if this is a PR review request
        if is_pr_review_request(user_message):
            print("🔍 Detected PR review request")
            pr_url = extract_pr_url(user_message)
            if pr_url:
                print(f"📋 PR URL: {pr_url}")
                print("🧠 Calling agent for PR review...")

                # Fetch PR data first
                pr_data = review_github_pr(pr_url)
                if "error" in pr_data:
                    response = f"❌ Failed to fetch PR: {pr_data['error']}"
                else:
                    # Build review context
                    review_context = f"""Please review this Pull Request:

**PR #{pr_data['pr_number']}**: {pr_data['title']}
**Author**: {pr_data['author']}
**Repository**: {pr_data['repository']}

**Description:**
{pr_data.get('description', 'No description provided')[:1000]}

**Changes:**
```diff
{pr_data['diff'][:10000]}
```

Provide a comprehensive code review with the 4-tier priority structure."""

                    # Agent reviews (uses Opus automatically)
                    response = agent.investigate(review_context, context="")
                    print(f"✅ Review complete ({len(response)} chars)")

                    # Post review to GitHub
                    print("📤 Posting review to GitHub PR...")
                    comment_result = post_pr_review_comment(pr_url, response)

                    if comment_result.get("success"):
                        comment_url = comment_result.get("comment_url")
                        print(f"✅ Posted to GitHub: {comment_url}")

                        # Generate summary for Slack
                        response = generate_review_summary(response, pr_data, comment_url)
                        print(f"📝 Generated summary for Slack ({len(response)} chars)")
                    else:
                        print(f"❌ Failed to post to GitHub: {comment_result.get('error')}")
                        # Keep full review as response if GitHub posting fails

                print("-" * 80)
            else:
                response = "I couldn't find a GitHub PR URL in your message. Please provide a link like: https://github.com/taptapsend/appian-frontend/pull/1234"
                print("-" * 80)
        else:
            # Regular investigation (not a PR review)
            print("🧠 Calling agent...")
            # Real agent investigation with thread context and history
            response = agent.investigate(user_message, context=context, thread_history=thread_context)
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

        # Check if this is a PR review request
        if is_pr_review_request(comment_body):
            print("🔍 Detected PR review request")
            pr_url = extract_pr_url(comment_body)
            if pr_url:
                print(f"📋 PR URL: {pr_url}")
                print("🧠 Calling agent for PR review...")

                # Fetch PR data
                pr_data = review_github_pr(pr_url)
                if "error" in pr_data:
                    response = f"❌ Failed to fetch PR: {pr_data['error']}"
                else:
                    # Build review context
                    review_context = f"""Please review this Pull Request:

**PR #{pr_data['pr_number']}**: {pr_data['title']}
**Author**: {pr_data['author']}
**Repository**: {pr_data['repository']}

**Description:**
{pr_data.get('description', 'No description provided')[:1000]}

**Changes:**
```diff
{pr_data['diff'][:10000]}
```

Provide a comprehensive code review with the 4-tier priority structure."""

                    # Agent reviews
                    response = agent.investigate(review_context, context=context)
                    print(f"✅ Review complete ({len(response)} chars)")

                    # Post review to GitHub
                    print("📤 Posting review to GitHub PR...")
                    comment_result = post_pr_review_comment(pr_url, response)

                    if comment_result.get("success"):
                        comment_url = comment_result.get("comment_url")
                        print(f"✅ Posted to GitHub: {comment_url}")

                        # Generate summary for Jira
                        response = generate_review_summary(response, pr_data, comment_url)
                        print(f"📝 Generated summary for Jira ({len(response)} chars)")
                    else:
                        print(f"❌ Failed to post to GitHub: {comment_result.get('error')}")

                print("-" * 80)
            else:
                response = "I couldn't find a GitHub PR URL in your comment. Please provide a link like: https://github.com/taptapsend/appian-frontend/pull/1234"
                print("-" * 80)
        else:
            # Regular investigation (not a PR review)
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
            print(f"🎨 Converting markdown to ADF format...")
            adf_body = markdown_to_adf(response)
            result = jira.add_comment(issue_key, None, adf_body=adf_body)
            if result.get("success"):
                print(f"✅ Successfully posted to {issue_key} (ADF formatted)")
                print(f"🔗 View at: https://taptapsend.atlassian.net/browse/{issue_key}")
                if result.get("comment_id"):
                    print(f"📝 Comment ID: {result['comment_id']}")
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
            adf_body = markdown_to_adf(error_response)
            result = jira.add_comment(issue_key, None, adf_body=adf_body)
            if result.get("success"):
                print(f"✅ Error posted to {issue_key}")
            else:
                print(f"❌ Failed to post error: {result.get('error')}")

        print("=" * 80 + "\n")
