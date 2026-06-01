"""Feedback-driven personalization loop.

Closes the loop on the thumbs up/down a user gives an assistant message:

- 👍 (feedback=+1): save the (query → answer) pair as a high-quality entry in the
  Few-Shot Library, so future similar questions are biased toward answers the user
  liked.
- 👎 (feedback=-1): ask the secretary model to infer ONE durable style/format
  preference and write it to the Neural Baseline (UserPreference.user_context),
  so future answers adapt to what the user actually wants.

Runs in the background (fire-and-forget) so the thumbs click returns instantly.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from qdrant_client import AsyncQdrantClient

from rain_brain.providers.base import ChatRequest
from rain_brain.config import brain_settings
from db.schemas import Message as MessageModel
from db.schemas.message import MessageRole
from rain_brain.services.conversation_service import DEFAULT_USER_ID

logger = logging.getLogger(__name__)


_DOWNVOTE_SYSTEM = (
    "The user gave a THUMBS-DOWN to the assistant answer below. Infer ONE durable, "
    "reusable preference about HOW they want answers — focus on style, format, length, "
    "tone, or depth, NOT the specific topic.\n"
    "Output EXACTLY one line in the form `<snake_case_key>: <preference, max 15 words>`.\n"
    "Use a STABLE key so it can be refined later. Allowed keys: answer_length, "
    "answer_format, detail_level, tone, code_style, language, citations.\n"
    "Examples:\n"
    "answer_length: keep answers short, under 4 sentences\n"
    "code_style: always include a runnable code example\n"
    "If you cannot infer a clear preference, output exactly: SKIP"
)


# Indonesian is written in ASCII, so an ASCII-ratio check can't distinguish it
# from English — detect it via common stopwords instead.
_ID_STOPWORDS = {
    "yang", "saya", "aku", "kamu", "apa", "dan", "di", "ini", "itu", "dengan",
    "untuk", "tidak", "adalah", "dari", "ke", "ada", "bisa", "kita", "atau",
    "juga", "akan", "sudah", "buat", "gak", "nggak", "kenapa", "bagaimana",
    "gimana", "tolong", "dong", "bang",
}


def _detect_language(text: str) -> str:
    words = {w.strip(".,!?;:").lower() for w in text.split()}
    if words & _ID_STOPWORDS:
        return "id"
    return "en"


async def _find_query_and_answer(db, message_id: UUID) -> tuple[str, str, UUID] | None:
    """Return (user_query, assistant_answer, conversation_id) for an assistant message."""
    res = await db.execute(select(MessageModel).where(MessageModel.id == message_id))
    msg = res.scalar_one_or_none()
    if msg is None or getattr(msg.role, "value", str(msg.role)) != "assistant":
        return None
    answer = (msg.content or "").strip()
    if not answer:
        return None

    # The query = the most recent user message before this assistant message.
    res2 = await db.execute(
        select(MessageModel)
        .where(
            MessageModel.conversation_id == msg.conversation_id,
            MessageModel.role == MessageRole.user,
            MessageModel.created_at < msg.created_at,
        )
        .order_by(MessageModel.created_at.desc())
        .limit(1)
    )
    user_msg = res2.scalar_one_or_none()
    query = (user_msg.content or "").strip() if user_msg else ""
    if not query:
        return None
    return query, answer, msg.conversation_id


async def _handle_upvote(db, qdrant_client, embed_provider, query: str, answer: str) -> None:
    """Save an approved (query → answer) pair as a high-quality few-shot example."""
    from rain_brain.services.few_shot_service import FewShotService
    from rain_brain.orchestrator.prompt_templates import detect_task_type

    fs = FewShotService(db)
    # Avoid duplicates if the user re-clicks: skip if an entry with the same
    # answer sample already exists.
    existing = await fs.list_entries(limit=50)
    for e in existing:
        if (e.response_sample or "").strip()[:200] == answer[:200]:
            logger.debug("feedback_loop: upvote already saved, skipping")
            return

    await fs.save_pattern(
        query_pattern=query[:500],
        response_structure="User-approved answer — match this depth, format, and tone.",
        response_sample=answer[:4000],
        task_type=detect_task_type(query),
        language=_detect_language(query),
        quality_score=0.9,
        source_ai="rain_feedback",
        qdrant_client=qdrant_client,
        embed_provider=embed_provider,
    )
    logger.info("feedback_loop: saved upvoted answer as few-shot pattern")


async def _handle_downvote(db, providers, query: str, answer: str) -> None:
    """Ask the secretary model to infer a style preference and store it in Baseline."""
    ollama = providers.get("ollama")
    if not ollama:
        logger.debug("feedback_loop: no ollama provider for downvote analysis")
        return

    req = ChatRequest(
        messages=[
            {"role": "system", "content": _DOWNVOTE_SYSTEM},
            {"role": "user", "content": f"USER ASKED:\n{query[:1500]}\n\nASSISTANT ANSWERED (disliked):\n{answer[:2500]}"},
        ],
        model=brain_settings.ollama_extraction_model,
        temperature=0.2,
        stream=False,
        max_tokens=60,
    )

    text = ""
    async for chunk in ollama.chat(req):
        if chunk.type == "token":
            text += str(chunk.data)
        elif chunk.type == "done":
            if isinstance(chunk.data, dict) and chunk.data.get("content"):
                text = str(chunk.data["content"])
        elif chunk.type == "error":
            logger.warning("feedback_loop: downvote analysis error: %s", chunk.data)
            return

    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    if not line or line.upper().startswith("SKIP") or ":" not in line:
        logger.debug("feedback_loop: downvote produced no actionable preference (%r)", line)
        return

    key, value = line.split(":", 1)
    key = key.strip().lower().replace(" ", "_")[:40]
    value = value.strip()[:200]
    if not key or not value:
        return

    from rain_brain.services.preference_service import PreferenceService
    result = await PreferenceService(db).update_memory(user_id=DEFAULT_USER_ID, key=key, value=value)
    logger.info("feedback_loop: learned preference from downvote → %s: %s (%s)", key, value, result.get("status"))


async def process_feedback_background(
    providers: dict,
    db_engine: AsyncEngine,
    qdrant_client: AsyncQdrantClient | None,
    message_id: UUID,
    feedback: int,
) -> None:
    """Background entry point: turn a thumbs up/down into persistent learning."""
    if feedback not in (1, -1):
        return
    try:
        sm = async_sessionmaker(db_engine, expire_on_commit=False)
        async with sm() as db:
            found = await _find_query_and_answer(db, message_id)
            if not found:
                return
            query, answer, _conv_id = found

            if feedback == 1:
                if qdrant_client is None or not providers.get("ollama"):
                    logger.debug("feedback_loop: upvote skipped (no qdrant/embed)")
                    return
                await _handle_upvote(db, qdrant_client, providers["ollama"], query, answer)
            else:
                await _handle_downvote(db, providers, query, answer)
    except Exception as e:
        logger.error("feedback_loop: failed: %s", e)
