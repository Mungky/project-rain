---
name: vector-collection-designer
description: Use this skill when the DB Agent needs to design or modify a Qdrant collection (Phase 2+). Triggers on any new vector use case (document RAG, episodic memory, semantic search) or when changing embedding models. Covers vector size, distance metric, payload schema, indexing strategy, and the YAML registration that Backend reads. Do NOT use for relational data — that goes to Postgres.
---

# Skill: vector-collection-designer

## Purpose
Design Qdrant collections that match Rain's workload patterns and free-tier constraints. Get the vector size right, the distance metric right, the payload filterable, and the on-disk footprint manageable on a 16GB-RAM laptop.

## When to use
- Phase 2+: adding RAG over user documents.
- Phase 3+: episodic memory (recall past conversations by similarity).
- Any time the embedding model changes.

## When NOT to use
- Relational data (users, conversations, messages) → Postgres.
- Cache or session state → Redis.
- File blobs → MinIO.

## The Two Mandatory Files

### 1. `/db/qdrant_collections.yaml`
Single source of truth Backend reads at startup.

```yaml
# Edit this file to add/modify Qdrant collections.
# Backend reads this at startup and ensures collections exist.
# Vector size must match the embedding model in use (Contract 4).

collections:
  - name: documents
    description: User-uploaded document chunks for RAG.
    vector_size: 768                    # nomic-embed-text dimensions
    distance: Cosine                    # text similarity
    on_disk: true                       # vectors on disk, indices in RAM (low-RAM friendly)
    quantization:
      scalar:
        type: int8                      # 4x memory savings, minor recall hit
        always_ram: true                # quantized version stays in RAM
    payload_schema:
      user_id:
        type: keyword
        index: true                     # filterable
      document_id:
        type: keyword
        index: true
      chunk_index:
        type: integer
        index: false
      text:
        type: text
        index: false                    # store but don't index (saves space)
      source:
        type: keyword
        index: true

  - name: episodic_memory               # Phase 3
    description: Past conversation turns indexed for similarity recall.
    vector_size: 768
    distance: Cosine
    on_disk: true
    quantization:
      scalar:
        type: int8
        always_ram: true
    payload_schema:
      user_id:
        type: keyword
        index: true
      conversation_id:
        type: keyword
        index: true
      message_id:
        type: keyword
        index: false
      role:
        type: keyword
        index: true
      text:
        type: text
        index: false
      created_at:
        type: integer                   # unix timestamp for range filtering
        index: true
```

### 2. `/db/seeds/seed_qdrant_collections.py`
Idempotent. Backend can safely call this on every startup.

```python
import asyncio
from pathlib import Path
import yaml
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, ScalarQuantization, ScalarQuantizationConfig,
    ScalarType, PayloadSchemaType,
)


async def ensure_collections(client: AsyncQdrantClient, config_path: Path) -> None:
    cfg = yaml.safe_load(config_path.read_text())
    for c in cfg["collections"]:
        name = c["name"]
        exists = await client.collection_exists(name)
        if exists:
            # Verify vector size matches (cheap consistency check)
            info = await client.get_collection(name)
            actual = info.config.params.vectors.size
            if actual != c["vector_size"]:
                raise RuntimeError(
                    f"Collection {name} exists with vector_size={actual}, "
                    f"config says {c['vector_size']}. Recreate manually."
                )
            continue

        quant = None
        if c.get("quantization", {}).get("scalar"):
            sq = c["quantization"]["scalar"]
            quant = ScalarQuantization(scalar=ScalarQuantizationConfig(
                type=ScalarType(sq["type"]),
                always_ram=sq.get("always_ram", True),
            ))

        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=c["vector_size"],
                distance=Distance(c["distance"]),
                on_disk=c.get("on_disk", True),
            ),
            quantization_config=quant,
        )

        # Create payload indices for fields marked index: true
        for field, spec in c.get("payload_schema", {}).items():
            if spec.get("index"):
                pst = {
                    "keyword": PayloadSchemaType.KEYWORD,
                    "integer": PayloadSchemaType.INTEGER,
                    "float": PayloadSchemaType.FLOAT,
                    "text": PayloadSchemaType.TEXT,
                    "bool": PayloadSchemaType.BOOL,
                    "geo": PayloadSchemaType.GEO,
                }[spec["type"]]
                await client.create_payload_index(name, field, pst)


if __name__ == "__main__":
    from rain_backend.settings import settings
    client = AsyncQdrantClient(url=settings.qdrant_url)
    asyncio.run(ensure_collections(client, Path("db/qdrant_collections.yaml")))
```

## Design decisions

### Vector size (must match embedding model)

| Embedding model | Dim |
|---|---|
| `nomic-embed-text` (Ollama, default) | 768 |
| `mxbai-embed-large` (Ollama) | 1024 |
| `text-embedding-3-small` (OpenAI) | 1536 |
| `text-embedding-3-large` (OpenAI) | 3072 |

**Phase 1-3 default: 768 (nomic-embed-text).** Runs on CPU, no VRAM contention.

If user later picks an OpenAI embedder, they'll want a separate collection — embeddings from different models are not interchangeable.

### Distance metric

| Use case | Distance |
|---|---|
| Text similarity (RAG, episodic) | Cosine |
| Image similarity | Cosine or Dot |
| Recommendations (normalized vectors) | Dot |
| Geographic / Euclidean spaces | Euclid |

Default: **Cosine**.

### On-disk vs in-memory

For Rain's hardware (16GB RAM):
- `on_disk: true` for vectors (HUGE savings).
- `always_ram: true` on quantized version → fast search, full vectors fetched from disk only on top-K rerank.
- Payload indices in RAM (small, fast).

This keeps Qdrant under ~500MB resident even with millions of chunks.

### Quantization

| Quantization | Memory | Recall |
|---|---|---|
| None | 100% | 100% |
| int8 scalar | 25% | ~98% |
| Binary | 3% | ~85% |

**Default: int8 scalar.** 4x memory savings, almost no quality loss for text.

### Payload — what to store

YES:
- `user_id` (always — for filtering)
- `document_id`, `conversation_id`, `message_id` (foreign-key-style links to Postgres)
- `text` (the actual chunk — Backend doesn't have to round-trip to MinIO/Postgres for snippets)
- `source` (filename, URL, etc. — for citations)
- `created_at` as unix timestamp (for range filtering)

NO:
- Full document content (use MinIO)
- LLM-generated summaries that change (those go in Postgres)
- Sensitive PII without justification (Qdrant has no native row-level security)

### Payload indices — be selective

Index a payload field only if Backend will filter or sort on it. Each indexed field has a memory cost.

| Field | Index? |
|---|---|
| user_id | YES (always filter by it) |
| document_id | YES (group chunks of one document) |
| created_at | YES if you'll do "recent first" or range queries |
| chunk_index | NO (you fetch by ID, never filter on it) |
| text | NO (full-text search via Postgres if needed) |

## Chunking strategy (relevant when designing the collection)

Even though chunking happens in Backend, the collection design assumes:
- ~512 token chunks (so vector_size 768 has good signal-to-noise).
- ~50 token overlap (preserve context across boundaries).
- One vector per chunk, not per document.

If Backend Agent picks different chunk sizes, revisit `vector_size` choice.

## Quality bar
- `qdrant_collections.yaml` validates against itself (each entry has all required keys).
- Seed script is idempotent (run 100 times → same end state, no errors).
- Vector size in YAML matches the embedding model named in CONTRACTS.md.
- Tests bring up Qdrant via testcontainers, run seeder, assert collections + indices exist.

## Anti-patterns
- ❌ One collection per user (use payload filter instead).
- ❌ Different vector sizes in the same collection.
- ❌ No payload index on `user_id` (every query filters by it; lookup will be slow).
- ❌ Storing huge text fields (>10KB) in payload — chunk smaller.
- ❌ Mixing embedding models within a collection.
- ❌ `on_disk: false` on a 16GB-RAM machine for non-trivial datasets.
