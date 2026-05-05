"""Create or overwrite a file in the Rain workspace."""

import os
import pathlib


def _get_workspace() -> pathlib.Path:
    raw = os.environ.get("RAIN_WORKSPACE_DIR", "").strip()
    if raw:
        ws = pathlib.Path(raw).expanduser().resolve()
    else:
        # Default: project-root/workspace
        ws = pathlib.Path(__file__).resolve().parents[3] / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def handle(inputs: dict) -> dict:
    rel_path = str(inputs.get("path", "")).strip().lstrip("/\\")
    content = inputs.get("content", "")
    encoding = inputs.get("encoding", "utf-8") or "utf-8"

    if not rel_path:
        return {"error": "path is required"}

    workspace = _get_workspace()

    # Normalize separators and guard against path traversal
    target = (workspace / pathlib.Path(rel_path.replace("\\", "/"))).resolve()
    if not str(target).startswith(str(workspace)):
        return {"error": f"Path escapes workspace: {rel_path}"}

    created = not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        target.write_text(content, encoding=encoding)
    except Exception as e:
        return {"error": f"Failed to write file: {e}"}

    return {
        "path": str(target),
        "relative_path": rel_path,
        "size_bytes": target.stat().st_size,
        "created": created,
        "workspace": str(workspace),
    }
