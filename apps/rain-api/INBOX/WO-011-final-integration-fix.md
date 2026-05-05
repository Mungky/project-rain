# WO-011: FINAL INTEGRATION FIX - Python Path & Runtime Stability
**To:** Backend Agent
**Phase:** 1 (Critical Fix)
**PRD Reference:** §5.2, §7.2
**Contract Reference:** Contract 3

## Goal
Permanently resolve `ModuleNotFoundError: No module named 'db'` and ensure the server starts successfully on Python 3.14.

## Acceptance Criteria
- [ ] **Bulletproof Root Path Injection:**
    - Modify `main.py` to inject the project root directory into `sys.path` using an absolute path calculation that works regardless of the working directory.
    - Ensure this injection happens BEFORE any `from rain_backend...` or `from db...` imports.
- [ ] **Python 3.14 Compatibility check:**
    - Verify that all dependencies in `pyproject.toml` are compatible with Python 3.14.
    - If any library is causing the `importlib` or `multiprocessing` failures seen in the user's logs, update the version or provide a polyfill.
- [ ] **Execution Proof:**
    - You MUST provide the exact command to run the server that is guaranteed to work (e.g., including `PYTHONPATH` or a specific `uv` flag).
    - Provide a log snippet showing:
        1. `INFO: Database connection handshake successful`
        2. `INFO: Uvicorn running on http://127.0.0.1:8000`
- [ ] **Dependency Check:**
    - Verify that `db/__init__.py` exists and is correctly placed.

## Hand-back Format
- Updated `main.py` and `pyproject.toml`.
- The "Guaranteed Command" for the user to launch the server.
- Full log output proof from a successful local run.
- Updated `CHANGELOG.md`.

## Warning
The user is seeing the same `ModuleNotFoundError` despite your previous claims of success. This is a failure of verification. Do not return this WO until you have actually run the server and seen the "handshake successful" log.
