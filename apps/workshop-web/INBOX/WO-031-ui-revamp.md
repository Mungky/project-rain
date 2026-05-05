# WO-031: UI/UX Mega Revamp (Rain Noir Edition)
**To:** Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** blocker
**Phase:** 2 (Design Sprint)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `frontend/SYSTEM_PROMPT.md` and `frontend/INSTRUCTIONS.md`.
2.  Install all skills in `frontend/skills/`.

## Goal
Completely overhaul the Rain UI/UX to a minimalist Black & White 3-panel layout with realistic rain effects and integrated management tools.

## Acceptance Criteria
- [ ] **New Layout (3-Column System)**:
    - Update `app/chat/layout.tsx` to support three columns:
        1.  **Sidebar (Left)**: Collapsible, minimal chat list.
        2.  **Main Chat (Center)**: Focused, clean message thread.
        3.  **Info Panel (Right)**: New collapsible panel containing:
            - **Usage**: Token counts (in/out) and model info.
            - **RAG Context**: Live display of snippets retrieved from Qdrant.
            - **Quick Files**: List of files in the current Knowledge Base.
- [ ] **Minimalist B&W Theme**:
    - Colors: True black (#000), white (#FFF), and subtle grays for borders.
    - Typography: Use a sharp, modern sans-serif (e.g., Inter or Geist).
    - Components: Update all `GlassPanel` and `Button` components to follow the B&W minimalist aesthetic (high contrast, clean borders).
- [ ] **Realistic Rain Background**:
    - Rewrite `components/identity/rain-backdrop.tsx`. 
    - Use a more realistic rain effect (e.g., subtle falling particles with vary speed/opacity, or a high-quality overlay).
- [ ] **Logo Integration**:
    - Use the logo from `../../002-Rephot/rephot-web/public/RePhot.svg` in the sidebar and loading states.
- [ ] **Unified Settings Interface**:
    - Build a "Settings" view/modal that consolidates:
        - **API Keys**: Form to save keys for Anthropic, OpenAI, etc.
        - **Skill Management**: UI to trigger `skills.sh` commands (list/install).
        - **Knowledge Base**: Integrated file upload and management (from WO-026).
- [ ] **Interactivity**:
    - Add smooth transitions using `framer-motion` between chat sessions and panel toggles.

## Hand-back
Standard completion report (`.completed.md`) and a screenshot of the new UI if possible (via description).
