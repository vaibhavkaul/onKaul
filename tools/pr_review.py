"""GitHub Pull Request review tool."""

import json
import re
import subprocess


def extract_pr_url(text: str) -> str | None:
    """
    Extract GitHub PR URL from text.

    Args:
        text: Text that may contain a PR URL

    Returns:
        PR URL if found, None otherwise
    """
    # Match full PR URLs
    match = re.search(r"https://github\.com/([\w-]+)/([\w-]+)/pull/(\d+)", text)
    if match:
        return match.group(0)

    # Match short form like "appian-frontend#1234"
    match = re.search(r"(appian-frontend|appian-server|tts-business)#(\d+)", text)
    if match:
        return f"https://github.com/taptapsend/{match.group(1)}/pull/{match.group(2)}"

    return None


def is_pr_review_request(text: str) -> bool:
    """
    Check if message is requesting a PR review.

    Args:
        text: Message text

    Returns:
        True if this is a PR review request
    """
    # Check for review keywords + PR URL
    has_review_keyword = bool(
        re.search(r"\b(review|check|analyze)\b", text, re.IGNORECASE)
    )
    has_pr_reference = bool(
        re.search(r"\b(PR|pull request|github\.com/[\w-]+/[\w-]+/pull/)\b", text, re.IGNORECASE)
    )

    return has_review_keyword and has_pr_reference


def review_github_pr(pr_url: str) -> dict:
    """
    Fetch GitHub PR details and diff for review.

    Args:
        pr_url: GitHub PR URL or number with repo (e.g., 'appian-frontend#1234')

    Returns:
        Dict with PR metadata and diff
    """
    try:
        # Fetch PR metadata
        metadata_result = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                pr_url,
                "--json",
                "title,number,author,body,state,headRefName,baseRefName,url",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if metadata_result.returncode != 0:
            return {"error": f"Failed to fetch PR: {metadata_result.stderr}"}

        metadata = json.loads(metadata_result.stdout)

        # Extract repo from URL
        repo_name = None
        if "url" in metadata:
            # URL format: https://github.com/org/repo/pull/123
            parts = metadata["url"].split("/")
            if len(parts) >= 5:
                repo_name = f"{parts[3]}/{parts[4]}"  # org/repo

        # Fetch PR diff
        diff_result = subprocess.run(
            ["gh", "pr", "diff", pr_url],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if diff_result.returncode != 0:
            return {"error": f"Failed to fetch diff: {diff_result.stderr}"}

        return {
            "pr_number": metadata.get("number"),
            "title": metadata.get("title"),
            "author": metadata.get("author", {}).get("login"),
            "description": metadata.get("body", ""),
            "repository": repo_name,
            "state": metadata.get("state"),
            "head_branch": metadata.get("headRefName"),
            "base_branch": metadata.get("baseRefName"),
            "diff": diff_result.stdout,
            "pr_url": metadata.get("url", pr_url),
        }

    except subprocess.TimeoutExpired:
        return {"error": "gh command timed out"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse gh output"}
    except FileNotFoundError:
        return {"error": "gh CLI not installed or not in PATH"}
    except Exception as e:
        return {"error": f"Failed to review PR: {str(e)}"}


def post_pr_review_comment(pr_url: str, review_text: str) -> dict:
    """
    Post a review comment to a GitHub PR.

    Args:
        pr_url: GitHub PR URL
        review_text: Markdown formatted review text

    Returns:
        Dict with comment URL and success status
    """
    try:
        # Post comment using gh CLI
        result = subprocess.run(
            ["gh", "pr", "comment", pr_url, "--body", review_text],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"error": f"Failed to post comment: {result.stderr}", "success": False}

        # gh pr comment returns the comment URL in stdout
        comment_url = result.stdout.strip()

        return {
            "success": True,
            "comment_url": comment_url,
            "message": "Review posted to GitHub PR",
        }

    except subprocess.TimeoutExpired:
        return {"error": "gh command timed out", "success": False}
    except Exception as e:
        return {"error": f"Failed to post comment: {str(e)}", "success": False}


def generate_review_summary(review_text: str, pr_data: dict, comment_url: str) -> str:
    """
    Generate a summary of the PR review for Slack/Jira.

    Args:
        review_text: Full review text
        pr_data: PR metadata
        comment_url: URL to GitHub comment

    Returns:
        Summary text for posting to Slack/Jira
    """
    # Count issues by priority
    high_count = len(re.findall(r"(?:^|\n)[-•]\s+", review_text.split("### 📋 Medium Priority")[0].split("### ⚠️ High Priority")[-1]))
    medium_match = re.search(r"### 📋 Medium Priority(.*?)(?:###|$)", review_text, re.DOTALL)
    medium_count = len(re.findall(r"(?:^|\n)[-•]\s+", medium_match.group(1))) if medium_match else 0

    nice_match = re.search(r"### ✨ Nice to Have(.*?)(?:###|$)", review_text, re.DOTALL)
    nice_count = len(re.findall(r"(?:^|\n)[-•]\s+", nice_match.group(1))) if nice_match else 0

    nits_match = re.search(r"### 🔍 Nits(.*?)(?:###|$)", review_text, re.DOTALL)
    nits_count = len(re.findall(r"(?:^|\n)[-•]\s+", nits_match.group(1))) if nits_match else 0

    # Build summary
    summary = f"""✅ **PR Review Complete**

**PR #{pr_data.get('pr_number')}**: {pr_data.get('title')}
**Author**: {pr_data.get('author')}

**Summary:**
- ⚠️ High Priority: {high_count} issue{'s' if high_count != 1 else ''}
- 📋 Medium Priority: {medium_count} issue{'s' if medium_count != 1 else ''}
- ✨ Nice to Have: {nice_count} suggestion{'s' if nice_count != 1 else ''}
- 🔍 Nits: {nits_count} item{'s' if nits_count != 1 else ''}

🔗 Full review: {comment_url}"""

    return summary
