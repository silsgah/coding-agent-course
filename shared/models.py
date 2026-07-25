"""
Model provider abstraction for the Coding Agent Course.

Provides a unified interface to call different LLM providers.
Supports Gemini (default, free), OpenRouter, OpenAI, and Anthropic.

Design note: This abstraction is deliberately thin. The goal is to show
students that the model is the *simplest* part — the harness is everything else.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from . import config


# ---------------------------------------------------------------------------
# Message types — kept simple so students can focus on the harness
# ---------------------------------------------------------------------------
@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None


@dataclass
class ToolCall:
    """A parsed tool call from the model."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelResponse:
    """What we get back from any provider."""
    content: str
    tool_calls: list[ToolCall]
    raw: dict[str, Any]  # Full provider response for debugging
    usage: dict[str, int]  # {"prompt_tokens": ..., "completion_tokens": ...}


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------
class GeminiProvider:
    """Google Gemini via the google-genai SDK."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or config.DEFAULT_MODEL
        self.api_key = api_key or config.get_api_key("gemini")
        from google import genai
        self.client = genai.Client(api_key=self.api_key)

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> ModelResponse:
        """Send messages and return a structured response."""
        from google.genai import types

        # Convert tool schemas to google.genai types
        tool_declarations = None
        if tools:
            func_decls = []
            for t in tools:
                if isinstance(t, dict) and t.get("type") == "function":
                    fn = t["function"]
                    func_decls.append(
                        types.FunctionDeclaration(
                            name=fn["name"],
                            description=fn.get("description", ""),
                            parameters=fn.get("parameters"),
                        )
                    )
            if func_decls:
                tool_declarations = [types.Tool(function_declarations=func_decls)]

        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg.role == "system":
                continue  # Handled separately in system_instruction

            if msg.role == "user":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part(text=msg.content)],
                    )
                )
            elif msg.role == "assistant":
                parts = []
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        parts.append(
                            types.Part.from_function_call(
                                name=tc["name"],
                                args=tc["arguments"],
                            )
                        )
                if msg.content:
                    parts.insert(0, types.Part(text=msg.content))
                if not parts:
                    parts = [types.Part(text="")]
                contents.append(types.Content(role="model", parts=parts))

            elif msg.role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=msg.tool_call_id or "tool",
                                response={"result": msg.content},
                            )
                        ],
                    )
                )

        system_msgs = [m.content for m in messages if m.role == "system"]
        system_instruction = "\n".join(system_msgs) if system_msgs else None

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tool_declarations,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=gen_config,
        )

        # Parse tool calls if present
        tool_calls = []
        text_content = ""

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tool_calls.append(
                        ToolCall(
                            id=fc.name,
                            name=fc.name,
                            arguments=dict(fc.args) if fc.args else {},
                        )
                    )
                elif hasattr(part, "text") and part.text:
                    text_content += part.text

        if not text_content and not tool_calls and response.text:
            text_content = response.text

        return ModelResponse(
            content=text_content,
            tool_calls=tool_calls,
            raw={"response": str(response)},
            usage={
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
                "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
            },
        )

    def __repr__(self) -> str:
        return f"GeminiProvider(model={self.model!r})"


class OpenAICompatibleProvider:
    """Works with OpenAI, OpenRouter, or any OpenAI-compatible API."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        provider_name: str = "openai",
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.provider_name = provider_name

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
    ) -> ModelResponse:
        """Send messages via the OpenAI-compatible chat completions API."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
            ],
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        msg = choice["message"]

        # Parse tool calls
        tool_calls = []
        for tc in msg.get("tool_calls", []):
            tool_calls.append(
                ToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]),
                )
            )

        return ModelResponse(
            content=msg.get("content", "") or "",
            tool_calls=tool_calls,
            raw=data,
            usage=data.get("usage", {}),
        )

    def __repr__(self) -> str:
        return f"OpenAICompatibleProvider(model={self.model!r}, provider={self.provider_name!r})"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_provider(
    provider: str | None = None,
    model: str | None = None,
) -> GeminiProvider | OpenAICompatibleProvider:
    """
    Create a model provider.

    Args:
        provider: "gemini", "openai", "openrouter", or "anthropic".
                  Defaults to auto-detecting from DEFAULT_MODEL.
        model: Model name. Defaults to DEFAULT_MODEL from .env.

    Returns:
        A provider instance ready to call .chat()
    """
    model = model or config.DEFAULT_MODEL

    # Auto-detect provider from model name
    if provider is None:
        if "gemini" in model:
            provider = "gemini"
        elif "gpt" in model or "o1" in model or "o3" in model:
            provider = "openai"
        elif "claude" in model:
            provider = "anthropic"
        else:
            provider = "openrouter"  # Fallback: try OpenRouter

    if provider == "gemini":
        return GeminiProvider(model=model)
    elif provider == "openai":
        return OpenAICompatibleProvider(
            model=model,
            api_key=config.get_api_key("openai"),
            base_url="https://api.openai.com/v1",
            provider_name="openai",
        )
    elif provider == "openrouter":
        return OpenAICompatibleProvider(
            model=model,
            api_key=config.get_api_key("openrouter"),
            base_url="https://openrouter.ai/api/v1",
            provider_name="openrouter",
        )
    elif provider == "anthropic":
        return OpenAICompatibleProvider(
            model=model,
            api_key=config.get_api_key("anthropic"),
            base_url="https://api.anthropic.com/v1",
            provider_name="anthropic",
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
