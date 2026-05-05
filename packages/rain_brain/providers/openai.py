"""OpenAI provider implementation."""

import json
from typing import AsyncIterator
import openai
from rain_brain.providers.base import Provider, ChatRequest, ChatChunk


class OpenAIProvider:
    """Provider for OpenAI API."""

    name = "openai"

    def __init__(self, api_key: str):
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def list_models(self) -> list[str]:
        """Fetch available models from OpenAI API (always valid for user's key)."""
        try:
            models = await self._client.models.list()
            # Only include models that support chat completions
            chat_prefixes = ("gpt-", "o1", "o3", "o4")
            return sorted([
                m.id for m in models.data
                if m.id.startswith(chat_prefixes) and not m.id.startswith("gpt-3.5-turbo-instruct")
            ])
        except Exception:
            # Fallback to conservative list if API fails
            return ["gpt-4o", "gpt-4o-mini", "o3-mini", "o4-mini"]

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream chat completion from OpenAI with tool call support."""
        try:
            # o1/o3/o4 reasoning models use different params from standard GPT models
            is_reasoning = req.model.startswith(("o1", "o3", "o4"))

            kwargs: dict = dict(
                model=req.model,
                messages=req.messages,
                stream=True,
                stream_options={"include_usage": True},
            )

            if is_reasoning:
                # Reasoning models: max_completion_tokens, no temperature, no tool_choice auto
                kwargs["max_completion_tokens"] = req.max_tokens
            else:
                kwargs["max_tokens"] = req.max_tokens
                kwargs["temperature"] = req.temperature

            if req.tools:
                kwargs["tools"] = req.tools
                if not is_reasoning:
                    kwargs["tool_choice"] = "auto"

            stream = await self._client.chat.completions.create(**kwargs)

            # Buffer tool call fragments — OpenAI streams them in pieces keyed by index
            tool_buf: dict[int, dict] = {}

            async for chunk in stream:
                if not chunk.choices:
                    # Usage-only final chunk
                    if chunk.usage:
                        yield ChatChunk(
                            type="done",
                            data={
                                "model": chunk.model,
                                "tokens_in": chunk.usage.prompt_tokens,
                                "tokens_out": chunk.usage.completion_tokens,
                            },
                        )
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # Regular text token
                if delta.content:
                    yield ChatChunk(type="token", data=delta.content)

                # Tool call fragments — accumulate until finish_reason == "tool_calls"
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_buf:
                            tool_buf[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            tool_buf[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_buf[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_buf[idx]["arguments"] += tc.function.arguments

                # Emit complete tool calls when the turn ends
                if choice.finish_reason == "tool_calls":
                    for tc_data in tool_buf.values():
                        try:
                            args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                        except json.JSONDecodeError:
                            args = {"_raw": tc_data["arguments"]}
                        yield ChatChunk(
                            type="tool_call",
                            data={"name": tc_data["name"], "args": args},
                        )
                    tool_buf.clear()

        except openai.AuthenticationError:
            yield ChatChunk(
                type="error",
                data={
                    "code": "invalid_api_key",
                    "message": "OpenAI API key is invalid or expired. Please update it in Settings → API Credentials.",
                },
            )
        except openai.RateLimitError:
            yield ChatChunk(
                type="error",
                data={"code": "rate_limit", "message": "OpenAI rate limit reached. Please try again shortly."},
            )
        except Exception as e:
            yield ChatChunk(
                type="error",
                data={"code": "openai_error", "message": str(e)},
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via OpenAI."""
        try:
            response = await self._client.embeddings.create(
                input=texts,
                model="text-embedding-3-small",
            )
            return [data.embedding for data in response.data]
        except Exception:
            return [[] for _ in texts]

    async def health(self) -> bool:
        return True

    async def close(self) -> None:
        pass
