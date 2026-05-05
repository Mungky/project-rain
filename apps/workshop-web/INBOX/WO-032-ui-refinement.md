# WO-032: UI/UX Refinement - The "Mist & Noir" Update
**To:** Frontend Agent
**From:** Parent Agent
**Date:** 2026-04-23
**Priority:** high
**Phase:** 2 (Design Sprint Revision)

## ⚠️ SETUP INSTRUCTIONS (MANDATORY)
1.  Read `frontend/SYSTEM_PROMPT.md`.
2.  Install skills in `frontend/skills/`.

## Goal
Refine the layout and atmosphere of Rain to match the user's "Mist & Noir" vision, focusing on a dynamic chat interface and immersive background.

## Acceptance Criteria
- [ ] **Atmospheric Background**:
    - Overhaul `components/identity/rain-backdrop.tsx`.
    - Atmosphere: "Dark sky, seen through a misty/foggy window."
    - Visuals: Use a deep, dark gradient for the sky. Add a layer of "dew/mist" blur (CSS `backdrop-filter: blur()`).
    - Rain: Ensure falling rain particles look sharp against the dark background but slightly muted by the "window mist."
- [ ] **Dynamic Chat Layout (Start vs Active)**:
    - **Empty State (0 messages)**:
        - Center the `Composer` vertically and horizontally in the chat area.
        - Add an "Attachment" icon button and a "Tools" icon button inside/near the chat box.
        - **Model Selection**: Move the `ModelSelector` (agent picker) to be a subtle icon/button *inside* the centered chat box.
    - **Active State (> 0 messages)**:
        - Move the `Composer` to the bottom (standard fixed position).
        - **Lock Mode**: Hide the "Model Selector", "Tools", and "Attachment" buttons once the conversation has started. The session is locked to the initial choices.
- [ ] **Info Panel (Right)**:
    - Change interaction from "Close" to "Hide/Show".
    - Add a toggle button (e.g., a chevron or "Info" icon) to collapse/expand the panel without unmounting it.
- [ ] **Minimalist Model Selector**:
    - Update `components/chat/model-selector.tsx`.
    - Display ONLY the provider/agent logo (minimalist).
    - Show model details/names ONLY on hover.
- [ ] **Assets**:
    - Use the logo provided at `frontend/public/rain-logo.svg` for all branding.
- [ ] Update `CHANGELOG.md`.

## Hand-back
Standard.
