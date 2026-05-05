"""Rain Brain MCP Server — Single Source of Truth for external agents.

Exposes Neural Context, Neural Archive, and Neural Baseline as MCP tools
via stdio transport. Reuses the existing service layer and database models.

Usage:
    uv run --package brain-mcp python -m brain_mcp.server
"""

import sys
import pathlib

# --- PATH INJECTION ---
# Ensure repo packages are importable when running outside the API server.
_repo_root = pathlib.Path.cwd().resolve()
_packages = _repo_root / "packages"
_for_pkg = pathlib.Path(__file__).resolve().parents[2] / "packages"
for _p in (str(_repo_root), str(_packages), str(_for_pkg)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json
import logging
import asyncio
from uuid import UUID
from datetime import UTC

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, ScalarQuantization, ScalarType, ScalarQuantizationConfig
from minio import Minio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from db.config import db_settings
from rain_brain.config import brain_settings
from rain_brain.services.context_service import ContextService, CONTEXT_COLLECTION
from rain_brain.services.conversation_service import ConversationService, DEFAULT_USER_ID
from rain_brain.services.preference_service import PreferenceService
from rain_brain.providers import get_provider

logger = logging.getLogger("brain_mcp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# ---------------------------------------------------------------------------
# Application lifecycle — holds DB engine, Qdrant client, Ollama provider
# ---------------------------------------------------------------------------

_app_state: dict = {}


async def _init_state() -> None:
    """Initialize DB engine, Qdrant client, Ollama provider, and MinIO client."""
    # DB
    engine = create_async_engine(db_settings.postgres_dsn, pool_pre_ping=True)
    _app_state["db_engine"] = engine
    _app_state["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)

    # Qdrant
    qdrant = AsyncQdrantClient(url=db_settings.qdrant_url)
    try:
        await qdrant.get_collections()
    except Exception as e:
        logger.warning("Qdrant not reachable at init: %s", e)
    _app_state["qdrant"] = qdrant

    # Ensure collections exist
    for collection_name in (CONTEXT_COLLECTION, "documents"):
        try:
            collections = await qdrant.get_collections()
            names = [c.name for c in collections.collections]
            if collection_name not in names:
                await qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=brain_settings.qdrant_vector_size,
                        distance=Distance.COSINE,
                    ),
                    quantization_config=ScalarQuantization(
                        scalar=ScalarQuantizationConfig(
                            type=ScalarType.INT8,
                            quantile=0.75,
                            always_ram=True,
                        )
                    ),
                )
                logger.info("Created Qdrant collection: %s", collection_name)
        except Exception as e:
            logger.warning("Qdrant collection init failed for %s: %s", collection_name, e)

    # Ollama provider (for embedding)
    _app_state["ollama"] = get_provider("ollama")

    # MinIO
    minio_client = None
    try:
        endpoint = brain_settings.minio_endpoint or "localhost:9000"
        minio_client = Minio(
            endpoint=endpoint,
            access_key=brain_settings.minio_access_key or "rain",
            secret_key=brain_settings.minio_secret_key or "rainminio",
            secure=brain_settings.minio_secure,
        )
        bucket = brain_settings.minio_bucket_uploads
        if not await asyncio.to_thread(minio_client.bucket_exists, bucket):
            await asyncio.to_thread(minio_client.make_bucket, bucket)
            logger.info("Created MinIO bucket: %s", bucket)
        logger.info("MinIO connected (endpoint=%s)", endpoint)
    except Exception as e:
        logger.warning("MinIO init failed — document storage unavailable: %s", e)
    _app_state["minio"] = minio_client


async def _cleanup() -> None:
    """Gracefully close connections."""
    qdrant = _app_state.get("qdrant")
    if qdrant:
        await qdrant.close()
    engine = _app_state.get("db_engine")
    if engine:
        await engine.dispose()


# ---------------------------------------------------------------------------
# MCP Server definition
# ---------------------------------------------------------------------------

server = Server("rain-brain")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="brain_get_baseline",
            description="Retrieve the user's Neural Baseline — preferences, episodic memory (key-value pairs), and custom system prompt. This is the foundational context that informs every conversation.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="brain_search",
            description="Semantic search across Neural Context (knowledge library) and Neural Archive (uploaded documents). Returns the most relevant chunks matching the query. Use this before answering questions that might require user-specific or project-specific context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "limit": {"type": "integer", "description": "Max results per collection (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="brain_get_context",
            description="List active Neural Context entries. These are curated knowledge fragments the user has saved. Optionally filter by category (e.g., Technical, Brand, Product, Personal).",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category, e.g. Technical, Brand, Product"},
                    "active_only": {"type": "boolean", "description": "Only return active entries (default true)", "default": True},
                },
            },
        ),
        Tool(
            name="brain_save_context",
            description="Save a new knowledge entry to Neural Context. The content will be automatically embedded into the vector store for future semantic retrieval. Use this when the user shares facts, decisions, or preferences worth remembering across sessions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short descriptive title"},
                    "content": {"type": "string", "description": "The knowledge content to store"},
                    "category": {"type": "string", "description": "Category label (e.g., Technical, Brand, Product, Personal)", "default": "Technical"},
                    "subcategory": {"type": "string", "description": "Optional sub-category"},
                },
                "required": ["title", "content"],
            },
        ),
        Tool(
            name="brain_save_document",
            description="Save text content as a document to Neural Archive. The text will be chunked, embedded, and stored in both MinIO and Qdrant for future RAG retrieval. Use this for longer content like architecture docs, meeting notes, or code references.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name for the stored document (e.g., 'meeting-notes-2024.md')"},
                    "content": {"type": "string", "description": "The full text content to store"},
                    "category": {"type": "string", "description": "Optional category tag"},
                },
                "required": ["filename", "content"],
            },
        ),
        Tool(
            name="brain_update_baseline",
            description="Upsert a key-value pair into the user's episodic memory (Neural Baseline). Use this when the user explicitly shares a preference, personal fact, or instruction they want remembered. Examples: preferred_language=TypeScript, coding_style=minimal comments, timezone=UTC+7.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Snake_case label for the memory (e.g., preferred_framework)"},
                    "value": {"type": "string", "description": "The value to store (e.g., Next.js)"},
                },
                "required": ["key", "value"],
            },
        ),
        Tool(
            name="brain_get_chat_history",
            description="Retrieve recent messages from a conversation. Useful for understanding context before continuing a thread or reviewing past decisions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string", "description": "UUID of the conversation"},
                    "limit": {"type": "integer", "description": "Max messages to return (default 20)", "default": 20},
                },
                "required": ["conversation_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    sf: async_sessionmaker = _app_state["session_factory"]
    qdrant: AsyncQdrantClient = _app_state["qdrant"]
    ollama = _app_state.get("ollama")
    minio_client = _app_state.get("minio")

    async with sf() as db:
        try:
            if name == "brain_get_baseline":
                return await _brain_get_baseline(db)

            elif name == "brain_search":
                return await _brain_search(db, qdrant, ollama, arguments)

            elif name == "brain_get_context":
                return await _brain_get_context(db, arguments)

            elif name == "brain_save_context":
                return await _brain_save_context(db, qdrant, ollama, arguments)

            elif name == "brain_save_document":
                return await _brain_save_document(db, qdrant, ollama, minio_client, arguments)

            elif name == "brain_update_baseline":
                return await _brain_update_baseline(db, arguments)

            elif name == "brain_get_chat_history":
                return await _brain_get_chat_history(db, arguments)

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.exception("Tool %s failed", name)
            return [TextContent(type="text", text=f"Error: {e}")]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _brain_get_baseline(db: AsyncSession) -> list[TextContent]:
    pref_svc = PreferenceService(db)
    from db.schemas import UserPreference
    from sqlalchemy import select
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == DEFAULT_USER_ID))
    pref = result.scalar_one_or_none()

    if pref is None:
        return [TextContent(type="text", text="No baseline found. User preferences not yet created.")]

    baseline = {
        "custom_system_prompt": pref.custom_system_prompt,
        "user_context": pref.user_context,
    }
    return [TextContent(type="text", text=json.dumps(baseline, ensure_ascii=False, indent=2))]


async def _brain_search(db: AsyncSession, qdrant: AsyncQdrantClient, ollama, arguments: dict) -> list[TextContent]:
    query = arguments["query"]
    limit = arguments.get("limit", 5)
    results: list[dict] = []

    if not ollama:
        return [TextContent(type="text", text="Error: Ollama provider not available for embedding.")]

    vectors = await ollama.embed([query])
    if not vectors or not vectors[0]:
        return [TextContent(type="text", text="Error: Failed to generate query embedding.")]

    for collection_name in (CONTEXT_COLLECTION, "documents"):
        try:
            count = await qdrant.count(collection_name)
            if count.count == 0:
                continue
        except Exception:
            continue

        try:
            search_result = await qdrant.query_points(
                collection_name=collection_name,
                query=vectors[0],
                limit=limit,
                with_payload=True,
            )
            source_label = "Neural Context" if collection_name == CONTEXT_COLLECTION else "Neural Archive"
            for p in search_result.points:
                results.append({
                    "source": source_label,
                    "title": p.payload.get("title") or p.payload.get("source", ""),
                    "text": p.payload.get("content") or p.payload.get("text", ""),
                    "score": getattr(p, "score", None),
                })
        except Exception as e:
            logger.warning("Search failed in %s: %s", collection_name, e)

    if not results:
        return [TextContent(type="text", text="No results found matching the query.")]

    lines = [f"Found {len(results)} results:\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"--- Result {i} ({r['source']}) ---")
        if r["title"]:
            lines.append(f"Title: {r['title']}")
        lines.append(r["text"])
        lines.append("")
    return [TextContent(type="text", text="\n".join(lines))]


async def _brain_get_context(db: AsyncSession, arguments: dict) -> list[TextContent]:
    ctx_svc = ContextService(db)
    category = arguments.get("category")
    active_only = arguments.get("active_only", True)

    entries = await ctx_svc.list_entries(category=category, active_only=active_only)

    if not entries:
        return [TextContent(type="text", text="No context entries found.")]

    lines = [f"Context entries ({len(entries)}):\n"]
    for e in entries:
        active = "active" if e.is_active else "inactive"
        created = e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else "?"
        lines.append(f"[{active}] {e.title} ({created})")
        if e.category:
            lines.append(f"  Category: {e.category}" + (f" / {e.subcategory}" if e.subcategory else ""))
        lines.append(f"  {e.content}")
        lines.append("")
    return [TextContent(type="text", text="\n".join(lines))]


async def _brain_save_context(db: AsyncSession, qdrant: AsyncQdrantClient, ollama, arguments: dict) -> list[TextContent]:
    ctx_svc = ContextService(db)
    entry = await ctx_svc.create_entry(
        title=arguments["title"],
        content=arguments["content"],
        category=arguments.get("category"),
        subcategory=arguments.get("subcategory"),
        source_type="manual",
        qdrant_client=qdrant,
        embed_provider=ollama,
    )
    result = {
        "id": str(entry.id),
        "title": entry.title,
        "category": entry.category,
        "is_active": entry.is_active,
        "created_at": entry.created_at.isoformat(),
    }
    return [TextContent(type="text", text=f"Context entry saved.\n{json.dumps(result, ensure_ascii=False, indent=2)}")]


async def _brain_save_document(
    db: AsyncSession,
    qdrant: AsyncQdrantClient,
    ollama,
    minio_client,
    arguments: dict,
) -> list[TextContent]:
    if not minio_client:
        return [TextContent(type="text", text="Error: MinIO storage not available. Cannot save documents.")]
    if not ollama:
        return [TextContent(type="text", text="Error: Ollama provider not available for embedding.")]

    import re as _re
    import mimetypes
    from io import BytesIO
    from uuid import uuid5, uuid4
    from datetime import datetime as _dt
    from qdrant_client.models import PointStruct
    from db.schemas import Document as DocumentModel
    from db.schemas.document import DocumentStatus
    from db.config import db_settings as _db_settings

    filename = arguments["filename"]
    content = arguments["content"]
    content_bytes = content.encode("utf-8")
    mime = mimetypes.guess_type(filename)[0] or "text/plain"

    doc_id = uuid5(uuid5(uuid4(), "rain-doc"), filename)
    minio_key = f"{DEFAULT_USER_ID}/{doc_id}/{filename}"

    # 1. Create DB row
    document = DocumentModel(
        id=doc_id,
        user_id=DEFAULT_USER_ID,
        filename=filename,
        mime=mime,
        minio_key=minio_key,
        source_type="manual",
        status=DocumentStatus.processing,
    )
    db.add(document)
    await db.commit()

    try:
        # 2. Store in MinIO
        await asyncio.to_thread(
            minio_client.put_object,
            bucket_name=brain_settings.minio_bucket_uploads,
            object_name=minio_key,
            data=BytesIO(content_bytes),
            length=len(content_bytes),
            content_type=mime,
        )

        # 3. Chunk & embed
        chunks = [c.strip() for c in _re.split(r"\n\n+", content.strip()) if c.strip()] if len(content.strip()) > 2000 else [content.strip()]
        if chunks:
            embeddings = await ollama.embed(chunks)
            DOC_NAMESPACE = uuid5(uuid4(), "rain-doc-ns")
            points = [
                PointStruct(
                    id=str(uuid5(DOC_NAMESPACE, f"{doc_id}:{i}")),
                    vector=embeddings[i],
                    payload={
                        "user_id": str(DEFAULT_USER_ID),
                        "document_id": str(doc_id),
                        "text": chunks[i],
                        "source": filename,
                    },
                )
                for i in range(len(chunks))
                if i < len(embeddings) and embeddings[i]
            ]
            if points:
                await qdrant.upsert(collection_name="documents", points=points)

        # 4. Finalize
        document.status = DocumentStatus.ready
        await db.commit()

    except Exception as e:
        logger.exception("Document save failed: %s", e)
        try:
            document.status = DocumentStatus.error
            await db.commit()
        except Exception:
            pass
        return [TextContent(type="text", text=f"Error saving document: {e}")]

    result = {
        "id": str(doc_id),
        "filename": filename,
        "status": "ready",
        "chunks": len(chunks) if chunks else 0,
    }
    return [TextContent(type="text", text=f"Document saved.\n{json.dumps(result, ensure_ascii=False, indent=2)}")]


async def _brain_update_baseline(db: AsyncSession, arguments: dict) -> list[TextContent]:
    pref_svc = PreferenceService(db)
    result = await pref_svc.update_memory(
        user_id=DEFAULT_USER_ID,
        key=arguments["key"],
        value=arguments["value"],
    )
    return [TextContent(type="text", text=f"Baseline updated: {json.dumps(result, ensure_ascii=False)}")]


async def _brain_get_chat_history(db: AsyncSession, arguments: dict) -> list[TextContent]:
    conv_svc = ConversationService(db)
    conversation_id = UUID(arguments["conversation_id"])
    limit = min(arguments.get("limit", 20), 50)

    conv = await conv_svc.get_conversation(conversation_id)
    if conv is None:
        return [TextContent(type="text", text=f"Conversation {conversation_id} not found.")]

    messages = conv.messages[-limit:] if len(conv.messages) > limit else conv.messages
    lines = [f"Conversation: {conv.title or 'Untitled'} (persona: {conv.persona})"]
    lines.append(f"Messages (last {len(messages)}):\n")
    for msg in messages:
        role = msg.role.upper()
        content = msg.content[:500] + ("..." if len(msg.content) > 500 else "")
        lines.append(f"[{role}] {content}")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    await _init_state()
    logger.info("Rain Brain MCP Server initialized")
    async with stdio_server() as (read_stream, write_stream):
        try:
            await server.run(read_stream, write_stream, server.create_initialization_options())
        finally:
            await _cleanup()

if __name__ == "__main__":
    asyncio.run(main())