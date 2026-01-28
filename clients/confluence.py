"""Confluence client for reading wiki pages."""

import re

import httpx

from config import config


class ConfluenceClient:
    """Client for Confluence wiki using REST API."""

    def __init__(self):
        # Scoped API tokens must use api.atlassian.com with cloud ID
        self.cloud_id = config.CONFLUENCE_CLOUD_ID
        self.api_base_url = config.CONFLUENCE_API_BASE_URL
        self.base_url = f"{self.api_base_url}/{self.cloud_id}/wiki"
        self.wiki_base_url = config.CONFLUENCE_WIKI_BASE_URL
        self.email = config.CONFLUENCE_EMAIL
        self.token = config.CONFLUENCE_API_TOKEN

    def read_page(self, page_id: str) -> dict:
        """
        Read a Confluence page and convert to markdown.

        Args:
            page_id: Confluence page ID (e.g., '2030403650')

        Returns:
            Dict with page title and content
        """
        if not self.email or not self.token:
            return {
                "error": "Confluence credentials not configured. Set CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN in .env"
            }

        try:
            # Fetch page with body in view format (HTML)
            response = httpx.get(
                f"{self.base_url}/rest/api/content/{page_id}",
                auth=(self.email, self.token),
                params={"expand": "body.view,version"},
                timeout=30.0,
            )

            if response.status_code == 404:
                return {"error": f"Page {page_id} not found"}

            if response.status_code != 200:
                return {
                    "error": f"Confluence API error: {response.status_code} {response.text[:200]}"
                }

            data = response.json()

            title = data.get("title", "")
            html_content = data.get("body", {}).get("view", {}).get("value", "")

            # Convert HTML to simpler text (basic conversion)
            text_content = self._html_to_text(html_content)

            return {
                "title": title,
                "content": text_content,
                "page_id": page_id,
                "url": f"{self.wiki_base_url}/spaces/ENG/pages/{page_id}",
                "version": data.get("version", {}).get("number"),
            }

        except httpx.TimeoutException:
            return {"error": "Confluence request timed out"}
        except httpx.HTTPError as e:
            return {"error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to read Confluence page: {str(e)}"}

    def _html_to_text(self, html: str) -> str:
        """
        Convert Confluence HTML to plain text (basic conversion).

        Args:
            html: HTML content

        Returns:
            Plain text with basic formatting
        """
        if not html:
            return ""

        # Remove script/style tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Convert headers
        text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.IGNORECASE)

        # Convert lists
        text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.IGNORECASE)

        # Convert paragraphs
        text = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", text, flags=re.IGNORECASE)

        # Convert line breaks
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

        # Convert code blocks
        text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.IGNORECASE)

        # Remove remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')

        # Clean up excessive whitespace
        text = re.sub(r"\n\n\n+", "\n\n", text)
        text = text.strip()

        return text


# Singleton instance
confluence = ConfluenceClient()
