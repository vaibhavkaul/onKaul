"""Gemini client for deep research tasks."""

import time

from google import genai
from google.genai.types import GenerateContentConfig, Tool

from config import config


class GeminiClient:
    """Client for Gemini Deep Research."""

    def __init__(self):
        self.api_key = config.GOOGLE_API_KEY
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def deep_research(self, question: str) -> dict:
        """
        Run deep research using Gemini Deep Research agent.

        This is a long-running operation (5-10 minutes) that:
        - Searches multiple sources
        - Reads documentation
        - Synthesizes comprehensive report
        - Includes citations

        Args:
            question: Research question

        Returns:
            Dict with report and citations
        """
        if not self.client:
            return {
                "error": "GOOGLE_API_KEY not configured",
                "message": "Deep research requires Google Gemini API key",
            }

        try:
            print(f"🔬 Starting Gemini Deep Research...")
            print(f"📝 Question: {question[:100]}...")

            # Create deep research task (background=True for async)
            response = self.client.interactions.create(
                agent="deep-research-pro-preview-12-2025",
                prompt=question,
                config=GenerateContentConfig(temperature=0.2),  # Lower temp for factual research
                background=True,
            )

            # Poll for completion
            print(f"⏳ Research task created: {response.id}")
            print(f"⏳ Polling for completion (this may take 5-10 minutes)...")

            max_wait = 600  # 10 minutes max
            poll_interval = 10  # Check every 10 seconds
            elapsed = 0

            while elapsed < max_wait:
                # Get current status
                status = self.client.interactions.get(response.id)

                print(f"⏳ Status: {status.state} ({elapsed}s elapsed)")

                if status.state == "completed":
                    print(f"✅ Research complete!")

                    # Extract report
                    report = ""
                    if status.response and status.response.text:
                        report = status.response.text

                    # Extract grounding metadata (citations)
                    citations = []
                    if hasattr(status.response, "grounding_metadata"):
                        metadata = status.response.grounding_metadata
                        if hasattr(metadata, "search_entry_point"):
                            # Citations from web search
                            pass  # Parse citations if available

                    return {
                        "report": report,
                        "citations": citations,
                        "duration_seconds": elapsed,
                        "question": question,
                    }

                elif status.state == "failed":
                    error_msg = status.error if hasattr(status, "error") else "Unknown error"
                    return {"error": f"Research failed: {error_msg}"}

                # Still running - wait and poll again
                time.sleep(poll_interval)
                elapsed += poll_interval

            # Timeout
            return {
                "error": "Research timeout",
                "message": f"Research took longer than {max_wait}s",
            }

        except Exception as e:
            return {"error": f"Failed to run deep research: {str(e)}"}


# Singleton instance
gemini = GeminiClient()
