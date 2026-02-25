"""OpenAI-backed provider for core onKaul investigations."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from openai import APIError, OpenAI

from agent.model_selector import model_selector
from agent.prompts import SYSTEM_PROMPT
from config import config
from tools.handlers import execute_tool
from tools.schemas import TOOL_SCHEMAS


class OpenAIAgentProvider:
    """Provider implementation using OpenAI Responses API."""

    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.store = config.OPENAI_STORE
        self.max_iterations = 100  # High limit for very thorough investigations
        self.tools = self._to_openai_tools(TOOL_SCHEMAS)

    def investigate(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> str:
        """Run investigation and return a complete response string."""
        if not self.client:
            return self._no_api_key_response(user_message)

        chunks: list[str] = []
        for chunk in self._run_openai_investigation_stream(user_message, context):
            chunks.append(chunk)
        return "".join(chunks) or "No response generated"

    def investigate_stream(
        self, user_message: str, context: str = "", thread_history: list | None = None
    ) -> Iterator[str]:
        """Run investigation and stream text chunks."""
        if not self.client:
            yield self._no_api_key_response(user_message)
            return

        yield from self._run_openai_investigation_stream(user_message, context)

    def _run_openai_investigation_stream(self, user_message: str, context: str) -> Iterator[str]:
        """Run Responses API loop with streaming enabled for each turn."""
        model_config = model_selector.select_model(user_message, context, provider="openai")
        print(f"\n🤖 Selected model: {model_config['name']}")
        print(f"📋 Reason: {model_config['reason']}")

        full_message = user_message
        if context:
            full_message = f"{context}\n\n---\n\n{user_message}"

        previous_response_id: str | None = None
        conversation_input: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": full_message}],
            }
        ]
        pending_input: list[dict[str, Any]] = conversation_input.copy()

        try:
            for iteration in range(self.max_iterations):
                print(f"\n{'─' * 80}")
                print(f"🔄 Agent Iteration {iteration + 1}/{self.max_iterations} (stream)")
                print(f"{'─' * 80}")

                stream_params = {
                    "model": model_config["id"],
                    "instructions": SYSTEM_PROMPT,
                    "tools": self.tools,
                    "input": pending_input,
                    "store": self.store,
                }
                if self.store and previous_response_id:
                    stream_params["previous_response_id"] = previous_response_id

                emitted_text = False
                with self.client.responses.stream(**stream_params) as stream:
                    for event in stream:
                        if getattr(event, "type", "") == "response.output_text.delta":
                            delta = getattr(event, "delta", "")
                            if delta:
                                emitted_text = True
                                yield delta
                    response = stream.get_final_response()

                if self.store:
                    previous_response_id = response.id
                tool_calls = self._extract_tool_calls(response)

                if not tool_calls:
                    # If nothing streamed (rare), fall back to final response text extraction.
                    if not emitted_text:
                        final_text = self._extract_text(response)
                        if final_text:
                            yield final_text
                    return

                print(f"\n🔧 Agent wants to use {len(tool_calls)} tool(s):")
                pending_input = []
                for call in tool_calls:
                    print(f"  • {call['name']}({self._format_inputs(call['args'])})")

                    print(f"\n  ▶ Executing {call['name']}...")
                    result = execute_tool(call["name"], call["args"])
                    result_preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"  ◀ Result: {result_preview}")

                    pending_input.append(
                        {
                            "type": "function_call_output",
                            "call_id": call["call_id"],
                            "output": result,
                        }
                    )

                if not self.store:
                    # With store disabled, keep full conversation state client-side.
                    conversation_input.extend(self._serialize_response_output_items(response))
                    conversation_input.extend(pending_input)
                    pending_input = conversation_input.copy()

            yield (
                f"\n\n_[Note: Investigation reached iteration limit after {self.max_iterations} "
                "tool uses. Consider breaking this into smaller questions.]_"
            )

        except APIError as e:
            yield f"❌ API Error: {str(e)}\n\nPlease check your OPENAI_API_KEY configuration."
        except Exception as e:
            yield f"❌ Unexpected error during investigation: {str(e)}"

    def _extract_tool_calls(self, response: Any) -> list[dict[str, Any]]:
        """Extract function calls from a Responses API response."""
        tool_calls: list[dict[str, Any]] = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) != "function_call":
                continue
            raw_args = getattr(item, "arguments", "{}") or "{}"
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}

            tool_calls.append(
                {
                    "call_id": getattr(item, "call_id", ""),
                    "name": getattr(item, "name", ""),
                    "args": args,
                }
            )
        return tool_calls

    def _extract_text(self, response: Any) -> str:
        """Extract final text from a Responses API response."""
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        text_parts: list[str] = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) != "message":
                continue
            for content_item in getattr(item, "content", []) or []:
                if getattr(content_item, "type", None) == "output_text":
                    text = getattr(content_item, "text", "")
                    if text:
                        text_parts.append(text)
        return "".join(text_parts)

    def _serialize_response_output_items(self, response: Any) -> list[dict[str, Any]]:
        """Convert output items into dict input format for stateless continuation."""
        serialized: list[dict[str, Any]] = []
        for item in getattr(response, "output", []) or []:
            model_dump = getattr(item, "model_dump", None)
            if callable(model_dump):
                serialized.append(model_dump())
        return serialized

    def _to_openai_tools(self, tool_schemas: list[dict]) -> list[dict]:
        """Convert Anthropic tool schemas to OpenAI Responses API function tools."""
        converted: list[dict] = []
        for tool in tool_schemas:
            converted.append(
                {
                    "type": "function",
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["input_schema"],
                    "strict": False,
                }
            )
        return converted

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
        return f"""⚠️ **OPENAI_API_KEY not configured**

I received your request:
> {user_message}

To enable OpenAI-powered investigations, please:
1. Create an API key in your OpenAI account
2. Add it to your `.env` file:
   ```
   OPENAI_API_KEY=your_key_here
   AGENT_PROVIDER=openai
   ```
3. Restart the server
"""
