# WO-026: Implement Document Management UI
**To:** Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2
**PRD Reference:** §4 Phase 2, Milestone 2.9
**Contracts Touched:** Contract 2 (Backend ↔ Frontend HTTP)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
Before starting this Work Order, you MUST:
1.  Read your `frontend/SYSTEM_PROMPT.md` to assume your identity as the Frontend Agent.
2.  Read your `frontend/INSTRUCTIONS.md` for your specific operational procedures.
3.  Install all skills in `frontend/skills/` (e.g., `rain-visual-identity`, `state-discipline`, etc.).

## Goal
Build the user interface for managing uploaded documents, allowing users to view, upload, and delete files used for RAG.

## Context
The Backend API for documents is now fully functional (list, upload, delete). We need a polished UI that fits the Rain aesthetic to let users manage their knowledge base.

## Acceptance Criteria
- [ ] **Document Management View**:
    - Create a new view for documents. This can be a dedicated page (e.g., `/chat/documents`) or a modal accessible from the sidebar.
    - It should display a list of uploaded documents in a clean table or grid.
- [ ] **Hooks**:
    - Create `use-documents.ts` hook to wrap the `GET`, `POST`, and `DELETE` document APIs using TanStack Query.
- [ ] **Features**:
    - **List**: Show filename, size (optional), created date, and current status (`processing`, `ready`, `error`).
    - **Upload**: Add a "Upload Document" button that opens a file picker. Show a progress/loading state while the backend is processing (chunking/embedding).
    - **Delete**: Add a delete icon/button for each document. Confirm before deleting.
- [ ] **Real-time Status**:
    - If a document is in `processing` state, it should ideally refresh or show a spinner until it turns `ready`.
- [ ] **Visual Identity**:
    - Use `<GlassPanel>` and the deep blue/slate theme.
    - Ensure empty states are handled gracefully ("No documents uploaded yet").
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard completion report (`.completed.md`).
