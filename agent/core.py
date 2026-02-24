"""Agent core with Claude API integration."""

from collections.abc import Iterator

import anthropic

from agent.model_selector import model_selector
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

    def investigate(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> str:
        """
        Run investigation based on user message.

        Uses Claude (Opus or Sonnet) with all available tools.
        For research questions, Claude will use web_search tool (Brave Search).

        Args:
            user_message: User's question/request
            context: Additional context (thread history, Jira description, etc.)
            thread_history: Full thread messages (unused, kept for compatibility)

        Returns:
            Investigation results
        """
        if not self.client:
            return self._no_api_key_response(user_message)

        # All investigations use Claude with tools
        # Opus will be selected for research questions and use web_search tool
        return self._run_claude_investigation(user_message, context)

    def investigate_stream(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> Iterator[str]:
        """
        Stream investigation text chunks based on user message.

        This is intended for local CLI usage and keeps tool behavior aligned
        with the non-streaming investigate() loop.
        """
        if not self.client:
            yield self._no_api_key_response(user_message)
            return

        yield from self._run_claude_investigation_stream(user_message, context)

    def _run_claude_investigation(self, user_message: str, context: str) -> str:
        """Run standard Claude investigation (original investigate logic)."""

        # Select appropriate model based on task
        model_config = model_selector.select_model(user_message, context)
        print(f"\n🤖 Selected model: {model_config['name']}")
        print(f"📋 Reason: {model_config['reason']}")
        print(f"🎯 Max tokens: {model_config['max_tokens']}")

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

                # Build API call parameters
                api_params = {
                    "model": model_config["id"],
                    "max_tokens": model_config["max_tokens"],
                    "system": SYSTEM_PROMPT,
                    "tools": TOOL_SCHEMAS,
                    "messages": messages,
                }

                # Add thinking parameter if using extended thinking
                if "thinking" in model_config:
                    api_params["thinking"] = model_config["thinking"]

                response = self.client.messages.create(**api_params)

                # Check if we're done
                if response.stop_reason == "end_turn":
                    print("✅ Agent finished (stop_reason: end_turn)")
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

    def _run_claude_investigation_stream(self, user_message: str, context: str) -> Iterator[str]:
        """Run Claude investigation with streaming text output."""
        model_config = model_selector.select_model(user_message, context)
        print(f"\n🤖 Selected model: {model_config['name']}")
        print(f"📋 Reason: {model_config['reason']}")
        print(f"🎯 Max tokens: {model_config['max_tokens']}")

        full_message = user_message
        if context:
            full_message = f"{context}\n\n---\n\n{user_message}"

        messages = [{"role": "user", "content": full_message}]

        try:
            for iteration in range(self.max_iterations):
                print(f"\n{'─' * 80}")
                print(f"🔄 Agent Iteration {iteration + 1}/{self.max_iterations} (stream)")
                print(f"{'─' * 80}")

                api_params = {
                    "model": model_config["id"],
                    "max_tokens": model_config["max_tokens"],
                    "system": SYSTEM_PROMPT,
                    "tools": TOOL_SCHEMAS,
                    "messages": messages,
                }
                if "thinking" in model_config:
                    api_params["thinking"] = model_config["thinking"]

                with self.client.messages.stream(**api_params) as stream:
                    for text in stream.text_stream:
                        yield text
                    response = stream.get_final_message()

                if response.stop_reason == "end_turn":
                    print("✅ Agent finished (stop_reason: end_turn)")
                    return

                if response.stop_reason == "tool_use":
                    tool_uses = [block for block in response.content if block.type == "tool_use"]
                    print(f"\n🔧 Agent wants to use {len(tool_uses)} tool(s):")
                    for block in tool_uses:
                        print(f"  • {block.name}({self._format_inputs(block.input)})")

                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            print(f"\n  ▶ Executing {block.name}...")
                            result = execute_tool(block.name, block.input)
                            result_preview = result[:200] + "..." if len(result) > 200 else result
                            print(f"  ◀ Result: {result_preview}")
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result,
                                }
                            )

                    messages.append({"role": "user", "content": tool_results})
                    continue

                print(f"⚠️  Unexpected stop_reason: {response.stop_reason}")
                text = self._extract_text(response)
                if text:
                    yield text
                return

            yield (
                f"\n\n_[Note: Investigation reached iteration limit after {self.max_iterations} "
                "tool uses. Consider breaking this into smaller questions.]_"
            )

        except anthropic.APIError as e:
            yield f"❌ API Error: {str(e)}\n\nPlease check your ANTHROPIC_API_KEY configuration."
        except Exception as e:
            yield f"❌ Unexpected error during investigation: {str(e)}"

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
