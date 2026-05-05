# WO-027: Implement Hosted Provider Adapters
**To:** Backend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2
**PRD Reference:** §4 Phase 2, Milestone 2.6
**Contracts Touched:** Contract 7 (Provider Adapter Interface), Contract 2 (GET /v1/models)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
Before starting this Work Order, you MUST:
1.  Read your `backend/SYSTEM_PROMPT.md`.
2.  Read your `backend/INSTRUCTIONS.md`.
3.  Install all skills in `backend/skills/` (especially `provider-adapter-builder`).

## Goal
Implement adapter classes for Anthropic, OpenAI, and Google Gemini to allow Rain to use hosted LLM models.

## Context
Phase 1 used local Ollama exclusively. Phase 2 opens up the system to frontier models via their respective APIs. All adapters must conform to the `Provider` protocol in `providers/base.py`.

## Acceptance Criteria
- [ ] **Adapters**:
    - Implement `AnthropicProvider` in `backend/src/rain_backend/providers/anthropic.py` (using `anthropic` sdk).
    - Implement `OpenAIProvider` in `backend/src/rain_backend/providers/openai.py` (using `openai` sdk).
    - Implement `GoogleProvider` in `backend/src/rain_backend/providers/google.py` (using `google-generativeai` sdk).
- [ ] **Unified Interface**:
    - Each `chat()` method must handle streaming and yield `ChatChunk` objects (`token`, `reasoning`, `done`, `error`).
    - Note: For reasoning, map the provider's native fields (e.g., Anthropic's reasoning blocks if available, or just standard tokens) to our `reasoning` chunk type if applicable.
- [ ] **Model Listing**:
    - Add a new endpoint `GET /v1/models` in `api/v1/health.py` (or a new `models.py`) that returns a union of all available models from all ENABLED providers.
- [ ] **Initialization**:
    - Update `build_providers()` in `providers/__init__.py` to instantiate these providers only if their respective API keys are present in `settings`.
- [ ] **Dependencies**:
    - Add `anthropic`, `openai`, and `google-generativeai` to `pyproject.toml` and run `uv sync`.
- [ ] **Error Handling**: Gracefully handle invalid API keys or rate limits by yielding an `error` chunk.
- [ ] Unit tests for each new provider using mocks to avoid actual API calls.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard completion report (`.completed.md`).
