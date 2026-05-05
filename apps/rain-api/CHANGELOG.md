# Changelog

## [Unreleased]

### Added
- Dynamic Skill Filtering and Context Awareness (WO-040):
    - Added PATCH endpoint for conversations to update skill settings (`auto_skills`, `enabled_skills`).
    - Implemented UserPreference injection (custom system prompts and user context) into chat orchestrator.
    - Added dynamic skill filtering in chat orchestrator based on conversation settings.
    - Added `GET /v1/skills` endpoint to list installed skills.
- Skill Installation and Uninstallation API (WO-042):
    - Added `POST /v1/skills/install` to install skills via Git URL.
    - Added `DELETE /v1/skills/{skill_name}` to uninstall skills.
    - Implemented folder-based registry management with DB synchronization.
- RAG retrieval in chat orchestrator.
- Support for citations in SSE `done` chunk.
- Filtering by `user_id` in Qdrant queries.
- New RAG system prompt template.
- Feedback API endpoint `PUT /v1/messages/{message_id}/feedback`.
- Reasoning extraction in chat orchestrator (detects `<think>` tags).
- Real-time streaming of reasoning content via `reasoning` SSE chunks.
- `reasoning_content` and `feedback` fields in `Message` schema and DB persistence.

### Fixed
- Missing `await` on Ollama `embed()` call in `chat_mode.py`.
- Corrected Qdrant `query_points` parameter name to `collection_name`.
- Test client fixture in `tests/test_messages_endpoints.py` now correctly triggers app lifespan.
