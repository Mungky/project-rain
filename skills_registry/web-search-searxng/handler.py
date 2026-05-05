"""Web search via SearXNG — aggregates Google, Bing, DDG, Wikipedia."""

import urllib.request
import urllib.parse
import urllib.error
import json
import os


SEARXNG_BASE_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")


def handle(inputs: dict) -> dict:
    query = str(inputs.get("query", "")).strip()
    if not query:
        return {"error": "query is required"}

    max_results = min(int(inputs.get("max_results", 8)), 15)

    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "categories": "general",
        "language": "auto",
    })
    url = f"{SEARXNG_BASE_URL}/search?{params}"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Rain/1.0 (AI Assistant)"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": f"SearXNG unreachable: {e.reason}. Is rain-searxng container running?"}
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

    raw_results = data.get("results", [])
    results = []
    seen_urls = set()

    for r in raw_results:
        url_val = r.get("url", "")
        if url_val in seen_urls:
            continue
        seen_urls.add(url_val)

        results.append({
            "title": r.get("title", ""),
            "url": url_val,
            "snippet": r.get("content", ""),
            "source": r.get("engine", ""),
        })

        if len(results) >= max_results:
            break

    if not results:
        return {"error": "No results found", "query": query}

    return {"results": results, "total": len(results), "query": query}
