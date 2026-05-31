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
        # SearXNG's bot-detection/limiter fails closed when it can't resolve a
        # client IP ("X-Forwarded-For nor X-Real-IP header is set!") and rejects
        # the request with 403. Since this is a trusted internal call from
        # rain-api, supply those headers plus a browser-like User-Agent so the
        # JSON API is reachable regardless of the limiter config.
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "X-Forwarded-For": "127.0.0.1",
                "X-Real-IP": "127.0.0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode(errors="replace")[:200]
        except Exception:
            pass
        return {"error": f"SearXNG HTTP {e.code} ({e.reason}). {body}".strip()}
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
