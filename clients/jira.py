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

            # Extract relevant fields
            for issue in data:
                issues.append(
                    {
                        "key": issue.get("key"),
                        "summary": issue.get("summary"),
                        "status": issue.get("status"),
                        "type": issue.get("type"),
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
        Get full details of a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., 'B2B-456')

        Returns:
            Dict with issue details
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

            return {
                "key": data.get("key"),
                "summary": data.get("summary"),
                "description": data.get("description"),
                "status": data.get("status"),
                "type": data.get("type"),
                "assignee": data.get("assignee"),
                "reporter": data.get("reporter"),
                "created": data.get("created"),
                "updated": data.get("updated"),
                "components": data.get("components", []),
                "labels": data.get("labels", []),
            }

        except subprocess.TimeoutExpired:
            return {"error": "acli command timed out"}
        except json.JSONDecodeError:
            return {"error": "Failed to parse acli JSON output"}
        except FileNotFoundError:
            return {"error": "acli not installed or not in PATH"}
        except Exception as e:
            return {"error": f"Failed to get Jira issue: {str(e)}"}


# Singleton instance
jira = JiraClient()
