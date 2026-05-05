"""Ollama provider implementation."""

import json
import re
from typing import AsyncIterator
import httpx
from rain_brain.providers.base import Provider, ChatRequest, ChatChunk
from rain_brain.config import brain_settings


def _parse_xml_tool_calls(xml: str) -> list[dict]:
    """Parse Claude-style <function_calls> XML into tool call dicts."""
    results = []
    for m in re.finditer(r'<invoke\s+name="([^"]+)">(.*?)</invoke>', xml, re.DOTALL):
        tool_name = m.group(1)
        args: dict = {}
        for p in re.finditer(r'<parameter\s+name="([^"]+)">(.*?)</parameter>', m.group(2), re.DOTALL):
            args[p.group(1)] = p.group(2).strip()
        results.append({"name": tool_name, "args": args})
    return results


class OllamaProvider:
    """Provider for local Ollama server."""

    name = "ollama"

    def __init__(self, base_url: str | None = None, timeout: float = 300.0):
        url = base_url or brain_settings.ollama_base_url
        if not url.endswith("/"):
            url += "/"
        self._base_url = url
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )

    async def list_models(self) -> list[str]:
        """List available models from Ollama."""
        try:
            # Use relative path without leading slash to avoid base_url issues
            response = await self._client.get("api/tags")
            response.raise_for_status()
            data = response.json()
            models = []
            for model in data.get("models", []):
                name = model.get("name")
                if name:
                    models.append(name)
            return models
        except Exception as e:
            # Fallback to empty and log error
            return []

    @staticmethod
    def _prepare_messages(messages: list[dict]) -> list[dict]:
        """Convert OpenAI-format messages to Ollama-compatible format.

        Handles:
        - Vision content blocks (OpenAI format → Ollama images array)
        - Tool call messages (arguments string → dict, strips extra fields)
        - Tool result messages (strips OpenAI/Anthropic/Gemini-specific fields)
        """
        out = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # ── Tool result message ──
            # Ollama only needs role + content (+ optional name). Strip
            # OpenAI's tool_call_id, Anthropic's tool_use_id, etc.
            if role == "tool":
                cleaned: dict = {"role": "tool", "content": str(content) if content else ""}
                if msg.get("name"):
                    cleaned["name"] = msg["name"]
                out.append(cleaned)
                continue

            # ── Assistant message with tool_calls ──
            # Ollama expects arguments as a dict, but we store them as JSON
            # strings (OpenAI format). Convert back to dict here.
            if role == "assistant" and msg.get("tool_calls"):
                tool_calls = []
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    tool_calls.append({
                        "function": {
                            "name": fn.get("name", ""),
                            "arguments": args,
                        }
                    })
                out.append({
                    "role": "assistant",
                    "content": str(content) if content else "",
                    "tool_calls": tool_calls,
                })
                continue

            # ── Vision content blocks ──
            if isinstance(content, list):
                text_parts: list[str] = []
                images: list[str] = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "image_url":
                        url = block["image_url"]["url"]
                        if url.startswith("data:"):
                            _, b64 = url.split(",", 1)
                            images.append(b64)
                entry: dict = {"role": role, "content": " ".join(text_parts)}
                if images:
                    entry["images"] = images
                out.append(entry)
                continue

            # ── Standard text message ──
            out.append({"role": role, "content": str(content) if content else ""})

        return out

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream chat completion from Ollama with tool and vision support."""
        payload = {
            "model": req.model,
            "messages": self._prepare_messages(req.messages),
            "stream": req.stream,
            "keep_alive": f"{brain_settings.ollama_keep_alive_minutes}m",
            "options": {
                "temperature": req.temperature,
                "num_predict": req.max_tokens,
            },
        }
        if req.response_format:
            payload["format"] = req.response_format
            
        if req.tools:
            payload["tools"] = req.tools

        try:
            async with self._client.stream(
                "POST",
                "api/chat",
                json=payload,
                timeout=self._timeout,
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    err = body.decode(errors="replace")[:500]
                    yield ChatChunk(
                        type="error",
                        data={"code": "ollama_error", "message": f"Ollama {response.status_code}: {err}"},
                    )
                    return
                buf = ""  # accumulation buffer for XML tool call detection

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Ollama streams errors as {"error": "..."} lines (not HTTP 4xx)
                    if "error" in obj and not obj.get("message"):
                        yield ChatChunk(
                            type="error",
                            data={"code": "ollama_error", "message": obj["error"]},
                        )
                        return

                    if obj.get("done", False):
                        # Non-streaming mode: content is in the final message,
                        # not in individual chunks. Extract it before returning.
                        message = obj.get("message", {})
                        done_content = message.get("content", "")
                        if done_content:
                            yield ChatChunk(type="token", data=done_content)
                        # Flush any leftover buffer that never completed an XML block
                        if buf.strip():
                            yield ChatChunk(type="token", data=buf)
                        yield ChatChunk(
                            type="done",
                            data={
                                "model": obj.get("model"),
                                "tokens_in": obj.get("prompt_eval_count", 0),
                                "tokens_out": obj.get("eval_count", 0),
                            },
                        )
                        return

                    message = obj.get("message", {})

                    # Native Ollama tool calls (JSON format)
                    tool_calls = message.get("tool_calls")
                    if tool_calls:
                        for tc in tool_calls:
                            yield ChatChunk(
                                type="tool_call",
                                data={
                                    "id": tc.get("id", "0"),
                                    "name": tc["function"]["name"],
                                    "args": tc["function"]["arguments"],
                                },
                            )

                    # Ollama thinking models (glm, qwen, deepseek-r1, etc.)
                    # emit reasoning tokens via the "thinking" field as separate chunks
                    thinking = message.get("thinking", "")
                    if thinking:
                        yield ChatChunk(type="reasoning", data=thinking)

                    content = message.get("content", "")
                    if not content and not thinking:
                        # No content and no thinking — skip (e.g. empty keep-alive)
                        continue

                    if not content:
                        # Thinking-only chunk (content still empty)
                        continue

                    buf += content

                    # Drain complete XML tool call blocks without leaking them as tokens
                    _FC_OPEN = "<function_calls>"
                    while True:
                        start = buf.find(_FC_OPEN)
                        if start == -1:
                            # Check if buf ends with a partial prefix (split across tokens)
                            safe_end = len(buf)
                            for i in range(1, len(_FC_OPEN)):
                                if buf.endswith(_FC_OPEN[:i]):
                                    safe_end = len(buf) - i
                                    break
                            if safe_end > 0:
                                yield ChatChunk(type="token", data=buf[:safe_end])
                            buf = buf[safe_end:]
                            break
                        end = buf.find("</function_calls>")
                        if end == -1:
                            # Incomplete block — emit text before it, keep buffering
                            if start > 0:
                                yield ChatChunk(type="token", data=buf[:start])
                                buf = buf[start:]
                            break
                        end += len("</function_calls>")
                        # Emit text before the XML block
                        if start > 0:
                            yield ChatChunk(type="token", data=buf[:start])
                        # Convert XML to tool_call chunks
                        for tc in _parse_xml_tool_calls(buf[start:end]):
                            yield ChatChunk(type="tool_call", data=tc)
                        buf = buf[end:]
                        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                yield ChatChunk(
                    type="error",
                    data={
                        "code": "ollama_error",
                        "message": f"Ollama 503: {e.response.text.strip()}"
                    },
                )
            else:
                yield ChatChunk(
                    type="error",
                    data={"code": "upstream_http", "message": f"HTTP {e.response.status_code}: {e.response.text.strip()}"},
                )
        except httpx.RequestError as e:
            yield ChatChunk(
                type="error",
                data={"code": "upstream_http", "message": str(e)},
            )
        except Exception as e:
            yield ChatChunk(
                type="error",
                data={"code": "internal", "message": str(e)},
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via Ollama with fallback to legacy API."""
        if not texts:
            return []
        
        # Try new batch embed API first
        try:
            response = await self._client.post(
                "api/embed",
                json={
                    "model": brain_settings.ollama_embedding_model,
                    "input": texts,
                },
                timeout=self._timeout,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("embeddings", [])
        except Exception:
            pass

        # Fallback to legacy single embedding API
        embeddings = []
        for text in texts:
            try:
                response = await self._client.post(
                    "api/embeddings",
                    json={
                        "model": brain_settings.ollama_embedding_model,
                        "prompt": text,
                    },
                    timeout=self._timeout,
                )
                if response.status_code == 200:
                    data = response.json()
                    embeddings.append(data.get("embedding", []))
                else:
                    embeddings.append([])
            except Exception:
                embeddings.append([])
        
        return embeddings

    async def health(self) -> bool:
        """Check if Ollama server is healthy."""
        try:
            response = await self._client.get("/api/tags", timeout=2.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()