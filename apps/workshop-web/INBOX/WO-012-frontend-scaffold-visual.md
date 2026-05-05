# WO-012: Frontend Scaffold & Visual Identity
**To:** Frontend Agent
**Phase:** 1 (Walking Skeleton)
**PRD Reference:** §4 (Phase 1), §5.4
**Contract Reference:** Contract 2 (HTTP/SSE)

## Goal
Establish the Next.js 16 project structure and implement the "Rain" visual identity (Glassmorphism) to provide a premium-feel baseline for the Chat UI.

## Acceptance Criteria
- [ ] **Project Setup:**
    - Scaffold Next.js 16 application with Tailwind CSS 4.
    - Install and configure Zustand (state management) and TanStack Query (server state).
    - Implement strict TypeScript configuration for a type-safe development experience.
- [ ] **Visual Identity (The "Rain" Look):**
    - Create a global theme using the specified palette: Deep Blue, Slate, and glassmorphism effects.
    - Implement core UI components:
        - `<RainBackdrop>`: An immersive, fluid background.
        - `<GlassPanel>`: A reusable frosted-glass container with subtle borders and shadows.
    - Ensure the UI feels "fluid" and "premium" as per the visual identity spec.
- [ ] **API Integration Layer:**
    - Implement an API client (using `fetch` or `axios`) configured to point to `http://localhost:8000` (provided by `.env.local`).
    - Implement a `useHealth` hook using TanStack Query to poll `GET /v1/health`.
- [ ] **Health Indicator UI:**
    - Create a small, non-intrusive status badge in the corner of the screen (Green = OK, Red = Error) based on the health check response.
- [ ] **Documentation:**
    - Update `frontend/README.md` with a crystal-clear "Quick Start" guide for a non-programmer (Installation $\to$ Run).

## Out of Scope
- Chat window and message threads (Deferred to WO-013).
- WebSocket integration (Phase 3).
- Dynamic theme switching.

## Hand-back Format
- All files committed to `/frontend`.
- Updated `CHANGELOG.md` with the visual identity milestones.
- A screenshot or detailed description of the visual components implemented.
- Verified that the health badge correctly reflects the backend status.
