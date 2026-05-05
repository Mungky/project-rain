"""Search Neural Archive and Knowledge Base via Qdrant semantic search."""

import json
import os
import urllib.request
import urllib.error

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def _embed(text: str) -> list | None:
    payload = json.dumps({"model": "nomic-embed-text", "input": [text]}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            vecs = data.get("embeddings", [])
            return vecs[0] if vecs else None
    except Exception as e:
        return None


def _qdrant_search(collection: str, vector: list, limit: int) -> list:
    payload = json.dumps({
        "vector": vector,
        "limit": limit,
        "with_payload": True,
        "score_threshold": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{collection}/points/search",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("result", [])
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []  # collection doesn't exist yet
        return []
    except Exception:
        return []


def handle(inputs: dict) -> dict:
    query = str(inputs.get("query", "")).strip()
    if not query:
        return {"error": "query is required"}

    limit = max(1, min(int(inputs.get("limit", 5)), 10))

    vector = _embed(query)
    if not vector:
        return {"error": "Could not generate query embedding — is Ollama running with nomic-embed-text?"}

    results = []

    # Search Neural Archive (uploaded documents)
    for point in _qdrant_search("documents", vector, limit):
        payload = point.get("payload", {})
        text = payload.get("text", "").strip()
        if text:
            results.append({
                "source": payload.get("source", "archive"),
                "text": text,
                "score": round(point.get("score", 0), 3),
                "type": "document",
            })

    # Search Knowledge Base (Neural Context entries)
    for point in _qdrant_search("context_library", vector, limit):
        payload = point.get("payload", {})
        title = payload.get("title", "")
        content = payload.get("content", "").strip()
        if content:
            results.append({
                "source": title or "context",
                "text": f"[{title}] {content}" if title else content,
                "score": round(point.get("score", 0), 3),
                "type": "knowledge",
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:limit]

    if not results:
        return {
            "message": "No relevant content found in Neural Archive or Knowledge Base.",
            "query": query,
            "results": [],
        }

    return {"results": results, "total": len(results), "query": query}
