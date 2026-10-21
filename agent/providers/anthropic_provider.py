"""Anthropic-backed provider for core onKaul investigations."""

from __future__ import annotations

import time
from collections.abc import Iterator

import anthropic

from agent.history import build_messages
from agent.model_selector import model_selector
from agent.prompts import SYSTEM_PROMPT, current_date_context
from config import config
from tools.handlers import execute_tool
from tools.schemas import TOOL_SCHEMAS
from utils.events import emit

# Models that support web_search_20260209 (dynamic filtering); others get the basic variant.
_DYNAMIC_WEB_SEARCH_MODEL_PREFIXES = (
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
)


class AnthropicAgentProvider:
    """Provider implementation using Anthropic's Messages API."""

    def __init__(self):
        self.api_key = config.ANTHROPIC_API_KEY
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
        self.max_iterations = 100  # High limit for very thorough investigations

    def investigate(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> str:
        """
        Run investigation based on user message.

        Uses Claude with all available tools.
        """
        if not self.client:
            return self._no_api_key_response(user_message)

        return self._run_claude_investigation(user_message, context, thread_history)

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

        yield from self._run_claude_investigation_stream(user_message, context, thread_history)

    def _run_claude_investigation(
        self, user_message: str, context: str, thread_history: list | None = None
    ) -> str:
        """Run standard Claude investigation (original investigate logic)."""

        model_config = model_selector.select_model(user_message, context, provider="anthropic")
        print(f"\n🤖 Selected model: {model_config['name']}")
        print(f"📋 Reason: {model_config['reason']}")
        print(f"🎯 Max tokens: {model_config['max_tokens']}")

        full_message = user_message
        if context:
            full_message = f"{context}\n\n---\n\n{user_message}"

        messages = build_messages(thread_history, full_message)

        try:
            for iteration in range(self.max_iterations):
                print(f"\n{'─' * 80}")
                print(f"🔄 Agent Iteration {iteration + 1}/{self.max_iterations}")
                print(f"{'─' * 80}")

                api_params = self._request_params(model_config, messages)

                start = time.monotonic()
                # Streamed even here: non-streaming requests hit the SDK's timeout
                # guard once max_tokens is large, and current models think first.
                with self.client.messages.stream(**api_params) as stream:
                    response = stream.get_final_message()
                self._emit_usage(model_config["id"], response, start, streamed=False)

                if response.stop_reason == "end_turn":
                    print("✅ Agent finished (stop_reason: end_turn)")
                    return self._extract_text(response)

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

                elif response.stop_reason == "pause_turn":
                    # A server tool (web search) paused the turn; resend to resume.
                    messages.append({"role": "assistant", "content": response.content})

                elif response.stop_reason == "refusal":
                    return self._refusal_message(response)

                else:
                    print(f"⚠️  Unexpected stop_reason: {response.stop_reason}")
                    return self._extract_text(response)

            return (
                self._extract_text(response)
                + f"\n\n_[Note: Investigation reached iteration limit after {iteration + 1} tool uses. Consider breaking this into smaller questions.]_"
            )

        except anthropic.APIError as e:
            self._emit_error(e)
            return self._api_error_message(e)
        except Exception as e:
            return f"❌ Unexpected error during investigation: {str(e)}"

    def _run_claude_investigation_stream(
        self, user_message: str, context: str, thread_history: list | None = None
    ) -> Iterator[str]:
        """Run Claude investigation with streaming text output."""
        model_config = model_selector.select_model(user_message, context, provider="anthropic")
        print(f"\n🤖 Selected model: {model_config['name']}")
        print(f"📋 Reason: {model_config['reason']}")
        print(f"🎯 Max tokens: {model_config['max_tokens']}")

        full_message = user_message
        if context:
            full_message = f"{context}\n\n---\n\n{user_message}"

        messages = build_messages(thread_history, full_message)

        try:
            for iteration in range(self.max_iterations):
                print(f"\n{'─' * 80}")
                print(f"🔄 Agent Iteration {iteration + 1}/{self.max_iterations} (stream)")
                print(f"{'─' * 80}")

                api_params = self._request_params(model_config, messages)

                start = time.monotonic()
                with self.client.messages.stream(**api_params) as stream:
                    for text in stream.text_stream:
                        yield text
                    response = stream.get_final_message()
                self._emit_usage(model_config["id"], response, start, streamed=True)

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

                if response.stop_reason == "pause_turn":
                    # A server tool (web search) paused the turn; resend to resume.
                    messages.append({"role": "assistant", "content": response.content})
                    continue

                if response.stop_reason == "refusal":
                    yield ("\n\n" if response.content else "") + self._refusal_message(response)
                    return

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
            self._emit_error(e)
            yield self._api_error_message(e)
        except Exception as e:
            yield f"❌ Unexpected error during investigation: {str(e)}"

    def _request_params(self, model_config: dict, messages: list) -> dict:
        params = {
            "model": model_config["id"],
            "max_tokens": model_config["max_tokens"],
            # Stable prompt first, the per-day date block after it.
            "system": [
                {"type": "text", "text": SYSTEM_PROMPT},
                {"type": "text", "text": current_date_context()},
            ],
            "tools": [*TOOL_SCHEMAS, *self._server_tools(model_config["id"])],
            "messages": messages,
        }
        if "thinking" in model_config:
            params["thinking"] = model_config["thinking"]
        if "effort" in model_config:
            params["output_config"] = {"effort": model_config["effort"]}
        return params

    @staticmethod
    def _server_tools(model_id: str) -> list[dict]:
        """Anthropic-hosted tools: web search (dynamic-filtering variant where supported)."""
        if not config.ENABLE_WEB_SEARCH:
            return []
        dynamic = model_id.startswith(_DYNAMIC_WEB_SEARCH_MODEL_PREFIXES)
        return [
            {
                "type": "web_search_20260209" if dynamic else "web_search_20250305",
                "name": "web_search",
                "max_uses": config.WEB_SEARCH_MAX_USES,
            }
        ]

    @staticmethod
    def _refusal_message(response) -> str:
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None)
        suffix = f" (category: {category})" if category else ""
        return f"⚠️ The model declined to answer this request{suffix}."

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

    @staticmethod
    def _emit_usage(model_id: str, response, start: float, *, streamed: bool) -> None:
        """Record one Messages API call with its token usage."""
        usage = getattr(response, "usage", None)
        emit(
            "llm.call",
            provider="anthropic",
            model=model_id,
            streamed=streamed,
            stop_reason=getattr(response, "stop_reason", None),
            duration_ms=round((time.monotonic() - start) * 1000),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", None),
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", None),
        )

    @staticmethod
    def _emit_error(error: anthropic.APIError) -> None:
        emit(
            "llm.error",
            provider="anthropic",
            error_type=type(error).__name__,
            status_code=getattr(error, "status_code", None),
            error=str(error)[:500],
        )

    @staticmethod
    def _api_error_message(error: anthropic.APIError) -> str:
        """Describe an API failure without blaming the key for rate limits or outages."""
        if isinstance(error, anthropic.AuthenticationError):
            return (
                "❌ Anthropic rejected the API key.\n\n"
                "Please check your ANTHROPIC_API_KEY configuration."
            )
        if isinstance(error, anthropic.APIStatusError):
            return f"❌ Anthropic API error (HTTP {error.status_code}): {error.message}"
        return f"❌ Anthropic API error: {error}"

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
