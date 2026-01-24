"""GitHub API client."""

import base64

import httpx

from config import config


class GitHubClient:
    """Client for GitHub API."""

    def __init__(self):
        self.base_url = "https://api.github.com"
        self.org = config.GITHUB_ORG
        self.token = config.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def search_code(self, repo: str, query: str) -> dict:
        """
        Search for code in a repository.

        Args:
            repo: Repository name (e.g., 'appian-frontend')
            query: Search query

        Returns:
            Dict with matches and total count
        """
        if not self.token:
            return {"error": "GITHUB_TOKEN not configured"}

        try:
            response = httpx.get(
                f"{self.base_url}/search/code",
                headers=self.headers,
                params={"q": f"{query} repo:{self.org}/{repo}"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("items", [])[:10]:  # Top 10 results
                results.append({"path": item["path"], "url": item.get("html_url")})

            return {"matches": results, "total_count": data.get("total_count", 0)}

        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to search code: {str(e)}"}

    def read_file(self, repo: str, path: str, branch: str = "main") -> dict:
        """
        Read file contents from repository.

        Args:
            repo: Repository name
            path: File path from repo root
            branch: Branch name (default: main)

        Returns:
            Dict with file content
        """
        if not self.token:
            return {"error": "GITHUB_TOKEN not configured"}

        try:
            response = httpx.get(
                f"{self.base_url}/repos/{self.org}/{repo}/contents/{path}",
                headers=self.headers,
                params={"ref": branch},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            # Decode base64 content
            content = base64.b64decode(data["content"]).decode("utf-8")

            return {
                "path": path,
                "content": content,
                "sha": data["sha"],
                "size": data["size"],
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}

    def list_directory(self, repo: str, path: str = "") -> dict:
        """
        List directory contents.

        Args:
            repo: Repository name
            path: Directory path (empty for root)

        Returns:
            Dict with items list
        """
        if not self.token:
            return {"error": "GITHUB_TOKEN not configured"}

        try:
            response = httpx.get(
                f"{self.base_url}/repos/{self.org}/{repo}/contents/{path}",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            items = []
            for item in data:
                items.append(
                    {
                        "name": item["name"],
                        "type": item["type"],  # "file" or "dir"
                        "path": item["path"],
                    }
                )

            return {"items": items}

        except httpx.HTTPStatusError as e:
            return {"error": f"GitHub API error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to list directory: {str(e)}"}


# Singleton instance
github = GitHubClient()
