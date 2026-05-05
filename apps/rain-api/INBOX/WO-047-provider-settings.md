# WO-047: Provider Settings — Toggle, API Keys, Model Filtering
**To:** Backend Agent + Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-24
**Priority:** high

## Problem
1. GET /v1/user/preferences does not exist → frontend 404s silently
2. Provider configs (enable/disable, API keys) have no persistence layer
3. GET /v1/models uses only startup env-var providers, ignores DB settings
4. Settings UI only shows Anthropic + OpenAI, missing Google + Ollama

## Architecture
Store all provider configs in user_preferences.api_keys JSONB (already exists).
Structure:
{
  "anthropic": {"enabled": false, "key": "sk-ant-..."},
  "openai":    {"enabled": false, "key": "sk-..."},
  "google":    {"enabled": false, "key": "AIza..."},
  "ollama":    {"enabled": true,  "base_url": "http://localhost:11434"}
}

## Backend Deliverables
- NEW api/v1/user.py: GET + PATCH /v1/user/preferences
- UPDATE api/v1/models.py: instantiate providers from DB config at request time
- Register user router in main.py and __init__.py

## Frontend Deliverables
- UPDATE settings-modal.tsx: replace flat key inputs with provider cards
- Each card: logo icon, name, toggle (enabled/disabled), key input, connection status
- UPDATE api-types.ts: new UserPreferencesResponse shape

## Constraints
- Return full API key in GET (local personal app, no external exposure)
- Ollama: no key field, only base_url + enabled toggle
- Model list must only return models from enabled providers
