"""Read a file from the Rain workspace."""

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
    max_chars = int(inputs.get("max_chars", 20000))

    if not rel_path:
        return {"error": "path is required"}

    workspace = _get_workspace()
    target = (workspace / pathlib.Path(rel_path.replace("\\", "/"))).resolve()

    if not str(target).startswith(str(workspace)):
        return {"error": f"Path escapes workspace: {rel_path}"}

    if not target.exists():
        # List workspace to help Storm know what files exist
        try:
            files = [
                str(p.relative_to(workspace))
                for p in workspace.rglob("*")
                if p.is_file()
            ][:30]
        except Exception:
            files = []
        return {
            "error": f"File not found: {rel_path}",
            "workspace_files": files,
        }

    if not target.is_file():
        return {"error": f"Path is not a file: {rel_path}"}

    size = target.stat().st_size
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}

    truncated = len(content) > max_chars
    return {
        "content": content[:max_chars],
        "path": str(target),
        "relative_path": rel_path,
        "size_bytes": size,
        "truncated": truncated,
    }
