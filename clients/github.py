"""GitHub client using gh CLI."""

import json
import subprocess

from config import config


class GitHubClient:
    """Client for GitHub using gh CLI."""

    def __init__(self):
        self.org = config.GITHUB_ORG

    def search_code(self, repo: str, query: str) -> dict:
        """
        Search for code in a repository.

        Args:
            repo: Repository name (e.g., 'appian-frontend')
            query: Search query

        Returns:
            Dict with matches and total count
        """
        try:
            # Use gh search code command
            result = subprocess.run(
                [
                    "gh",
                    "search",
                    "code",
                    query,
                    "--repo",
                    f"{self.org}/{repo}",
                    "--json",
                    "path,repository",
                    "--limit",
                    "10",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {"error": f"gh error: {result.stderr}"}

            # Parse JSON output
            data = json.loads(result.stdout)
            results = []

            for item in data:
                repo_name = item.get("repository", {}).get("name", repo)
                path = item.get("path", "")
                results.append(
                    {
                        "path": path,
                        "url": f"https://github.com/{self.org}/{repo_name}/blob/main/{path}",
                    }
                )

            return {"matches": results, "total_count": len(results)}

        except subprocess.TimeoutExpired:
            return {"error": "gh command timed out"}
        except json.JSONDecodeError:
            return {"error": "Failed to parse gh JSON output"}
        except FileNotFoundError:
            return {"error": "gh CLI not installed or not in PATH"}
        except Exception as e:
            return {"error": f"Failed to search code: {str(e)}"}

    def read_file(self, repo: str, path: str, branch: str = "main") -> dict:
        """
        Read file contents from repository.

        Args:
            repo: Repository name
            path: File path from repo root
            branch: Branch name (default: main) - currently ignored, uses default branch

        Returns:
            Dict with file content
        """
        try:
            # Use gh api to read file contents
            # Note: Not specifying branch - uses repo's default branch
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{self.org}/{repo}/contents/{path}",
                    "--jq",
                    ".content",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {"error": f"gh error: {result.stderr}"}

            # Decode base64 content
            import base64

            content = base64.b64decode(result.stdout.strip()).decode("utf-8")

            return {
                "path": path,
                "content": content,
                "branch": branch,  # Requested branch (not actually used)
            }

        except subprocess.TimeoutExpired:
            return {"error": "gh command timed out"}
        except FileNotFoundError:
            return {"error": "gh CLI not installed or not in PATH"}
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
        try:
            # Use gh api to list directory
            api_path = (
                f"repos/{self.org}/{repo}/contents/{path}"
                if path
                else f"repos/{self.org}/{repo}/contents"
            )

            result = subprocess.run(
                ["gh", "api", api_path, "--jq", ".[].name,.[].type,.[].path"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {"error": f"gh error: {result.stderr}"}

            # Parse output (3 lines per item: name, type, path)
            lines = result.stdout.strip().split("\n")
            items = []

            for i in range(0, len(lines), 3):
                if i + 2 < len(lines):
                    items.append(
                        {
                            "name": lines[i],
                            "type": lines[i + 1],
                            "path": lines[i + 2],
                        }
                    )

            return {"items": items}

        except subprocess.TimeoutExpired:
            return {"error": "gh command timed out"}
        except FileNotFoundError:
            return {"error": "gh CLI not installed or not in PATH"}
        except Exception as e:
            return {"error": f"Failed to list directory: {str(e)}"}


# Singleton instance
github = GitHubClient()
