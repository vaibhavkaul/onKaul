"""Agent core with Claude API integration and deep research support."""

import anthropic

from agent.model_selector import model_selector
from agent.prompts import SYSTEM_PROMPT
from agent.research_detector import research_detector
from clients.gemini import gemini
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

        Handles:
        - Regular investigations (Claude)
        - Deep research requests (Gemini)
        - Confirmation flows for research

        Args:
            user_message: User's question/request
            context: Additional context (thread history, Jira description, etc.)
            thread_history: Full thread messages (for state inference)

        Returns:
            Investigation results or research confirmation request
        """
        if not self.client:
            return self._no_api_key_response(user_message)

        # Check if this is a deep research question
        is_research = research_detector.is_research_question(user_message, context)

        if is_research:
            return self._handle_research_flow(user_message, context, thread_history)

        # Regular investigation with Claude
        return self._run_claude_investigation(user_message, context)

    def _handle_research_flow(
        self, user_message: str, context: str, thread_history: list | None
    ) -> str:
        """
        Handle deep research flow with confirmation.

        Args:
            user_message: User's message
            context: Additional context
            thread_history: Thread messages for state inference

        Returns:
            Confirmation request, research results, or error
        """
        # Extract bot's own messages from thread
        bot_messages = []
        if thread_history:
            for msg in thread_history:
                # Check if message is from bot (has bot_id or is from our user)
                if msg.get("bot_id") or msg.get("username") == "onKaul":
                    text = msg.get("text", "")
                    bot_messages.append(text)

        # Check state from conversation history
        already_asked = research_detector.already_requested_confirmation(bot_messages)
        already_done = research_detector.already_completed_research(bot_messages)

        # If already completed research, provide summary
        if already_done:
            return """I've already completed deep research on this topic earlier in this thread.

Please review my previous research report above, or ask a specific follow-up question if you need additional details on a particular aspect."""

        # If we already asked for confirmation
        if already_asked:
            # Check if user confirmed
            confirmation = research_detector.parse_confirmation(user_message)

            if confirmation == "yes":
                # User confirmed - run deep research
                print("✅ User confirmed deep research - proceeding...")
                result = gemini.deep_research(user_message)

                if "error" in result:
                    return f"❌ Deep research failed: {result['error']}\n\n{result.get('message', '')}"

                # Format research report
                report = result.get("report", "No report generated")
                duration = result.get("duration_seconds", 0)

                return f"""✅ **Deep Research Complete** ({duration // 60} minutes)

{report}

---
_Research conducted using Gemini Deep Research_"""

            elif confirmation == "no":
                return "👍 Understood - deep research canceled. Let me know if you need anything else!"

            else:
                # User didn't clearly confirm - remind them
                return """I'm waiting for your confirmation to start deep research.

Please reply with:
- '@onkaul yes' to proceed with deep research
- '@onkaul no' to cancel"""

        # First time - request confirmation
        return f"""🔬 This question requires **deep web research** (5-10 minutes).

I'll need to:
- Search multiple sources across the web
- Read documentation and articles
- Compare options and synthesize findings
- Compile a comprehensive report with citations

**Your question:** {user_message}

Should I proceed with deep research? Reply with:
- **'@onkaul yes'** or **'@onkaul go for it'** to start
- **'@onkaul no'** or **'skip'** to cancel"""

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
