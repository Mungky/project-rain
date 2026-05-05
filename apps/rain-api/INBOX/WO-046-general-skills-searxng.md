# WO-046: General-Purpose Skills + SearXNG Integration
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-24
**Priority:** high
**Phase:** 2

## Goal
Install three general-purpose skills that make the local AI feel comparable to a frontier model.
Replace DuckDuckGo with SearXNG (self-hosted, aggregates Google+Bing+DDG+Wikipedia).

## Services Added (Parent-owned)
- SearXNG added to `docker-compose.yml` on port 8080
- Config at `searxng/settings.yml` (JSON format enabled, limiters off)

## Skills to Create in skills_registry/

### 1. web-search-searxng
- Replaces web-search-duckduckgo
- Calls SearXNG HTTP API at http://localhost:8080/search?format=json
- Inputs: query (string), max_results (int, default 8)
- Returns: [{title, url, snippet, source}]

### 2. web-reader
- Fetches full text content from a URL
- Stdlib only: urllib + html.parser
- Strips scripts, styles, nav, footer tags
- Truncates at 6000 chars
- Inputs: url (string)
- Returns: {url, title, content, char_count}
- Use case: deep research, scraping, summarization

### 3. python-executor
- Runs arbitrary Python code in a subprocess with timeout
- Inputs: code (string), timeout (int, default 10, max 30)
- Returns: {stdout, stderr, returncode}
- Security: subprocess isolation, no network access restriction (local env)

## Note on web-search-duckduckgo
Folder missing from registry, still in DB. Skills UI should show it as broken.
New conversations should use web-search-searxng instead.
