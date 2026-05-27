"""Anthropic provider implementation."""

import json
from typing import AsyncIterator
import anthropic
from rain_brain.providers.base import Provider, ChatRequest, ChatChunk


class AnthropicProvider:
    """Provider for Anthropic API."""

    name = "anthropic"

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def list_models(self) -> list[str]:
        from rain_brain.providers.model_registry import get_provider_models
        return get_provider_models("anthropic")

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream chat completion from Anthropic with tool call support."""
        try:
            system_msg = ""
            messages: list[dict] = []

            for msg in req.messages:
                role = msg.get("role", "")
                if role == "system":
                    system_msg += str(msg.get("content", "")) + "\n"
                elif role == "tool":
                    # Anthropic expects tool results as user messages with specific content blocks
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_use_id", "unknown"),
                            "content": str(msg.get("content", "")),
                        }],
                    })
                elif role == "assistant" and msg.get("tool_calls"):
                    # Assistant message with tool calls → convert to Anthropic content blocks
                    tool_blocks = []
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except (json.JSONDecodeError, TypeError):
                                args = {}
                        tool_blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", f"call_{fn.get('name', 'tool')}"),
                            "name": fn.get("name", ""),
                            "input": args,
                        })
                    messages.append({"role": "assistant", "content": tool_blocks})
                else:
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        # Vision: convert OpenAI-format content blocks to Anthropic format
                        anthropic_blocks = []
                        for block in content:
                            if block.get("type") == "text":
                                anthropic_blocks.append({"type": "text", "text": block["text"]})
                            elif block.get("type") == "image_url":
                                url = block["image_url"]["url"]
                                if url.startswith("data:"):
                                    header, b64data = url.split(",", 1)
                                    media_type = header.split(";")[0].split(":")[1]
                                    anthropic_blocks.append({
                                        "type": "image",
                                        "source": {"type": "base64", "media_type": media_type, "data": b64data},
                                    })
                                else:
                                    anthropic_blocks.append({
                                        "type": "image",
                                        "source": {"type": "url", "url": url},
                                    })
                        if anthropic_blocks and role in ("user", "assistant"):
                            messages.append({"role": role, "content": anthropic_blocks})
                    elif content or role in ("user", "assistant"):
                        messages.append({"role": role, "content": content})

            # Convert tools to Anthropic format if present
            anthropic_tools = []
            if req.tools:
                for t in req.tools:
                    fn = t.get("function", {})
                    anthropic_tools.append({
                        "name": fn.get("name", ""),
                        "description": fn.get("description", ""),
                        "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                    })

            stream_kwargs: dict = dict(
                model=req.model,
                max_tokens=req.max_tokens or 4096,
                messages=messages,
                system=system_msg.strip() or anthropic.NOT_GIVEN,
                temperature=req.temperature,
            )
            if anthropic_tools:
                stream_kwargs["tools"] = anthropic_tools

            async with self._client.messages.stream(**stream_kwargs) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield ChatChunk(type="token", data=event.delta.text)
                        elif event.delta.type == "input_json_delta":
                            # Tool input streaming — handled at block_stop
                            pass
                    elif event.type == "content_block_stop":
                        block = event.model_dump().get("content_block")
                        if block and block.get("type") == "tool_use":
                            try:
                                args = block.get("input", {})
                                if isinstance(args, str):
                                    args = json.loads(args)
                            except (json.JSONDecodeError, TypeError):
                                args = {}
                            yield ChatChunk(
                                type="tool_call",
                                data={"name": block.get("name", ""), "args": args},
                            )

                final_msg = await stream.get_final_message()
                yield ChatChunk(
                    type="done",
                    data={
                        "model": final_msg.model,
                        "tokens_in": final_msg.usage.input_tokens,
                        "tokens_out": final_msg.usage.output_tokens,
                    },
                )

        except anthropic.AuthenticationError:
            yield ChatChunk(
                type="error",
                data={
                    "code": "invalid_api_key",
                    "message": "Anthropic API key is invalid or expired. Please update it in Settings → API Credentials.",
                },
            )
        except Exception as e:
            yield ChatChunk(
                type="error",
                data={"code": "anthropic_error", "message": str(e)},
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[] for _ in texts]

    async def health(self) -> bool:
        return True

    async def close(self) -> None:
        pass
