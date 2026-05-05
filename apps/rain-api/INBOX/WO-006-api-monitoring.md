# WO-006: API Documentation & System Monitoring
**To:** Backend Agent
**Phase:** 1 (Interlude)
**PRD Reference:** §4 (Phase 1), §5.2
**Contract Reference:** Contract 2 (HTTP/OpenAPI)

## Goal
Ensure the user can visually verify and test the backend API via Swagger UI and monitor system resources using Docker tools.

## Acceptance Criteria
- [ ] **Swagger UI Optimization:** 
    - Ensure `GET /docs` is active and fully functional.
    - Add clear, human-readable descriptions to all endpoints, request bodies, and response models in the code so that the Swagger UI is intuitive for a non-programmer.
    - Verify that the "Try it out" button works for all Phase 1 endpoints (Health, Conversations CRUD).
- [ ] **Resource Monitoring Guide:**
    - Create a brief guide in `backend/README.md` explicitly showing the user how to use the Docker Desktop Dashboard to monitor CPU and RAM usage for the `rain-backend`, `rain-db`, and `rain-redis` containers.
    - Include a "What to look for" section (e.g., "If RAM exceeds 1.5GB for Postgres, we have a problem").
- [ ] **API Accessibility:** 
    - Confirm that the backend is configured to allow requests from the user's local network/browser for testing.

## Out of Scope
- Building a custom admin dashboard (use Swagger/Docker for now).
- Implementing advanced Prometheus/Grafana monitoring (Phase 1 limitation).

## Hand-back Format
- Updated code for documentation and `backend/README.md`.
- Updated `CHANGELOG.md` with a detailed entry.
- A "Quick-Link" list provided in the hand-back message (e.g., `http://localhost:8000/docs`).
