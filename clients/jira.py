"""Jira client using acli CLI."""

import json
import subprocess


class JiraClient:
    """Client for Jira using acli CLI."""

    def query_issues(self, jql: str) -> dict:
        """
        Search Jira issues using JQL.

        Args:
            jql: JQL query string

        Returns:
            Dict with matching issues
        """
        try:
            result = subprocess.run(
                ["acli", "jira", "workitem", "search", "--jql", jql, "--json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {"error": f"acli error: {result.stderr}"}

            # Parse JSON output
            data = json.loads(result.stdout)
            issues = []

            # Extract relevant fields (same structure as get_issue)
            for issue in data:
                fields = issue.get("fields", {})
                status_data = fields.get("status", {})
                issuetype_data = fields.get("issuetype", {})

                issues.append(
                    {
                        "key": issue.get("key"),
                        "summary": fields.get("summary"),
                        "status": status_data.get("name") if status_data else None,
                        "type": issuetype_data.get("name") if issuetype_data else None,
                    }
                )

            return {"issues": issues, "total": len(issues)}

        except subprocess.TimeoutExpired:
            return {"error": "acli command timed out"}
        except json.JSONDecodeError:
            return {"error": "Failed to parse acli JSON output"}
        except FileNotFoundError:
            return {"error": "acli not installed or not in PATH"}
        except Exception as e:
            return {"error": f"Failed to query Jira: {str(e)}"}

    def get_issue(self, issue_key: str) -> dict:
        """
        Get full details of a Jira issue including comments.

        Args:
            issue_key: Jira issue key (e.g., 'B2B-456')

        Returns:
            Dict with issue details and comments
        """
        try:
            result = subprocess.run(
                ["acli", "jira", "workitem", "view", issue_key, "--json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {"error": f"acli error: {result.stderr}"}

            # Parse JSON output
            data = json.loads(result.stdout)
            fields = data.get("fields", {})

            # Extract description from Atlassian Document Format (ADF)
            description = self._extract_adf_text(fields.get("description"))

            # Extract assignee
            assignee_data = fields.get("assignee")
            assignee = assignee_data.get("displayName") if assignee_data else None

            # Extract reporter
            reporter_data = fields.get("reporter")
            reporter = reporter_data.get("displayName") if reporter_data else None

            # Extract status
            status_data = fields.get("status", {})
            status = status_data.get("name") if status_data else None

            # Extract issue type
            issuetype_data = fields.get("issuetype", {})
            issue_type = issuetype_data.get("name") if issuetype_data else None

            # Extract components
            components = [c.get("name") for c in fields.get("components", []) if c.get("name")]

            # Fetch comments separately
            comments = self._get_comments(issue_key)

            return {
                "key": data.get("key"),
                "summary": fields.get("summary"),
                "description": description,
                "status": status,
                "type": issue_type,
                "assignee": assignee,
                "reporter": reporter,
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "components": components,
                "labels": fields.get("labels", []),
                "comments": comments,
            }

        except subprocess.TimeoutExpired:
            return {"error": "acli command timed out"}
        except json.JSONDecodeError:
            return {"error": "Failed to parse acli JSON output"}
        except FileNotFoundError:
            return {"error": "acli not installed or not in PATH"}
        except Exception as e:
            return {"error": f"Failed to get Jira issue: {str(e)}"}

    def _extract_adf_text(self, adf_content) -> str:
        """Extract plain text from Atlassian Document Format."""
        if not adf_content:
            return ""

        text_parts = []

        def walk(node):
            if isinstance(node, dict):
                # Text nodes have the actual text
                if node.get("type") == "text":
                    text_parts.append(node.get("text", ""))
                # Recurse into content
                for child in node.get("content", []):
                    walk(child)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(adf_content)
        return " ".join(text_parts)

    def _get_comments(self, issue_key: str) -> list:
        """
        Fetch comments for a Jira issue.

        Args:
            issue_key: Jira issue key

        Returns:
            List of comments with author and body
        """
        try:
            result = subprocess.run(
                ["acli", "jira", "workitem", "comment", "list", "--key", issue_key, "--json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                # If comments fail, return empty list rather than failing whole request
                return []

            # Parse JSON output
            data = json.loads(result.stdout)
            comments_data = data.get("comments", [])

            comments = []
            for comment in comments_data:
                comments.append(
                    {
                        "author": comment.get("author", "Unknown"),
                        "body": comment.get("body", ""),
                        "id": comment.get("id"),
                    }
                )

            return comments

        except Exception:
            # If comments fail, return empty list
            return []

    def add_comment(self, issue_key: str, comment: str) -> dict:
        """
        Add a comment to a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., 'B2B-333')
            comment: Comment text to add

        Returns:
            Dict with success/error status
        """
        try:
            result = subprocess.run(
                [
                    "acli",
                    "jira",
                    "workitem",
                    "comment",
                    "create",
                    "--key",
                    issue_key,
                    "--body",
                    comment,
                ],
                capture_output=True,
                text=True,
                timeout=30,  # Increased timeout for longer comments
            )

            if result.returncode != 0:
                return {"error": f"acli error: {result.stderr}", "success": False}

            return {"success": True, "message": f"Comment added to {issue_key}"}

        except subprocess.TimeoutExpired:
            return {"error": "acli command timed out", "success": False}
        except FileNotFoundError:
            return {"error": "acli not installed or not in PATH", "success": False}
        except Exception as e:
            return {"error": f"Failed to add comment: {str(e)}", "success": False}


# Singleton instance
jira = JiraClient()
