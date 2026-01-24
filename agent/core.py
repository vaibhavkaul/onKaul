"""Agent core with Claude API integration."""

import anthropic

from agent.prompts import SYSTEM_PROMPT
from config import config
from tools.handlers import execute_tool
from tools.schemas import TOOL_SCHEMAS


class Agent:
    """Agent that uses Claude with tools."""

    def __init__(self):
        self.api_key = config.ANTHROPIC_API_KEY
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
        self.max_iterations = 100  # High limit for very thorough investigations

    def investigate(self, user_message: str, context: str = "") -> str:
        """
        Run investigation based on user message.

        Args:
            user_message: User's question/request
            context: Additional context (thread history, Jira description, etc.)

        Returns:
            Investigation results as formatted string
        """
        if not self.client:
            return self._no_api_key_response(user_message)

        # Build initial user message
        full_message = user_message
        if context:
            full_message = f"{context}\n\n---\n\n{user_message}"

        messages = [{"role": "user", "content": full_message}]

        try:
            for iteration in range(self.max_iterations):
                print(f"\n{'─' * 80}")
                print(f"🔄 Agent Iteration {iteration + 1}/{self.max_iterations}")
                print(f"{'─' * 80}")

                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8192,  # Maximum for Sonnet 4 - allows thorough investigations
                    system=SYSTEM_PROMPT,
                    tools=TOOL_SCHEMAS,
                    messages=messages,
                )

                # Check if we're done
                if response.stop_reason == "end_turn":
                    print(f"✅ Agent finished (stop_reason: end_turn)")
                    return self._extract_text(response)

                # Handle tool use
                if response.stop_reason == "tool_use":
                    # Log what tools the agent wants to use
                    tool_uses = [block for block in response.content if block.type == "tool_use"]
                    print(f"\n🔧 Agent wants to use {len(tool_uses)} tool(s):")
                    for block in tool_uses:
                        print(f"  • {block.name}({self._format_inputs(block.input)})")

                    # Add assistant message with tool uses
                    messages.append({"role": "assistant", "content": response.content})

                    # Execute tools and collect results
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            print(f"\n  ▶ Executing {block.name}...")
                            result = execute_tool(block.name, block.input)
                            # Show result preview
                            result_preview = result[:200] + "..." if len(result) > 200 else result
                            print(f"  ◀ Result: {result_preview}")
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result,
                                }
                            )

                    # Add tool results as user message
                    messages.append({"role": "user", "content": tool_results})

                else:
                    # Unexpected stop reason
                    print(f"⚠️  Unexpected stop_reason: {response.stop_reason}")
                    return self._extract_text(response)

            # Hit max iterations
            return (
                self._extract_text(response)
                + f"\n\n_[Note: Investigation reached iteration limit after {iteration + 1} tool uses. Consider breaking this into smaller questions.]_"
            )

        except anthropic.APIError as e:
            return f"❌ API Error: {str(e)}\n\nPlease check your ANTHROPIC_API_KEY configuration."
        except Exception as e:
            return f"❌ Unexpected error during investigation: {str(e)}"

    def _extract_text(self, response) -> str:
        """Extract text content from response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts) or "No response generated"

    def _format_inputs(self, inputs: dict) -> str:
        """Format tool inputs for logging."""
        parts = []
        for key, value in inputs.items():
            if isinstance(value, str) and len(value) > 50:
                parts.append(f"{key}='{value[:50]}...'")
            else:
                parts.append(f"{key}={repr(value)}")
        return ", ".join(parts)

    def _no_api_key_response(self, user_message: str) -> str:
        """Return helpful message when API key not configured."""
        return f"""⚠️ **ANTHROPIC_API_KEY not configured**

I received your request:
> {user_message}

To enable real investigations, please:
1. Get an API key from https://console.anthropic.com/
2. Add it to your `.env` file:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```
3. Restart the server

Once configured, I'll be able to:
- 🔍 Investigate Sentry errors
- 📁 Search code in GitHub repos
- 📊 Query Datadog logs
- 🎫 Search Jira issues
- 💡 Provide actionable fixes
"""


# Singleton instance
agent = Agent()
