"""Background task handlers for webhook processing."""

import time

from agent.core import agent
from clients.jira import jira
from clients.slack import slack
from config import config
from tools.regulatory import (
    extract_regulatory_url,
    is_regulatory_request,
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

    Performs investigation with full thread context, attachments, and tool access.
    Posts responses to Slack if ENABLE_SLACK_POSTING=true.
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

        # Check if this is a regulatory publication request
        if is_regulatory_request(user_message):
            print("📋 Detected regulatory publication request")
            reg_url = extract_regulatory_url(user_message)
            if reg_url:
                print(f"🔗 URL: {reg_url}")
                print("📥 Fetching regulatory publication...")

                # Fetch page content
                import httpx

                try:
                    page_response = httpx.get(reg_url, timeout=30, follow_redirects=True)
                    if page_response.status_code == 200:
                        html_content = page_response.text
                        print(f"✅ Fetched page ({len(html_content)} chars)")

                        # Ask Claude to extract structured data
                        extraction_prompt = f"""Extract regulatory publication information from this webpage:

**URL:** {reg_url}

**Task:** Extract the following fields:
1. **Jurisdiction** - Which country/region (e.g., UK, US, Dubai, Singapore)
2. **Date of Implementation** - When this regulation takes effect (extract from content or URL)
3. **Summary** - One sentence describing what the publication is, then summarize the calls to action in 3 short bullet points for a payments firm doing regulatory horizon scanning

**Provide response in this exact format:**

Jurisdiction: [jurisdiction]

Date of Implementation: [date]

Summary:
[One sentence description of the publication]

Calls to Action:
1. [First action in ~20 words]
2. [Second action in ~20 words]
3. [Third action in ~20 words]

---

**Page Content (first 20,000 chars):**
{html_content[:20000]}
"""

                        print("🧠 Calling agent to extract regulatory info...")
                        response = agent.investigate(extraction_prompt, context="")
                        print(f"✅ Extraction complete ({len(response)} chars)")
                        print("-" * 80)

                    else:
                        response = (
                            f"❌ Failed to fetch regulatory page: HTTP {page_response.status_code}"
                        )
                        print("-" * 80)

                except Exception as e:
                    response = f"❌ Failed to fetch regulatory page: {str(e)}"
                    print(f"❌ Error: {str(e)}")
                    print("-" * 80)
            else:
                response = "I couldn't find a regulatory publication URL in your message. Please provide a link to FCA, SEC, FinCEN, DFSA, MAS, or other regulatory authority."
                print("-" * 80)

        else:
            # Regular investigation (not a PR review)
            print("🧠 Calling agent...")
            # Real agent investigation with thread context and history
            response = agent.investigate(
                user_message, context=context, thread_history=thread_context
            )
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
                print("✅ Successfully posted to Slack")
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
                print("✅ Error posted to Slack")
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

    Performs investigation and posts ADF-formatted responses to Jira if enabled.
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

        # Check if this is a regulatory publication request
        if is_regulatory_request(comment_body):
            print("📋 Detected regulatory publication request")
            reg_url = extract_regulatory_url(comment_body)
            if reg_url:
                print(f"🔗 URL: {reg_url}")
                print("📥 Fetching regulatory publication...")

                # Fetch page content
                import httpx

                try:
                    page_response = httpx.get(reg_url, timeout=30, follow_redirects=True)
                    if page_response.status_code == 200:
                        html_content = page_response.text
                        print(f"✅ Fetched page ({len(html_content)} chars)")

                        # Ask Claude to extract structured data
                        extraction_prompt = f"""Extract regulatory publication information from this webpage:

**URL:** {reg_url}

**CRITICAL:** Follow this EXACT format with each field on its own line:

Jurisdiction: [jurisdiction]

Date of Implementation: [date]

Summary:
[One sentence description of what the publication is about]

Calls to Action:
1. [First action - be specific and actionable, ~20 words]
2. [Second action - be specific and actionable, ~20 words]
3. [Third action - be specific and actionable, ~20 words]

**Requirements:**
- Put "Jurisdiction:" and "Date of Implementation:" on SEPARATE lines with blank line between
- Extract implementation date from page content, meta tags, or URL
- Summary should be ONE clear sentence explaining the publication's purpose
- Calls to action should be what a payments firm needs to DO (monitor, implement, review, update, etc.)

---

**Page Content (first 20,000 chars):**
{html_content[:20000]}
"""

                        print("🧠 Calling agent to extract regulatory info...")
                        response = agent.investigate(extraction_prompt, context=context)
                        print(f"✅ Extraction complete ({len(response)} chars)")
                        print("-" * 80)

                    else:
                        response = (
                            f"❌ Failed to fetch regulatory page: HTTP {page_response.status_code}"
                        )
                        print("-" * 80)

                except Exception as e:
                    response = f"❌ Failed to fetch regulatory page: {str(e)}"
                    print(f"❌ Error: {str(e)}")
                    print("-" * 80)
            else:
                response = "I couldn't find a regulatory publication URL in your comment. Please provide a link to FCA, SEC, FinCEN, DFSA, MAS, or other regulatory authority."
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

        # Post to Jira if enabled
        if config.ENABLE_JIRA_POSTING:
            print(f"📤 Posting comment to {issue_key}...")
            print("🎨 Converting markdown to ADF format...")
            adf_body = markdown_to_adf(response)
            result = jira.add_comment(issue_key, None, adf_body=adf_body)
            if result.get("success"):
                print(f"✅ Successfully posted to {issue_key} (ADF formatted)")
                if config.JIRA_BASE_URL:
                    print(f"🔗 View at: {config.JIRA_BASE_URL}/browse/{issue_key}")
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
