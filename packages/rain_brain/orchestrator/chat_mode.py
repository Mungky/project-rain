"""Linear chat orchestrator for Phase 2.

Handles history, RAG retrieval, tool calls, and response persistence.
"""

import logging
import json
import re
import asyncio
from datetime import datetime
from uuid import UUID, uuid4
from typing import AsyncIterator, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, async_sessionmaker
from qdrant_client import AsyncQdrantClient
from rain_brain.providers.base import ChatRequest, ChatChunk
from rain_brain.services.conversation_service import ConversationService
from rain_brain.services.message_service import MessageService
from rain_brain.services.skill_service import SkillService
from rain_brain.services.preference_service import PreferenceService
from rain_brain.skills.executor import SkillExecutor
from rain_brain.config import brain_settings
from rain_brain.orchestrator.prompt_templates import (
    build_chat_messages,
    build_rag_messages,
    get_temperature,
    detect_task_type,
    build_task_directive,
)
from db.schemas.message import MessageRole
from db.schemas import UserPreference
from rain_brain.observability import tracer
from rain_brain.providers.model_registry import get_model_capabilities, has_capability


logger = logging.getLogger(__name__)


def _step_preview(args: dict) -> str:
    """Return a short human-readable preview of tool arguments for the CoT display."""
    for key in ("url", "query", "code", "command", "path", "input"):
        val = args.get(key)
        if val:
            s = str(val)
            return s[:80] + "…" if len(s) > 80 else s
    if args:
        first_val = next(iter(args.values()))
        s = str(first_val)
        return s[:80] + "…" if len(s) > 80 else s
    return ""


# ── Background task GC protection ────────────────────────────────────────────
_bg_tasks: set = set()

def _fire_and_forget(coro) -> None:
    task = asyncio.ensure_future(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

# ── Context extraction constants ──────────────────────────────────────────────
# Primary model from config, then local fallbacks in order of preference
_EXTRACTION_MODEL_CANDIDATES = [
    brain_settings.ollama_extraction_model,  # from config (default: glm-5.1:cloud)
    "gemma4:31b-cloud",
    "gemma3:27b",
    "gemma3:12b",
    "llama3.3:latest",
    "llama3.1:8b",
    "mistral:latest",
]
_EXTRACTION_MODEL = _EXTRACTION_MODEL_CANDIDATES[0]  # resolved at runtime below

_EXTRACTION_SYSTEM = (
    "You are a context extraction agent for Project Rain. "
    "Extract valuable, reusable knowledge from this conversation and save it using save_context_entry.\n\n"
    "SAVE — specific, actionable knowledge:\n"
    "- Technical decisions: stack choices, architecture patterns, API designs, config values\n"
    "- User preferences: tools, workflows, coding style, communication style\n"
    "- Project facts: goals, constraints, team structure, key deadlines\n"
    "- Findings: solutions that worked, approaches that failed and why\n"
    "- GOOD: 'Rain stack: FastAPI+PostgreSQL+Qdrant backend, Next.js+shadcn frontend, Ollama for LLM'\n"
    "- BAD: 'User discussed their tech stack', 'We talked about architecture'\n\n"
    "NEVER SAVE — skip silently:\n"
    "- Passwords, API keys, tokens, secrets, credentials, or anything that looks like a secret\n"
    "- Personal identifying info: full names, email addresses, phone numbers, addresses\n"
    "- Trivial small talk, greetings, or meta-comments about the conversation itself\n\n"
    "Categories (pick the closest): technical | preference | project | research | decision\n\n"
    "Rules:\n"
    "- Each entry = one distinct topic. Content under 400 chars, dense and specific.\n"
    "- Call save_context_entry 0-5 times (0 if nothing substantive was discussed).\n"
    "- Priority order: decision > finding > preference > trivia. Skip trivia entirely.\n"
    "- After all saves, reply: done"
)


async def _extract_context_background(
    providers: dict,
    db_engine: AsyncEngine,
    qdrant_client: AsyncQdrantClient | None,
    messages_snapshot: list[dict],
) -> None:
    """Background task: extract and persist key context points from the recent turn."""
    try:
        ollama = providers.get("ollama")
        if not ollama:
            return

        # Resolve extraction model: use first available from candidate list
        extraction_model = _EXTRACTION_MODEL
        try:
            available = await ollama.list_models()
            for candidate in _EXTRACTION_MODEL_CANDIDATES:
                if candidate in available:
                    extraction_model = candidate
                    break
            else:
                if available:
                    chat_models = [m for m in available if "embed" not in m.lower()]
                    if chat_models:
                        extraction_model = chat_models[0]
                    else:
                        logger.debug("bg_extract: no chat-capable Ollama model found, skipping")
                        return
                else:
                    logger.debug("bg_extract: no Ollama models available, skipping")
                    return
        except Exception:
            pass  # fall back to _EXTRACTION_MODEL

        convo_text = "\n".join(
            f"{m['role'].upper()}: {str(m.get('content', ''))[:600]}"
            for m in messages_snapshot
            if m.get("content") and m.get("role") in ("user", "assistant")
        )
        if not convo_text.strip():
            return

        req = ChatRequest(
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM},
                {"role": "user", "content": f"Extract key context from:\n\n{convo_text}"},
            ],
            model=extraction_model,
            temperature=0.2,
            stream=True,
            tools=[CONTEXT_TOOL],
        )

        pending: list[dict] = []
        async for chunk in ollama.chat(req):
            if chunk.type == "tool_call":
                pending.append(chunk.data)
            elif chunk.type == "error":
                logger.warning("bg_extract model error: %s", chunk.data)
                return

        if not pending:
            logger.debug("bg_extract: nothing to save this turn")
            return

        from rain_brain.services.context_service import ContextService, CONTEXT_COLLECTION
        _sm = async_sessionmaker(db_engine, expire_on_commit=False)

        async with _sm() as bg_db:
            for tc in pending:
                if tc.get("name") != "save_context_entry":
                    continue
                args = tc.get("args", {})
                _content = args.get("content", "")
                if not _content:
                    continue
                _title = args.get("title") or (
                    _content[:60].rstrip() + "…" if len(_content) > 60 else _content
                )

                existing_id: str | None = None
                if qdrant_client and _content:
                    try:
                        vecs = await ollama.embed([_content])
                        if vecs and vecs[0]:
                            hits = await qdrant_client.query_points(
                                collection_name=CONTEXT_COLLECTION,
                                query=vecs[0],
                                limit=1,
                                score_threshold=0.82,
                            )
                            if hits.points:
                                existing_id = str(hits.points[0].id)
                    except Exception:
                        pass

                try:
                    ctx_svc = ContextService(bg_db)
                    if existing_id:
                        from uuid import UUID as _UUID
                        await ctx_svc.update_entry(
                            entry_id=_UUID(existing_id),
                            title=_title,
                            content=_content,
                            category=args.get("category"),
                            subcategory=args.get("subcategory"),
                            qdrant_client=qdrant_client,
                            embed_provider=ollama,
                        )
                        logger.info("bg_extract: updated %s → %s", existing_id, _title)
                    else:
                        entry = await ctx_svc.create_entry(
                            title=_title,
                            content=_content,
                            category=args.get("category"),
                            subcategory=args.get("subcategory"),
                            source_type="session",
                            qdrant_client=qdrant_client,
                            embed_provider=ollama,
                        )
                        logger.info("bg_extract: created → %s", entry.title)
                    await bg_db.commit()
                except Exception as save_err:
                    logger.error("bg_extract save failed: %s", save_err)
                    await bg_db.rollback()

    except Exception as e:
        logger.error("bg_extract task failed: %s", e)


async def _generate_title_background(
    providers: dict,
    db_engine: AsyncEngine,
    conversation_id: UUID,
    user_message: str,
    assistant_content: str,
) -> None:
    """Background task: generate a smart conversation title using LLM."""
    new_title: str | None = None
    try:
        ollama = providers.get("ollama")
        if ollama:
            req = ChatRequest(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Generate a concise title (max 6 words) for a conversation. "
                            "Output ONLY the title — no quotes, no punctuation at the end, no explanation. "
                            "Match the language of the user's message."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"User: {user_message[:300]}\nAssistant: {assistant_content[:200]}",
                    },
                ],
                model=brain_settings.ollama_default_model,
                temperature=0.1,
                stream=False,
                max_tokens=20,
            )
            title_text = ""
            async for chunk in ollama.chat(req):
                if chunk.type == "token":
                    title_text += str(chunk.data)
                elif chunk.type == "done":
                    if chunk.data and isinstance(chunk.data, dict):
                        title_text = str(chunk.data.get("content", title_text))
            candidate = title_text.strip().strip("\"'").strip()[:80]
            if candidate:
                new_title = candidate
    except Exception as e:
        logger.warning("title_gen LLM failed (non-blocking): %s", e)

    if not new_title:
        words = user_message.strip().split()
        new_title = " ".join(words[:10]) + ("..." if len(words) > 10 else "") or "Chat"

    try:
        _sm = async_sessionmaker(db_engine, expire_on_commit=False)
        async with _sm() as bg_db:
            await ConversationService(bg_db).update_conversation(
                conversation_id=conversation_id, title=new_title
            )
            await bg_db.commit()
    except Exception as e:
        logger.warning("title_gen: failed to save title: %s", e)


# Context window management: keep this many recent messages verbatim.
# Older messages get dropped with a note in the system prompt.
CONTEXT_TAIL_KEEP = 24

# Built-in system tools: always injected, not from skills_registry
MEMORY_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "memory_user_edits",
        "description": (
            "Permanently save a fact or preference about the user to long-term memory in the Brain (Neural Baseline/Archive). "
            "Call this silently (without announcing it) when the user shares personal info, "
            "preferences, goals, or context that should persist across sessions. "
            "Examples: preferred coding language, job role, ongoing project name, personal goals."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Short snake_case label, e.g. 'preferred_language', 'job_role'",
                },
                "value": {
                    "type": "string",
                    "description": "The value to store. Keep it concise.",
                },
            },
            "required": ["key", "value"],
        },
    },
}

CONTEXT_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "save_context_entry",
        "description": (
            "Save a concise summary of key knowledge to the permanent knowledge base. "
            "The content field must be a SUMMARY OF KEY POINTS — dense, scannable, useful standalone. "
            "NOT the full answer, NOT a description of what happened. "
            "GOOD content: '3 top crypto trading strategies: (1) HODL with conviction (CZ/Saylor), "
            "(2) On-chain analysis via Glassnode+CryptoQuant, (3) Technical: RSI+MACD+support-resistance.' "
            "BAD content: 'User asked about crypto trading', 'We discussed scalable architecture'. "
            "Call for: research findings user explicitly requested, project decisions, tech choices, "
            "domain knowledge specific to user's goals, action items, key recommendations. "
            "One call per distinct topic. Keep content under 400 chars per entry."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short label, e.g. 'Rain Frontend Framework'",
                },
                "content": {
                    "type": "string",
                    "description": "The specific fact to remember, with enough detail to be useful standalone.",
                },
                "category": {
                    "type": "string",
                    "enum": ["Technical", "Brand", "Market", "Product", "Personal", "Demographic"],
                    "description": "Category for the knowledge entry.",
                },
                "subcategory": {
                    "type": "string",
                    "description": "Optional sub-label, e.g. 'Frontend', 'Backend', 'Infrastructure'.",
                },
            },
            "required": ["title", "content", "category"],
        },
    },
}


async def _run_nimbus(
    conversation_id: UUID,
    user_message: str,
    model: str,
    providers: dict,
    db: AsyncSession,
    user_id: UUID,
) -> AsyncIterator[ChatChunk]:
    """Nimbus persona: generate an image from the prompt and stream as markdown."""
    from rain_brain.providers.image_gen import generate_image

    message_service = MessageService(db)

    # Resolve API keys from user preferences
    api_keys: dict | None = None
    try:
        pref_result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        pref = pref_result.scalar_one_or_none()
        if pref and pref.api_keys:
            api_keys = pref.api_keys
    except Exception:
        pass

    content_parts: list[str] = []

    async for chunk in generate_image(user_message, model, providers, api_keys):
        if chunk.type == "token":
            content_parts.append(chunk.data)
            yield chunk
        elif chunk.type == "error":
            yield chunk
            return
        # "done" from generate_image is replaced by our own below

    assistant_content = "".join(content_parts)

    try:
        msg = await message_service.create_message(
            conversation_id=conversation_id,
            role=MessageRole.assistant,
            content=assistant_content,
            model=model,
        )
        await db.commit()
        yield ChatChunk(type="done", data={"message_id": str(msg.id), "model": model})
    except Exception as e:
        await db.rollback()
        logger.error("_run_nimbus: failed to save assistant message: %s", e)
        yield ChatChunk(type="done", data={"model": model})


async def _run_shower(
    conversation_id: UUID,
    user_message: str,
    model: str,
    providers: dict,
    db: AsyncSession,
    user_id: UUID,
    current_date: str,
) -> AsyncIterator[ChatChunk]:
    """Shower persona: quick direct LLM call, no tools, no ReAct, no RAG.

    Reads Neural Baseline for light personalization only.
    """
    from rain_brain.orchestrator.prompt_templates import SHOWER_PERSONA_PRELUDE

    message_service = MessageService(db)

    # Resolve provider
    if model.startswith("claude"):
        provider_name = "anthropic"
    elif model.startswith("gpt") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4"):
        provider_name = "openai"
    elif model.startswith("gemini"):
        provider_name = "google"
    else:
        provider_name = "ollama"

    provider = providers.get(provider_name)
    if not provider:
        yield ChatChunk(type="error", data={
            "code": "no_provider",
            "message": f"No provider available for model '{model}'."
        })
        return

    # Minimal system prompt + user context only (no conversation history, no Brain)
    system_instruction = (
        f"{SHOWER_PERSONA_PRELUDE}\n\n"
        f"Today is {current_date}."
    )

    # Light personalization: read Neural Baseline only
    try:
        pref_result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        preference = pref_result.scalar_one_or_none()
        if preference and preference.user_context:
            formatted = PreferenceService.format_for_prompt(preference.user_context)
            system_instruction += f"\n\nWhat you know about the user:\n{formatted}"
    except Exception as e:
        logger.warning("_run_shower: failed to fetch user preferences: %s", e)

    # System + user only (no history for speed and token savings)
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_message},
    ]

    req = ChatRequest(
        messages=messages,
        model=model,
        temperature=0.3,
        stream=True,
        tools=None,
    )

    assistant_content = ""
    async for chunk in provider.chat(req):
        if chunk.type == "token":
            assistant_content += str(chunk.data)
            yield chunk
        elif chunk.type == "error":
            yield chunk
            return
        elif chunk.type == "done":
            if isinstance(chunk.data, dict):
                total_in = chunk.data.get("tokens_in", 0)
                total_out = chunk.data.get("tokens_out", 0)
            else:
                total_in, total_out = 0, 0

    try:
        msg = await message_service.create_message(
            conversation_id=conversation_id,
            role=MessageRole.assistant,
            content=assistant_content,
            model=model,
            tokens_in=total_in,
            tokens_out=total_out,
        )
        await db.commit()
        yield ChatChunk(type="done", data={
            "message_id": str(msg.id),
            "model": model,
            "tokens_in": total_in,
            "tokens_out": total_out,
        })
    except Exception as e:
        await db.rollback()
        logger.error("_run_shower: failed to save assistant message: %s", e)
        yield ChatChunk(type="done", data={"model": model})


async def run_chat(
    conversation_id: UUID,
    user_message: str,
    model: str | None,
    providers: dict[str, Any],
    db: AsyncSession,
    qdrant_client: AsyncQdrantClient | None = None,
    attachments: list[dict] | None = None,
    db_engine: AsyncEngine | None = None,
    minio_client=None,
) -> AsyncIterator[ChatChunk]:
    """Run the chat flow with RAG, skill execution, and episodic memory."""
    conversation_service = ConversationService(db)
    message_service = MessageService(db)
    skill_service = SkillService(db)
    preference_service = PreferenceService(db)
    skill_executor = SkillExecutor()

    conversation = await conversation_service.get_conversation(conversation_id)
    if conversation is None:
        yield ChatChunk(
            type="error",
            data={"code": "conversation_not_found", "message": f"Conversation {conversation_id} not found"},
        )
        return

    persona = getattr(conversation, "persona", "drizzle")
    logger.info("run_chat: conv=%s model_hint=%s persona=%s", conversation_id, model or "auto", persona)

    # ── Model selection via tag-based rotation ────────────────────────────────
    # If the request explicitly provides a model, honour it (manual API override).
    # Otherwise, use the model_router to pick the best registered model by tag.
    from rain_brain.orchestrator.model_router import select_model as _select_model

    # Quick check for attachment types — needed for tag detection
    _has_images = bool(attachments and any(
        a.get("mime_type", "text/plain").startswith("image/") for a in attachments
    ))
    _has_docs = bool(attachments and any(
        not a.get("mime_type", "text/plain").startswith("image/") for a in attachments
    ))
    _history_len = len(conversation.messages or [])

    # Load hidden_models from user preferences for the router
    _hidden: list[str] = []
    try:
        from db.schemas import UserPreference as _UP
        _pref_r = await db.execute(select(_UP).where(_UP.user_id == conversation.user_id))
        _pref = _pref_r.scalar_one_or_none()
        if _pref and _pref.hidden_models:
            _hidden = _pref.hidden_models
    except Exception:
        pass

    if not model:
        model = await _select_model(
            message=user_message,
            persona=persona,
            db=db,
            has_images=_has_images,
            has_docs=_has_docs,
            history_length=_history_len,
            fallback=None,
            hidden_models=_hidden,
        )

    if not model:
        yield ChatChunk(type="error", data={"code": "no_model", "message": "No model registered for this persona. Add one in Settings → Models."})
        return

    logger.info("run_chat: resolved model=%s", model)

    # Determine provider early — used for prompt and tool customization below
    if model.startswith("claude"):
        provider_name = "anthropic"
    elif model.startswith("gpt") or model.startswith("dall-e") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4"):
        provider_name = "openai"
    elif model.startswith("gemini"):
        provider_name = "google"
    else:
        provider_name = "ollama"

    # --- Capability gate ---
    # For Ollama/unknown models, check DB overrides first
    model_caps = get_model_capabilities(model)
    if model_caps == ["chat"] and provider_name == "ollama":
        try:
            from db.schemas.model_capability_override import ModelCapabilityOverride as _MCO
            _override = await db.execute(
                select(_MCO).where(_MCO.model_id == model)
            )
            _row = _override.scalar_one_or_none()
            if _row and _row.capabilities:
                model_caps = _row.capabilities
        except Exception:
            pass
    if "image-gen" in model_caps and "chat" not in model_caps and persona != "nimbus":
        yield ChatChunk(type="error", data={
            "code": "capability_mismatch",
            "message": f"'{model}' is an image generation model. Use the Generate Image feature to create images.",
        })
        return

    # Build the LLM user message — handle image attachments for vision
    llm_user_message: str | list = user_message

    if attachments:
        image_attachments = [a for a in attachments if a.get("mime_type", "text/plain").startswith("image/")]
        text_attachments  = [a for a in attachments if not a.get("mime_type", "text/plain").startswith("image/")]

        if image_attachments:
            if "vision" not in model_caps:
                yield ChatChunk(type="error", data={
                    "code": "capability_mismatch",
                    "message": f"Model '{model}' does not support image input. Select a vision-capable model or remove image attachments.",
                })
                return

            # Build OpenAI-format content blocks (all providers convert from this)
            content_blocks: list[dict] = []
            ATTACH_CONTENT_MAX = 50_000
            if text_attachments:
                text_block = "\n\n".join(
                    f"[Attached: {a['name']}]\n```\n{a['content'][:ATTACH_CONTENT_MAX]}"
                    + ("\n[...truncated]" if len(a["content"]) > ATTACH_CONTENT_MAX else "")
                    + "\n```"
                    for a in text_attachments
                )
                content_blocks.append({"type": "text", "text": text_block})
            for a in image_attachments:
                content_blocks.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{a['mime_type']};base64,{a['content']}"},
                })
            if user_message.strip():
                content_blocks.append({"type": "text", "text": user_message.strip()})
            llm_user_message = content_blocks
        else:
            # Text-only attachments — inject as code blocks (existing behaviour)
            ATTACH_CONTENT_MAX = 50_000
            blocks = "\n\n".join(
                f"[Attached: {a['name']}]\n```\n{a['content'][:ATTACH_CONTENT_MAX]}"
                + ("\n[...truncated]" if len(a["content"]) > ATTACH_CONTENT_MAX else "")
                + "\n```"
                for a in text_attachments
            )
            llm_user_message = f"{blocks}\n\n{user_message}".strip() if user_message.strip() else blocks

    # Persist user message — store only the typed text, NOT the raw attachment content
    if attachments and not user_message.strip():
        display_content = f"[{len(attachments)} file(s) attached]"
    else:
        display_content = user_message

    # Auto-save attachments to Neural Archive (MinIO) if available
    saved_attachments: list[dict] = []
    if attachments:
        if not minio_client:
            logger.warning("MinIO not available — %d attachment(s) will NOT be saved to Neural Archive. "
                          "Start MinIO with: docker compose --profile phase2 up", len(attachments))
        else:
            from rain_brain.services.document_service import DocumentService as _DocService
            from rain_brain.config import brain_settings as _settings
            _doc_service = _DocService(db)
            for a in attachments:
                try:
                    import base64 as _b64
                    mime = a.get("mime_type", "text/plain")
                    raw_content = a.get("content", "")
                    if mime.startswith("image/"):
                        content_bytes = _b64.b64decode(raw_content)
                    else:
                        content_bytes = raw_content.encode("utf-8")
                    doc = await _doc_service.save_chat_attachment(
                        filename=a.get("name", "attachment"),
                        mime=mime,
                        content_bytes=content_bytes,
                        minio_client=minio_client,
                        settings=_settings,
                        message_id=None,
                    )
                    saved_attachments.append({"id": str(doc.id), "filename": doc.filename, "mime": doc.mime})
                except Exception as _e:
                    logger.error("Failed to save attachment '%s' to Neural Archive: %s", a.get("name", "?"), _e)

    try:
        user_msg_record = await message_service.create_message(
            conversation_id=conversation_id,
            role=MessageRole.user,
            content=display_content,
            attachments=saved_attachments if saved_attachments else None,
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Failed to save user message: %s", e)
        yield ChatChunk(type="error", data={"code": "database_error", "message": str(e)})
        return

    prev_messages = list(conversation.messages or [])

    # --- 0. Pre-branch: check for Shower (quick-reply, no tools) ---
    if persona == "shower":
        async for chunk in _run_shower(
            conversation_id=conversation_id,
            user_message=user_message,
            model=model,
            providers=providers,
            db=db,
            user_id=conversation.user_id,
            current_date=datetime.now().strftime("%A, %B %d, %Y"),
        ):
            yield chunk
        return

    # Nimbus persona: delegate to image generation flow
    if persona == "nimbus":
        async for chunk in _run_nimbus(
            conversation_id=conversation_id,
            user_message=user_message,
            model=model,
            providers=providers,
            db=db,
            user_id=conversation.user_id,
        ):
            yield chunk
        return

    prev_messages = list(conversation.messages or [])

    # --- 1. System Prompt: persona + date + user preferences ---
    current_date = datetime.now().strftime("%A, %B %d, %Y")

    # Check for a user-defined default prompt in the prompt library
    _default_system_base: str | None = None
    try:
        from db.schemas.prompt import Prompt as _PromptModel
        _prompt_result = await db.execute(
            select(_PromptModel).where(_PromptModel.is_default == True).limit(1)
        )
        _default_prompt = _prompt_result.scalar_one_or_none()
        if _default_prompt:
            _default_system_base = _default_prompt.content
    except Exception:
        pass

    if _default_system_base:
        system_instruction = f"{_default_system_base}\n\nToday is {current_date}."
    else:
        if persona == "storm":
            from rain_brain.orchestrator.prompt_templates import STORM_PERSONA_PRELUDE
            system_instruction = (
                f"{STORM_PERSONA_PRELUDE}\n\n"
                f"Today is {current_date}.\n"
                f"Knowledge cutoff: January 2026."
            )
        else:
            from rain_brain.orchestrator.prompt_templates import DRIZZLE_PERSONA_PRELUDE
            system_instruction = (
                f"{DRIZZLE_PERSONA_PRELUDE}\n\n"
                f"Today: {current_date}. Knowledge cutoff: Jan 2026."
            )
    # Inject task-specific directive — constrains model behavior before any context is loaded
    _detected_task = detect_task_type(user_message)
    _task_directive = build_task_directive(_detected_task)
    if _task_directive:
        system_instruction += f"\n\n{_task_directive}"

    # Inject built-in tools description for all providers that support function calling
    if provider_name != "ollama":
        system_instruction += (
            "\n\nBUILT-IN TOOLS (call silently, never announce):\n"
            "- update_user_memory: call when user shares personal info, preferences, or goals.\n"
            "- save_context_entry: call as part of your tool-calling sequence BEFORE writing your "
            "final answer. Use when: (1) you did research the user explicitly requested — call it "
            "1-4x with concise summaries of distinct key findings; "
            "(2) conversation produced project decisions, tech choices, or action items. "
            "Content = dense summary of key points, under 350 chars. "
            "NOT descriptions: never 'User asked about X' or 'We discussed Y' — "
            "save the actual knowledge: 'Method A works by doing B, used by C'."
        )
    try:
        pref_result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == conversation.user_id)
        )
        preference = pref_result.scalar_one_or_none()
        if preference:
            if preference.custom_system_prompt:
                system_instruction += f"\n\nCustom Instructions:\n{preference.custom_system_prompt}"
            if preference.user_context:
                formatted = PreferenceService.format_for_prompt(preference.user_context)
                system_instruction += f"\n\nUser profile — adapt style, depth, and language accordingly:\n{formatted}"
    except Exception as e:
        logger.warning("Failed to fetch user preferences: %s", e)

    # --- 1b. Always inject active context library entries ---
    # This gives the agent proactive awareness of the knowledge base,
    # unlike RAG which only injects on semantic similarity.
    try:
        from rain_brain.services.context_service import ContextService
        ctx_service = ContextService(db)
        ctx_entries = await ctx_service.list_entries(active_only=True)
        if ctx_entries:
            # Inject only the 8 most recent entries; RAG handles semantic retrieval for the rest
            lines = [
                f"- [{e.category or 'General'}] {e.title}: {e.content[:200]}"
                for e in ctx_entries[:8]
            ]
            system_instruction += (
                "\n\nPINNED CONTEXT (recent knowledge — use if relevant, ignore otherwise):\n"
                + "\n".join(lines)
            )
    except Exception as e:
        logger.warning("Failed to load context library: %s", e)

    # --- Observability trace (spans attached below) ---
    lf_trace = tracer.trace(
        name="chat",
        input=user_message,
        metadata={"model": model, "conversation_id": str(conversation_id)},
    )

    # --- 2. RAG Retrieval (documents + context library) ---
    context_text = None
    citations: list[str] = []
    if qdrant_client is not None:
        lf_rag_span = lf_trace.span(name="rag", input={"query": user_message[:200]})
        _rag_chunks_found = 0
        try:
            docs_count = await qdrant_client.count("documents")
            ctx_count = await qdrant_client.count("context_library")
            has_docs = docs_count.count > 0
            has_ctx = ctx_count.count > 0

            if has_docs or has_ctx:
                query_vectors = await providers["ollama"].embed([user_message])
                if query_vectors and len(query_vectors[0]) > 0:
                    all_chunks: list[dict] = []

                    if has_docs:
                        doc_result = await qdrant_client.query_points(
                            collection_name="documents",
                            query=query_vectors[0],
                            limit=4,
                            with_payload=True,
                        )
                        all_chunks += [
                            {"source": p.payload.get("source", "archive"), "text": p.payload.get("text", "")}
                            for p in doc_result.points
                        ]

                    if has_ctx:
                        ctx_result = await qdrant_client.query_points(
                            collection_name="context_library",
                            query=query_vectors[0],
                            limit=6,
                            with_payload=True,
                        )
                        for p in ctx_result.points:
                            all_chunks.append({
                                "source": p.payload.get("title", "context"),
                                "text": f"[{p.payload.get('title', '')}] {p.payload.get('content', '')}",
                                "score": getattr(p, "score", 0.0),
                                "collection": "context",
                            })

                    if all_chunks:
                        _rag_chunks_found = len(all_chunks)

                        # High-similarity context entries (>0.85) are injected directly into
                        # system prompt as authoritative knowledge — not buried in retrieved context
                        high_sim = [
                            c for c in all_chunks
                            if c.get("collection") == "context" and c.get("score", 0) > 0.85
                        ]
                        if high_sim:
                            hs_lines = "\n".join(f"• {c['text']}" for c in high_sim[:3])
                            system_instruction += (
                                "\n\nHIGHLY RELEVANT KNOWLEDGE (directly applicable — prioritize this):\n"
                                + hs_lines
                            )

                        regular_chunks = [c for c in all_chunks if c not in high_sim]
                        raw_context = "\n\n---\n\n".join(c["text"] for c in regular_chunks)
                        CONTEXT_TEXT_MAX = 30_000
                        context_text = (
                            "RETRIEVED CONTEXT (may or may not be relevant — ignore if unrelated):\n"
                            + raw_context[:CONTEXT_TEXT_MAX]
                        )
                        if len(raw_context) > CONTEXT_TEXT_MAX:
                            context_text += "\n\n[context truncated]"
                        citations = list({c["source"] for c in all_chunks})
                        yield ChatChunk(type="neural_context", data=all_chunks)

            lf_rag_span.end(output={"chunks": _rag_chunks_found})
        except Exception as e:
            lf_rag_span.end(output={"error": str(e)}, level="ERROR")
            logger.warning("RAG failed: %s", e)

    # --- 2b. Few-Shot Library: inject response patterns ---
    # Retrieve semantically similar examples to guide response format and depth.
    # Silent — never announced to the user. Only active when Qdrant + embed are available.
    _few_shot_ids: list[str] = []
    if qdrant_client and providers.get("ollama"):
        try:
            from rain_brain.services.few_shot_service import FewShotService
            _fs_service = FewShotService(db)
            _fs_results = await _fs_service.semantic_search(
                query=user_message,
                embed_provider=providers["ollama"],
                qdrant_client=qdrant_client,
                task_type=_detected_task if _detected_task != "general_chat" else None,
                limit=2,
                min_quality=0.75,
            )
            if _fs_results:
                _few_shot_ids = [r["id"] for r in _fs_results]
                _examples = "\n\n".join(
                    f"Pattern: {r['query_pattern']}\n"
                    f"Structure: {r['response_structure']}\n"
                    f"Example:\n{r['response_sample'][:600]}"
                    for r in _fs_results
                )
                system_instruction += (
                    "\n\nRESPONSE PATTERNS (follow this structure when applicable — "
                    "adapt but do not copy verbatim):\n" + _examples
                )
                logger.debug("few_shot: injected %d pattern(s) for task_type=%s", len(_fs_results), _detected_task)
        except Exception as _fs_err:
            logger.debug("few_shot retrieval failed (non-blocking): %s", _fs_err)

    # --- 2c. Session Registry: inject active cross-AI handoff context ---
    # If another AI handed off work to Rain, inject the session state so Rain
    # continues seamlessly without re-asking what was already done.
    try:
        from rain_brain.services.session_service import SessionService
        _sess_service = SessionService(db)
        _active_session = await _sess_service.get_active_session()
        if _active_session and _active_session.hand_off_to in (None, "rain", f"rain_{persona}"):
            _sess_block = _sess_service.format_for_prompt(_active_session)
            system_instruction += f"\n\n{_sess_block}"
            logger.info("run_chat: injected session handoff from %s", _active_session.source_ai)
    except Exception as _sess_err:
        logger.debug("session registry lookup failed (non-blocking): %s", _sess_err)

    # --- 3. Build Tools: skills + built-in memory tool ---
    skills = await skill_service.get_enabled_skills()
    if not conversation.auto_skills:
        # enabled_skills stores either UUIDs or names — support both
        enabled_identifiers = set(conversation.enabled_skills or [])
        skills = [
            s for s in skills
            if s.name in enabled_identifiers or str(s.id) in enabled_identifiers
        ]

    tools: list[dict] = skill_service.get_tools_for_llm(skills)
    model_supports_tools = "tools" in model_caps

    # All Ollama models use the XML tool-call path regardless of capability flags.
    # Sending native JSON tools causes silent failures for cloud-proxy Ollama models
    # (kimi, gemma-cloud, etc.). Local models that support tools get XML instructions
    # injected into the system prompt instead.
    ollama_uses_xml = provider_name == "ollama"

    if model_supports_tools and provider_name != "ollama":
        tools.append(MEMORY_TOOL)
        tools.append(CONTEXT_TOOL)
    elif not model_supports_tools and not ollama_uses_xml:
        tools = []

    if skills and (model_supports_tools or ollama_uses_xml):
        skill_info = "\n".join(
            f"- {s.name}: {s.manifest_json.get('description', '')}" for s in skills
        )
        system_instruction += (
            f"\n\nIMPORTANT: Your knowledge cutoff is late 2024. Today is {current_date}. "
            "For events or data from 2025/2026, use web search immediately — do not guess.\n\n"
            f"AVAILABLE TOOLS:\n{skill_info}\n\n"
            "To call a tool, output EXACTLY this XML format (no other text before the tag):\n"
            "<function_calls>\n"
            "<invoke name=\"TOOL_NAME\">\n"
            "<parameter name=\"PARAM\">VALUE</parameter>\n"
            "</invoke>\n"
            "</function_calls>"
        )
    elif model_supports_tools and not ollama_uses_xml:
        system_instruction += "\n\nNo external tools are enabled."

    # For Ollama XML-path: never send JSON tools to provider
    if ollama_uses_xml:
        tools = []

    # --- 4. Build LLM message list ---
    # Two-pass context trimming:
    #   Pass 1 — message count cap (prevent O(n) memory growth)
    #   Pass 2 — byte budget cap (prevent "prompt too large" from huge attachments in history)
    # Target ~180k chars in history ≈ ~45k tokens, safe for all models including small Ollama ones.
    HISTORY_BYTE_BUDGET = 180_000

    def _content_len(content) -> int:
        if isinstance(content, str):
            return len(content)
        if isinstance(content, list):
            return sum(len(b.get("text", "")) for b in content if isinstance(b, dict))
        return 0

    def _strip_images(content):
        """Replace base64 image blocks with a placeholder to keep history lean."""
        if not isinstance(content, list):
            return content
        out = []
        for block in content:
            if block.get("type") == "image_url":
                out.append({"type": "text", "text": "[image]"})
            else:
                out.append(block)
        return out

    windowed_messages = prev_messages
    if len(prev_messages) > CONTEXT_TAIL_KEEP:
        windowed_messages = prev_messages[-CONTEXT_TAIL_KEEP:]

    # Build history with images stripped (they live in the current message only)
    msg_history = [
        {"role": m.role, "content": _strip_images(m.content)}
        for m in windowed_messages
    ]

    # Pass 2: drop oldest messages until total history fits in byte budget
    while msg_history and sum(_content_len(m["content"]) for m in msg_history) > HISTORY_BYTE_BUDGET:
        msg_history.pop(0)

    total_dropped = len(prev_messages) - len(msg_history)
    if total_dropped > 0:
        system_instruction += (
            f"\n\n[Note: {total_dropped} earlier messages were trimmed to fit context limits. "
            "Continue naturally from what's visible below.]"
        )

    msg_history.append({"role": "user", "content": llm_user_message})

    # Adaptive temperature: use detected task type; bump toward qa_with_context if RAG found context
    # but preserve code/translation/definition precision even when context is present
    _precision_tasks = {"code", "translation", "definition", "extraction", "json"}
    task_type = _detected_task if _detected_task in _precision_tasks else (
        "qa_with_context" if context_text else _detected_task
    )
    temperature = get_temperature(task_type)

    if context_text:
        llm_messages = build_rag_messages(msg_history, context=context_text, system_instruction=system_instruction)
    else:
        llm_messages = build_chat_messages(msg_history, system_instruction=system_instruction)

    # --- 5. Resolve Provider ---
    # DB key always wins over startup provider — user may have set a key via Settings UI
    # after startup, or the startup provider was initialized with no/wrong key from env.
    provider = None
    if provider_name != "ollama":
        try:
            from rain_brain.providers import AnthropicProvider, OpenAIProvider, GoogleProvider
            _pref_result = await db.execute(
                select(UserPreference).where(UserPreference.user_id == conversation.user_id)
            )
            _pref = _pref_result.scalar_one_or_none()
            if _pref and _pref.api_keys:
                _cfg = _pref.api_keys.get(provider_name, {})
                _key = _cfg.get("key", "").strip()
                if _key:
                    if provider_name == "anthropic":
                        provider = AnthropicProvider(api_key=_key)
                    elif provider_name == "openai":
                        provider = OpenAIProvider(api_key=_key)
                    elif provider_name == "google":
                        provider = GoogleProvider(api_key=_key)
        except Exception as e:
            logger.warning("Failed to build provider %s from DB key: %s", provider_name, e)

    # Fall back to startup provider if DB has no key configured
    if provider is None:
        provider = providers.get(provider_name)

    if not provider:
        yield ChatChunk(
            type="error",
            data={"code": "provider_unavailable", "message": f"No API key configured for {provider_name}. Please add one in Settings → API Credentials."},
        )
        return

    # --- 6. ReAct Streaming Loop ---
    # Reason → Act (tool call) → Observe (result) → Reason again.
    # Explicit iteration cap instead of recursion; tools stay available across all turns.
    # Storm persona gets more iterations for deep multi-step reasoning.
    MAX_TOOL_ITERATIONS = 15 if persona == "storm" else 8

    assistant_content = ""
    reasoning_content = ""
    is_thinking = False
    final_done_chunk = None
    total_tokens_in = 0
    total_tokens_out = 0
    collected_tool_events: list[dict] = []
    collected_react_steps: list[dict] = []

    async def _execute_tool(tool_name: str, tool_args: dict, lf_parent: Any = None) -> dict:
        """Execute a single tool and return its result."""
        lf_span = (lf_parent or lf_trace).span(
            name=f"tool:{tool_name}",
            input=tool_args,
        ) if lf_parent is not None or tracer.enabled else _noop_span()

        try:
            if tool_name == "memory_user_edits":
                result = await preference_service.update_memory(
                    user_id=conversation.user_id,
                    key=tool_args.get("key", ""),
                    value=tool_args.get("value", ""),
                )
            elif tool_name == "save_context_entry":
                try:
                    from rain_brain.services.context_service import ContextService, CONTEXT_COLLECTION
                    ctx_svc = ContextService(db)
                    existing_id: str | None = None
                    _content = tool_args.get("content", "")
                    _title = tool_args.get("title") or (_content[:60].rstrip() + "…" if len(_content) > 60 else _content)
                    _embed = providers.get("ollama")
                    if qdrant_client and _embed and _content:
                        try:
                            _vecs = await _embed.embed([_content])
                            if _vecs and _vecs[0]:
                                _hits = await qdrant_client.query_points(
                                    collection_name=CONTEXT_COLLECTION,
                                    query=_vecs[0],
                                    limit=1,
                                    score_threshold=0.82,
                                )
                                if _hits.points:
                                    existing_id = str(_hits.points[0].id)
                        except Exception:
                            pass

                    if existing_id:
                        from uuid import UUID as _UUID
                        await ctx_svc.update_entry(
                            entry_id=_UUID(existing_id),
                            title=_title,
                            content=_content or None,
                            category=tool_args.get("category"),
                            subcategory=tool_args.get("subcategory"),
                            qdrant_client=qdrant_client,
                            embed_provider=_embed,
                        )
                        logger.info("save_context_entry: updated %s → %s", existing_id, _title)
                        result = {"status": "updated", "id": existing_id, "title": _title}
                    else:
                        entry = await ctx_svc.create_entry(
                            title=_title,
                            content=_content,
                            category=tool_args.get("category"),
                            subcategory=tool_args.get("subcategory"),
                            source_type="session",
                            qdrant_client=qdrant_client,
                            embed_provider=_embed,
                        )
                        logger.info("save_context_entry: created → %s", entry.title)
                        result = {"status": "saved", "id": str(entry.id), "title": entry.title}
                except Exception as e:
                    logger.error("save_context_entry failed: %s", e)
                    result = {"status": "error", "message": str(e)}
            else:
                logger.info("Executing skill: %s args=%s", tool_name, tool_args)
                result = await skill_executor.execute(tool_name, tool_args)
                logger.info("Skill %s returned: %s", tool_name, json.dumps(result)[:200])

            lf_span.end(output=result)
            return result
        except Exception as e:
            lf_span.end(output={"error": str(e)}, level="ERROR")
            raise

    def _noop_span():
        from rain_brain.observability.tracer import _Noop
        return _Noop()

    current_messages: list[dict] = list(llm_messages)
    _tool_call_counts: dict[str, int] = {}  # dedup: track (name, args_json) → count

    for _iter in range(MAX_TOOL_ITERATIONS):
        # Reset per-iteration content — only the LAST iteration's answer is kept.
        # This prevents duplication when the model answers, spawns more tools,
        # and answers again in a later iteration.
        assistant_content = ""
        lf_iter_span = lf_trace.span(
            name=f"react_iter_{_iter}",
            metadata={"iteration": _iter},
        )

        _retry_with_fallback = False

        req = ChatRequest(
            messages=current_messages,
            model=model,
            temperature=temperature,
            stream=True,
            tools=tools if tools else None,
        )

        pending_tool_calls: list[dict] = []
        iter_has_error = False
        
        # Buffer for detecting tags across tokens
        stream_buffer = ""

        async for chunk in provider.chat(req):
            if chunk.type == "token":
                token = str(chunk.data)
                stream_buffer += token

                while stream_buffer:
                    if not is_thinking:
                        if "<think>" in stream_buffer:
                            # Yield anything before <think> as normal tokens (unlikely but possible)
                            pre, match, post = stream_buffer.partition("<think>")
                            if pre:
                                assistant_content += pre
                                yield ChatChunk(type="token", data=pre)
                            
                            is_thinking = True
                            stream_buffer = post
                            # Do not yield empty reasoning chunk here, we yield tokens as they come
                            continue
                        else:
                            # Not thinking and no <think> tag found yet.
                            # But wait! The buffer might contain a partial tag (e.g. "<thi")
                            if "<" in stream_buffer:
                                # Keep the part from the first "<" in buffer, yield before it
                                idx = stream_buffer.find("<")
                                if idx > 0:
                                    pre = stream_buffer[:idx]
                                    assistant_content += pre
                                    yield ChatChunk(type="token", data=pre)
                                    stream_buffer = stream_buffer[idx:]
                                break # Wait for more tokens
                            else:
                                # No tag started, yield all
                                assistant_content += stream_buffer
                                yield ChatChunk(type="token", data=stream_buffer)
                                stream_buffer = ""
                                break
                    else:
                        # is_thinking = True
                        if "</think>" in stream_buffer:
                            pre, match, post = stream_buffer.partition("</think>")
                            if pre:
                                reasoning_content += pre
                                yield ChatChunk(type="reasoning", data=pre)
                            
                            is_thinking = False
                            stream_buffer = post
                            continue
                        else:
                            # Thinking and no </think> tag found yet.
                            if "<" in stream_buffer:
                                idx = stream_buffer.find("<")
                                if idx > 0:
                                    pre = stream_buffer[:idx]
                                    reasoning_content += pre
                                    yield ChatChunk(type="reasoning", data=pre)
                                    stream_buffer = stream_buffer[idx:]
                                break
                            else:
                                reasoning_content += stream_buffer
                                yield ChatChunk(type="reasoning", data=stream_buffer)
                                stream_buffer = ""
                                break

            elif chunk.type == "reasoning":
                # Provider-native reasoning (e.g. Ollama "thinking" field).
                # Accumulate and pass through; skip the <tool_call>/`` tag state machine
                # since the provider already separated reasoning from content.
                reasoning_content += str(chunk.data)
                yield ChatChunk(type="reasoning", data=chunk.data)

            elif chunk.type == "tool_call":
                # If we have anything left in stream_buffer, flush it
                if stream_buffer:
                    if is_thinking:
                        reasoning_content += stream_buffer
                        yield ChatChunk(type="reasoning", data=stream_buffer)
                    else:
                        assistant_content += stream_buffer
                        yield ChatChunk(type="token", data=stream_buffer)
                    stream_buffer = ""

                collected_tool_events.append({"name": chunk.data["name"], "args": chunk.data.get("args", {}), "status": "calling"})
                yield chunk
                pending_tool_calls.append(chunk.data)

            elif chunk.type == "done":
                # Final flush
                if stream_buffer:
                    if is_thinking:
                        reasoning_content += stream_buffer
                        yield ChatChunk(type="reasoning", data=stream_buffer)
                    else:
                        assistant_content += stream_buffer
                        yield ChatChunk(type="token", data=stream_buffer)
                    stream_buffer = ""

                final_done_chunk = chunk
                if isinstance(chunk.data, dict):
                    total_tokens_in += chunk.data.get("tokens_in", 0)
                    total_tokens_out += chunk.data.get("tokens_out", 0)

            elif chunk.type == "error":
                # Special fallback for Ollama 503 Overloaded
                if chunk.data.get("code") == "ollama_error" and "503" in str(chunk.data.get("message", "")):
                    # Attempt fallback
                    _fallback_model = await _select_model(
                        message=user_message,
                        persona=persona,
                        db=db,
                        has_images=_has_images,
                        has_docs=_has_docs,
                        history_length=_history_len,
                        fallback=None,
                        hidden_models=_hidden + [model], # Exclude current failing model
                    )
                    
                    if _fallback_model and _fallback_model != model:
                        logger.warning(f"Ollama 503 Overloaded on '{model}'. Falling back to '{_fallback_model}'.")
                        
                        yield ChatChunk(
                            type="token", 
                            data=f"\n\n_⚠️ Model '{model}' overloaded. Retrying with fallback model '{_fallback_model}'..._\n\n"
                        )
                        
                        # Reset states for retry
                        model = _fallback_model
                        iter_has_error = True
                        _retry_with_fallback = True
                        assistant_content = ""
                        reasoning_content = ""
                        stream_buffer = ""
                        pending_tool_calls = []
                        collected_tool_events = []
                        
                        # Re-evaluate provider based on new model
                        if model.startswith("claude"):
                            provider_name = "anthropic"
                        elif model.startswith("gpt") or model.startswith("dall-e") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4"):
                            provider_name = "openai"
                        elif model.startswith("gemini"):
                            provider_name = "google"
                        else:
                            provider_name = "ollama"
                            
                        # Try to find provider instance for new model
                        try:
                            if _pref and _pref.api_keys:
                                _cfg = _pref.api_keys.get(provider_name, {})
                                _key = _cfg.get("key", "").strip()
                                if _key:
                                    if provider_name == "anthropic":
                                        from rain_brain.providers.anthropic import AnthropicProvider
                                        provider = AnthropicProvider(api_key=_key)
                                    elif provider_name == "openai":
                                        from rain_brain.providers.openai import OpenAIProvider
                                        provider = OpenAIProvider(api_key=_key)
                                    elif provider_name == "google":
                                        from rain_brain.providers.google import GoogleProvider
                                        provider = GoogleProvider(api_key=_key)
                        except Exception:
                            pass
                            
                        if not getattr(provider, "name", None) == provider_name:
                            provider = providers.get(provider_name)
                            
                        break

                yield chunk
                lf_iter_span.end(output={"error": chunk.data}, level="ERROR")
                iter_has_error = True
                break

        if _retry_with_fallback:
            continue

        if iter_has_error:
            break

        lf_iter_span.end(
            output={
                "tool_calls": len(pending_tool_calls),
                "tokens": len(assistant_content),
            }
        )

        if not pending_tool_calls:
            # No more tool calls — model is done reasoning
            break

        # Execute all buffered tool calls, then loop for next model response
        assistant_tool_msgs: list[dict] = []
        tool_results: list[tuple[str, str, str]] = []  # (call_id, name, result_json)

        for tc in pending_tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            call_id = f"call_{uuid4().hex[:12]}"

            # Dedup: skip tool if called 3+ times with same args
            _dedup_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
            _dedup_count = _tool_call_counts.get(_dedup_key, 0) + 1
            _tool_call_counts[_dedup_key] = _dedup_count

            if _dedup_count >= 3:
                logger.warning("dedup: skipping %s (called %dx)", _dedup_key, _dedup_count)
                result = {"skipped": True, "reason": f"Already called {_dedup_count}x with same args — move on."}
                yield ChatChunk(type="tool_result", data={"name": tool_name, "result": result})
                # Inject a strong hint that the model must stop repeating itself
                current_messages.append({
                    "role": "user",
                    "content": (
                        f"[System] You have called '{tool_name}' with the same arguments {_dedup_count} times. "
                        "The results are not changing. STOP searching now and deliver your final answer immediately. "
                        "Do NOT call any more tools — just write the answer."
                    ),
                })
                # Mark matching tool_event as skipped
                for te in collected_tool_events:
                    if te["name"] == tool_name and te["status"] == "calling":
                        te["result"] = result
                        te["status"] = "done"
                        break
                continue

            result = await _execute_tool(tool_name, tool_args, lf_parent=lf_iter_span)
            yield ChatChunk(type="tool_result", data={"name": tool_name, "result": result})
            # Mark matching tool_event as done with its result
            for te in collected_tool_events:
                if te["name"] == tool_name and te["status"] == "calling":
                    te["result"] = result
                    te["status"] = "done"
                    break
            assistant_tool_msgs.append({
                "id": call_id,
                "type": "function",
                "function": {"name": tool_name, "arguments": json.dumps(tool_args)},
                "_thought_signature": tc.get("_thought_signature"),
            })
            tool_results.append((call_id, tool_name, json.dumps(result)))

        current_messages.append(
            {"role": "assistant", "content": "", "tool_calls": assistant_tool_msgs}
        )
        for call_id, t_name, result_str in tool_results:
            current_messages.append({
                "role": "tool",
                "tool_call_id": call_id,   # OpenAI
                "tool_use_id": call_id,    # Anthropic
                "name": t_name,            # Gemini
                "content": result_str,
            })

        # Emit iteration summary so frontend can display structured CoT progress
        step_data = {
            "iteration": _iter,
            "tools": [
                {"name": tc["name"], "arg_preview": _step_preview(tc.get("args", {}))}
                for tc in pending_tool_calls
            ],
        }
        collected_react_steps.append(step_data)
        yield ChatChunk(type="react_step", data=step_data)

    # --- 6b. Self-Correction Pass ---
    # Self-correction is always enabled for Storm persona,
    # otherwise controlled via SELF_CORRECTION_ENABLED env var.
    _SELF_CORRECTION_ENABLED = brain_settings.self_correction_enabled or persona == "storm"

    if _SELF_CORRECTION_ENABLED:
        lf_correction_span = lf_trace.span(name="self_correction")
        try:
            _verify_msgs = list(current_messages) + [
                {"role": "assistant", "content": assistant_content.strip()},
                {
                    "role": "user",
                    "content": (
                        "[Self-review] Check your response above for factual errors, code bugs, "
                        "logical mistakes, or critical omissions. "
                        "If it is correct, reply with exactly: OK\n"
                        "If you found an issue, reply with the complete corrected response only — "
                        "no preamble, no explanation of what changed."
                    ),
                },
            ]
            _verify_req = ChatRequest(
                messages=_verify_msgs,
                model=model,
                temperature=0.1,
                stream=True,
                tools=None,
                max_tokens=500,
            )

            _corrected = ""
            async for _chunk in provider.chat(_verify_req):
                if _chunk.type == "token":
                    _corrected += str(_chunk.data)
                elif _chunk.type in ("done", "error"):
                    break

            _corrected = _corrected.strip()
            _ok_set = {
                "ok", "[ok]", "ok.", "correct", "looks correct", "this is correct",
                "no errors", "no issues", "looks good", "all good", "no errors found",
                "response is correct", "the response is correct", "answer is correct",
                "no corrections needed", "the answer is correct",
            }

            if _corrected and _corrected.lower().rstrip(".").strip() not in _ok_set and len(_corrected) > 150:
                logger.info(
                    "self_correction: revised (%d → %d chars)", len(assistant_content), len(_corrected)
                )
                yield ChatChunk(type="correction", data=_corrected)
                assistant_content = _corrected
                lf_correction_span.end(output={"corrected": True, "new_len": len(_corrected)})
            else:
                logger.debug("self_correction: verified OK")
                lf_correction_span.end(output={"corrected": False})
        except Exception as _ce:
            logger.warning("self_correction failed (non-blocking): %s", _ce)
            lf_correction_span.end(output={"error": str(_ce)}, level="ERROR")

    # --- 7. Persist Assistant Response ---
    if assistant_content.strip() or reasoning_content.strip():
        try:
            assistant_msg = await message_service.create_message(
                conversation_id=conversation_id,
                role=MessageRole.assistant,
                content=assistant_content.strip(),
                reasoning_content=reasoning_content.strip() or None,
                tokens_in=total_tokens_in,
                tokens_out=total_tokens_out,
                model=model,
                tool_events=collected_tool_events or None,
                react_steps=collected_react_steps or None,
            )

            # Generate title on first message; re-generate every 10 messages to reflect topic drift
            _msg_count = len(prev_messages) + 2
            _should_generate_title = (
                conversation.title is None
                or (_msg_count > 10 and _msg_count % 10 == 0)
            )
            if _should_generate_title and db_engine:
                _fire_and_forget(
                    _generate_title_background(
                        providers, db_engine, conversation_id,
                        user_message, assistant_content.strip(),
                    )
                )
            elif conversation.title is None:
                words = user_message.strip().split()
                _fallback_title = " ".join(words[:10]) + ("..." if len(words) > 10 else "") or "Chat"
                await conversation_service.update_conversation(
                    conversation_id=conversation_id,
                    title=_fallback_title,
                )
            else:
                # Update updated_at so conversation sorts to top
                await conversation_service.update_conversation(
                    conversation_id=conversation_id,
                )

            await db.commit()

            if final_done_chunk and isinstance(final_done_chunk.data, dict):
                final_done_chunk.data["message_id"] = str(assistant_msg.id)
                if citations:
                    final_done_chunk.data["citations"] = citations
        except Exception as e:
            logger.error("Persistence failed: %s", e)
            await db.rollback()

    if final_done_chunk:
        yield final_done_chunk
    else:
        yield ChatChunk(type="done", data={"model": model})

    # Finalize Langfuse trace
    lf_trace.update(output=assistant_content.strip()[:500] if assistant_content.strip() else None)

    # --- 8. Background Context Extraction ---
    if db_engine and assistant_content.strip():
        snapshot = [
            {"role": getattr(m.role, "value", str(m.role)), "content": m.content}
            for m in prev_messages[-10:]
        ]
        snapshot.append({"role": "user", "content": user_message})
        snapshot.append({"role": "assistant", "content": assistant_content.strip()})
        _fire_and_forget(_extract_context_background(providers, db_engine, qdrant_client, snapshot))

    # Increment usage count for retrieved few-shot examples (fire-and-forget)
    if _few_shot_ids and db_engine:
        async def _increment_few_shot_usage(ids: list[str], engine: AsyncEngine) -> None:
            try:
                from sqlalchemy.ext.asyncio import async_sessionmaker as _sm_factory
                _sm2 = _sm_factory(engine, expire_on_commit=False)
                async with _sm2() as _bg_db:
                    from rain_brain.services.few_shot_service import FewShotService as _FSS
                    _fss = _FSS(_bg_db)
                    for _fid in ids:
                        await _fss.increment_usage(UUID(_fid))
            except Exception as _e:
                logger.debug("few_shot usage increment failed: %s", _e)
        _fire_and_forget(_increment_few_shot_usage(_few_shot_ids, db_engine))

