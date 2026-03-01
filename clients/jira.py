"""Jira client using Jira REST API v3."""

import httpx

from config import config

# Fields to request when fetching an issue
_ISSUE_FIELDS = (
    "summary,description,status,issuetype,assignee,reporter,created,updated,components,labels"
)


class JiraClient:
    """Client for Jira REST API v3."""

    def _auth(self) -> tuple[str, str]:
        return (config.JIRA_EMAIL, config.JIRA_API_TOKEN)

    def _base(self) -> str:
        return config.JIRA_BASE_URL.rstrip("/")

    def _headers(self) -> dict:
        return {"Accept": "application/json", "Content-Type": "application/json"}

    def query_issues(self, jql: str) -> dict:
        """Search Jira issues using JQL."""
        if not config.JIRA_EMAIL or not config.JIRA_API_TOKEN:
            return {"error": "JIRA_EMAIL or JIRA_API_TOKEN not configured"}

        try:
            response = httpx.get(
                f"{self._base()}/rest/api/3/search",
                auth=self._auth(),
                headers=self._headers(),
                params={"jql": jql, "fields": "summary,status,issuetype", "maxResults": 50},
                timeout=15.0,
            )
            if response.status_code != 200:
                return {"error": f"Jira API error: {response.status_code} {response.text}"}

            data = response.json()
            issues = []
            for issue in data.get("issues", []):
                fields = issue.get("fields", {})
                issues.append(
                    {
                        "key": issue.get("key"),
                        "summary": fields.get("summary"),
                        "status": (fields.get("status") or {}).get("name"),
                        "type": (fields.get("issuetype") or {}).get("name"),
                    }
                )

            return {"issues": issues, "total": data.get("total", len(issues))}

        except httpx.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to query Jira: {str(e)}"}

    def get_issue(self, issue_key: str) -> dict:
        """Get full details of a Jira issue including comments."""
        if not config.JIRA_EMAIL or not config.JIRA_API_TOKEN:
            return {"error": "JIRA_EMAIL or JIRA_API_TOKEN not configured"}

        try:
            response = httpx.get(
                f"{self._base()}/rest/api/3/issue/{issue_key}",
                auth=self._auth(),
                headers=self._headers(),
                params={"fields": _ISSUE_FIELDS},
                timeout=15.0,
            )
            if response.status_code != 200:
                return {"error": f"Jira API error: {response.status_code} {response.text}"}

            data = response.json()
            fields = data.get("fields", {})

            assignee_data = fields.get("assignee")
            reporter_data = fields.get("reporter")

            return {
                "key": data.get("key"),
                "summary": fields.get("summary"),
                "description": self._extract_adf_text(fields.get("description")),
                "status": (fields.get("status") or {}).get("name"),
                "type": (fields.get("issuetype") or {}).get("name"),
                "assignee": assignee_data.get("displayName") if assignee_data else None,
                "reporter": reporter_data.get("displayName") if reporter_data else None,
                "created": fields.get("created"),
                "updated": fields.get("updated"),
                "components": [
                    c.get("name") for c in fields.get("components", []) if c.get("name")
                ],
                "labels": fields.get("labels", []),
                "comments": self._get_comments(issue_key),
            }

        except httpx.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to get Jira issue: {str(e)}"}

    def _get_comments(self, issue_key: str) -> list:
        """Fetch comments for a Jira issue."""
        try:
            response = httpx.get(
                f"{self._base()}/rest/api/3/issue/{issue_key}/comment",
                auth=self._auth(),
                headers=self._headers(),
                params={"orderBy": "created", "maxResults": 50},
                timeout=15.0,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            return [
                {
                    "id": c.get("id"),
                    "author": (c.get("author") or {}).get("displayName", "Unknown"),
                    "body": self._extract_adf_text(c.get("body")),
                    "created": c.get("created"),
                }
                for c in data.get("comments", [])
            ]

        except Exception:
            return []

    def add_comment(self, issue_key: str, comment: str, adf_body: dict | None = None) -> dict:
        """Add a comment to a Jira issue in ADF format."""
        if not config.JIRA_EMAIL or not config.JIRA_API_TOKEN:
            return {"error": "JIRA_EMAIL or JIRA_API_TOKEN not configured", "success": False}

        body = adf_body or {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}],
        }

        try:
            response = httpx.post(
                f"{self._base()}/rest/api/3/issue/{issue_key}/comment",
                auth=self._auth(),
                headers=self._headers(),
                json={"body": body},
                timeout=30.0,
            )
            if response.status_code == 201:
                return {
                    "success": True,
                    "message": f"Comment added to {issue_key}",
                    "comment_id": response.json().get("id"),
                }
            return {
                "error": f"Jira API error: {response.status_code} {response.text}",
                "success": False,
            }

        except httpx.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}", "success": False}
        except Exception as e:
            return {"error": f"Failed to add comment: {str(e)}", "success": False}

    def _extract_adf_text(self, adf_content) -> str:
        """Extract plain text from Atlassian Document Format."""
        if not adf_content:
            return ""
        parts: list[str] = []

        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    parts.append(node.get("text", ""))
                for child in node.get("content", []):
                    walk(child)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(adf_content)
        return " ".join(parts)


# Singleton instance
jira = JiraClient()
