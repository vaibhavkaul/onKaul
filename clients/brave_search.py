"""Brave Search API client for web research."""

import httpx

from config import config


class BraveSearchClient:
    """Client for Brave Search API."""

    def __init__(self):
        self.api_key = config.BRAVE_SEARCH_API_KEY
        self.base_url = "https://api.search.brave.com/res/v1"

    def search(self, query: str, count: int = 5) -> dict:
        """
        Search the web using Brave Search API.

        Args:
            query: Search query
            count: Number of results to return (default: 5, max: 20)

        Returns:
            Dict with search results (title, url, description)
        """
        if not self.api_key:
            return {
                "error": "Brave Search API key not configured",
                "message": "Set BRAVE_SEARCH_API_KEY in .env to enable web search",
            }

        try:
            response = httpx.get(
                f"{self.base_url}/web/search",
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self.api_key,
                },
                params={"q": query, "count": min(count, 20)},
                timeout=30.0,
            )

            if response.status_code != 200:
                return {
                    "error": f"Brave Search API error: {response.status_code}",
                    "message": response.text[:200],
                }

            data = response.json()

            # Extract web results
            web_results = data.get("web", {}).get("results", [])

            results = []
            for result in web_results[:count]:
                results.append(
                    {
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "description": result.get("description"),
                    }
                )

            return {
                "query": query,
                "results": results,
                "total": len(results),
            }

        except httpx.TimeoutException:
            return {"error": "Brave Search request timed out"}
        except httpx.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to search: {str(e)}"}


# Singleton instance
brave_search = BraveSearchClient()
