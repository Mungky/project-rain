"""Surgical string replacement in workspace files."""

import os
import pathlib


def _get_workspace() -> pathlib.Path:
    raw = os.environ.get("RAIN_WORKSPACE_DIR", "").strip()
    if raw:
        ws = pathlib.Path(raw).expanduser().resolve()
    else:
        ws = pathlib.Path(__file__).resolve().parents[3] / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def handle(inputs: dict) -> dict:
    rel_path = str(inputs.get("path", "")).strip().lstrip("/\\")
    old_str = inputs.get("old_str", "")
    new_str = inputs.get("new_str", "")

    if not rel_path:
        return {"error": "path is required"}
    if old_str == "":
        return {"error": "old_str cannot be empty — use create_file to write new content"}

    workspace = _get_workspace()
    target = (workspace / pathlib.Path(rel_path.replace("\\", "/"))).resolve()

    if not str(target).startswith(str(workspace)):
        return {"error": f"Path escapes workspace: {rel_path}"}

    if not target.exists():
        return {"error": f"File not found: {rel_path}"}

    try:
        original = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}

    if old_str not in original:
        # Give context: show first 500 chars so Storm can adjust
        return {
            "error": "old_str not found in file — check exact whitespace and indentation",
            "file_preview": original[:500],
            "success": False,
        }

    # Replace first occurrence only (like most editors)
    updated = original.replace(old_str, new_str, 1)

    try:
        target.write_text(updated, encoding="utf-8")
    except Exception as e:
        return {"error": f"Failed to write file: {e}"}

    return {
        "success": True,
        "replacements": 1,
        "path": str(target),
        "relative_path": rel_path,
    }
