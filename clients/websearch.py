"""Web search client using Google Custom Search API."""

import httpx

from config import config


class WebSearchClient:
    """Client for web search using Google Custom Search API."""

    def __init__(self):
        self.api_key = config.GOOGLE_SEARCH_API_KEY
        self.search_engine_id = config.GOOGLE_SEARCH_ENGINE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def search(self, query: str, num_results: int = 5) -> dict:
        """
        Search the web using Google Custom Search.

        Args:
            query: Search query
            num_results: Number of results to return (max 10)

        Returns:
            Dict with search results or error
        """
        if not self.api_key or not self.search_engine_id:
            return {
                "error": "Google Custom Search not configured. Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env",
                "results": [],
            }

        try:
            response = httpx.get(
                self.base_url,
                params={
                    "key": self.api_key,
                    "cx": self.search_engine_id,
                    "q": query,
                    "num": min(num_results, 10),  # Google limits to 10
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("items", []):
                results.append(
                    {
                        "title": item.get("title"),
                        "link": item.get("link"),
                        "snippet": item.get("snippet"),
                    }
                )

            return {
                "results": results,
                "total_results": data.get("searchInformation", {}).get("totalResults", "0"),
                "query": query,
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error: {e.response.status_code}"
            if e.response.status_code == 403:
                error_msg += " (Check API key or quota)"
            return {"error": error_msg, "results": []}
        except Exception as e:
            return {"error": f"Search failed: {str(e)}", "results": []}


# Singleton instance
web_search = WebSearchClient()
