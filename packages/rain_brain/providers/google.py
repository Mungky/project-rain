"""Google Gemini provider implementation."""

import asyncio
import base64
import json
import warnings
from typing import AsyncIterator

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai
from rain_brain.providers.base import Provider, ChatRequest, ChatChunk

_GEMINI_TIMEOUT = 120


def _build_schema(schema: dict) -> "genai.protos.Schema":
    """Convert JSON Schema dict to Gemini Schema proto."""
    type_map = {
        "string": genai.protos.Type.STRING,
        "number": genai.protos.Type.NUMBER,
        "integer": genai.protos.Type.INTEGER,
        "boolean": genai.protos.Type.BOOLEAN,
        "array": genai.protos.Type.ARRAY,
        "object": genai.protos.Type.OBJECT,
    }
    g_type = type_map.get(schema.get("type", "string"), genai.protos.Type.STRING)
    kwargs: dict = {"type_": g_type, "description": schema.get("description", "")}

    if g_type == genai.protos.Type.OBJECT:
        props = schema.get("properties", {})
        if props:
            kwargs["properties"] = {k: _build_schema(v) for k, v in props.items()}
        if "required" in schema:
            kwargs["required"] = schema["required"]
    elif g_type == genai.protos.Type.ARRAY and "items" in schema:
        kwargs["items"] = _build_schema(schema["items"])

    return genai.protos.Schema(**kwargs)


def _to_gemini_tools(tools: list[dict]) -> list["genai.protos.Tool"]:
    """Convert OpenAI-style tool list to Gemini Tool protos."""
    result = []
    for t in tools:
        fn = t.get("function", {})
        params = fn.get("parameters", {})
        try:
            parameters = _build_schema(params) if params else genai.protos.Schema(
                type_=genai.protos.Type.OBJECT,
            )
        except Exception:
            parameters = genai.protos.Schema(type_=genai.protos.Type.OBJECT)

        fd = genai.protos.FunctionDeclaration(
            name=fn.get("name", ""),
            description=fn.get("description", ""),
            parameters=parameters,
        )
        result.append(genai.protos.Tool(function_declarations=[fd]))
    return result


def _msg_to_content(msg: dict) -> "genai.protos.Content | None":
    """Convert a single chat message dict to a Gemini Content proto."""
    role = msg.get("role", "")
    content = msg.get("content") or ""

    if role == "tool":
        name = msg.get("name") or msg.get("tool_use_id") or "tool"
        try:
            result_val = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            result_val = {"result": content}
        if not isinstance(result_val, dict):
            result_val = {"result": result_val}
        return genai.protos.Content(
            role="user",
            parts=[genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=name,
                    response=result_val,
                )
            )],
        )

    if role == "assistant" and msg.get("tool_calls"):
        parts = []
        for tc in msg["tool_calls"]:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            part = genai.protos.Part(
                function_call=genai.protos.FunctionCall(
                    name=fn.get("name", ""),
                    args=args,
                )
            )
            # Restore thought_signature required by Gemini thinking models
            ts_b64 = tc.get("_thought_signature")
            if ts_b64:
                try:
                    part.thought_signature = base64.b64decode(ts_b64)
                except Exception:
                    pass
            parts.append(part)
        return genai.protos.Content(role="model", parts=parts)

    if role in ("user", "assistant"):
        gemini_role = "user" if role == "user" else "model"
        if isinstance(content, list):
            # Vision: convert OpenAI-format content blocks
            parts = []
            for block in content:
                if block.get("type") == "text" and block.get("text"):
                    parts.append(genai.protos.Part(text=block["text"]))
                elif block.get("type") == "image_url":
                    url = block["image_url"]["url"]
                    if url.startswith("data:"):
                        header, b64data = url.split(",", 1)
                        mime_type = header.split(";")[0].split(":")[1]
                        raw = base64.b64decode(b64data)
                        parts.append(genai.protos.Part(
                            inline_data=genai.protos.Blob(mime_type=mime_type, data=raw)
                        ))
            return genai.protos.Content(role=gemini_role, parts=parts) if parts else None
        elif content.strip():
            return genai.protos.Content(role=gemini_role, parts=[genai.protos.Part(text=content)])

    return None


class GoogleProvider:
    """Provider for Google Gemini API."""

    name = "google"

    def __init__(self, api_key: str):
        self._api_key = api_key
        genai.configure(api_key=api_key)

    async def list_models(self) -> list[str]:
        """Fetch available models from Google Gemini API (always valid for user's key)."""
        try:
            models = genai.list_models()
            # Only include models that support generateContent (chat)
            gemini_ids = []
            for m in models:
                if "generateContent" in getattr(m, "supported_generation_methods", []):
                    # Extract model name from models/xxx format
                    name = m.name.replace("models/", "")
                    gemini_ids.append(name)
            return sorted(gemini_ids)
        except Exception:
            # Fallback to conservative list if API fails
            return ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"]

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream chat completion from Google Gemini with tool call support."""
        try:
            system_parts: list[str] = []
            contents: list["genai.protos.Content"] = []

            for msg in req.messages:
                if msg.get("role") == "system":
                    txt = (msg.get("content") or "").strip()
                    if txt:
                        system_parts.append(txt)
                    continue
                c = _msg_to_content(msg)
                if c is not None:
                    contents.append(c)

            system_instruction = "\n\n".join(system_parts) or None

            if not contents:
                yield ChatChunk(type="error", data={"code": "google_error", "message": "No messages to send."})
                return

            history = contents[:-1]
            last_content = contents[-1]

            # Gemini rejects history that starts with a model turn
            while history and history[0].role != "user":
                history.pop(0)

            gemini_tools = _to_gemini_tools(req.tools) if req.tools else None

            model = genai.GenerativeModel(
                model_name=req.model,
                system_instruction=system_instruction,
                tools=gemini_tools,
            )

            chat_session = model.start_chat(history=history)

            tokens_in = 0
            tokens_out = 0

            async with asyncio.timeout(_GEMINI_TIMEOUT):
                response = await chat_session.send_message_async(
                    last_content.parts,
                    stream=True,
                    generation_config=genai.types.GenerationConfig(
                        temperature=req.temperature,
                        max_output_tokens=req.max_tokens,
                    ),
                )

                # Buffer tool calls — thought_signature is only fully populated
                # on the resolved (post-stream) response, not in streaming chunks.
                buffered_tool_calls: list[dict] = []

                async for chunk in response:
                    try:
                        for part in chunk.parts:
                            if hasattr(part, "function_call") and part.function_call.name:
                                fc = part.function_call
                                args = {k: v for k, v in fc.args.items()} if fc.args else {}
                                buffered_tool_calls.append({"name": fc.name, "args": args})
                            elif hasattr(part, "text") and part.text:
                                if getattr(part, "thought", False):
                                    yield ChatChunk(type="reasoning", data=part.text)
                                else:
                                    yield ChatChunk(type="token", data=part.text)
                    except Exception:
                        try:
                            text = chunk.text
                            if text:
                                yield ChatChunk(type="token", data=text)
                        except Exception:
                            continue

                # After stream fully consumed — extract thought_signatures from
                # the resolved response Parts (only available post-stream).
                if buffered_tool_calls:
                    try:
                        resolved_fc_parts = [
                            p for p in response.candidates[0].content.parts
                            if hasattr(p, "function_call") and p.function_call.name
                        ]
                        for i, tc in enumerate(buffered_tool_calls):
                            if i < len(resolved_fc_parts):
                                raw_ts = getattr(resolved_fc_parts[i], "thought_signature", None)
                                if raw_ts:
                                    tc["_thought_signature"] = base64.b64encode(bytes(raw_ts)).decode("ascii")
                    except Exception:
                        pass
                    for tc in buffered_tool_calls:
                        yield ChatChunk(type="tool_call", data=tc)

                # Token counts after stream is fully consumed
                try:
                    usage = response.usage_metadata
                    if usage:
                        tokens_in = getattr(usage, "prompt_token_count", 0) or 0
                        tokens_out = getattr(usage, "candidates_token_count", 0) or 0
                except Exception:
                    pass

            yield ChatChunk(
                type="done",
                data={"model": req.model, "tokens_in": tokens_in, "tokens_out": tokens_out},
            )

        except asyncio.TimeoutError:
            yield ChatChunk(
                type="error",
                data={"code": "google_timeout", "message": f"Gemini did not respond within {_GEMINI_TIMEOUT}s. Check model name or API key."},
            )
        except Exception as e:
            yield ChatChunk(
                type="error",
                data={"code": "google_error", "message": str(e)},
            )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=texts,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception:
            return [[] for _ in texts]

    async def health(self) -> bool:
        return True

    async def close(self) -> None:
        pass
