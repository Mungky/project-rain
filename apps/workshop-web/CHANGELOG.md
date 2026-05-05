# Changelog

## [Unreleased] - 2026-04-23

### Added
- **Functional Skill Store**:
  - Replaced placeholders with real data from `GET /v1/skills`.
  - Added "Git URL" installation capability with real-time status feedback.
  - Implemented skill uninstallation (Discard) linked to backend API.
- **Neural Archive Management**:
  - Integrated Knowledge Base management directly into System Settings.
  - Support for local file injection (PDF, MD, TXT) with status tracking.
  - List view of all indexed fragments with removal capability.
- **Persistent API Credentials**:
  - Synchronized Cloud Gateway fields with `user_preferences` API.
  - Secure "Authorize Sync" flow for Anthropic and OpenAI keys.
- **Skill Control Center**: Integrated into the right Info Panel.
  - Master **AUTO** toggle to let AI manage skill selection.
  - Searchable list of installed skills with individual activation toggles.
  - Visual sync with backend state via `PATCH /v1/conversations`.
- **Neural Context Visualization**: Real-time display of RAG retrieval fragments in the Info Panel, captured directly from the SSE stream.
- **Neural Baseline (Custom Prompt)**: Added a reference section to override system prompts per-conversation, with auto-sync on blur.
- **Markdown & Math Mastery**:
  - Full support for **LaTeX formulas** using KaTeX.
  - Advanced syntax highlighting for code blocks with "copy" functionality.
  - Enhanced styling for tables, images, and long-form markdown content.
- **Dynamic Layout Refinement**:
  - Chatbox now scales and shifts vertically based on session activity.
  - Info Panel features a "vertical strip" mode when collapsed to prevent chat overlap.
  - Sidebar and Dashboard transitions for a smoother user experience.

### Fixed
- Fixed text color contrast issues in user message bubbles (White-on-White bug).
- Resolved focus ring artifacts in the chatbox textarea.
- Optimized "Wet Window" background performance for smoother 30-45 FPS animation.
- Restored model selection persistence between the UI and Database.