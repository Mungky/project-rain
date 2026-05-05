"""Skill execution runtime."""

import asyncio
import importlib.util
import inspect
import logging
import pathlib
import sys
from typing import Any, Dict

logger = logging.getLogger(__name__)


SKILL_TIMEOUT_SECONDS = 60


class SkillExecutor:
    """Runtime for executing skill handlers."""

    def __init__(self, registry_path: str | None = None):
        if registry_path:
            self.registry_path = pathlib.Path(registry_path).resolve()
        else:
            base_dir = pathlib.Path(__file__).resolve().parents[3]
            self.registry_path = (base_dir / "skills_registry").resolve()

        if not self.registry_path.exists():
            self.registry_path.mkdir(parents=True, exist_ok=True)

    async def execute(self, skill_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a skill handler by name with a hard timeout."""
        # Path traversal guard
        skill_dir = (self.registry_path / skill_name).resolve()
        if not str(skill_dir).startswith(str(self.registry_path)):
            return {"error": f"Invalid skill name: {skill_name}"}

        if not skill_dir.exists():
            return {"error": f"Skill '{skill_name}' not found in registry"}

        # Try manifest-declared entry point first, then fall back to conventional names
        handler_path = self._resolve_handler(skill_dir)
        if handler_path is None:
            return {"error": f"Skill '{skill_name}' has no handler — it may not be a Rain skill"}

        try:
            async with asyncio.timeout(SKILL_TIMEOUT_SECONDS):
                return await self._run_handler(skill_name, skill_dir, handler_path, inputs)
        except TimeoutError:
            logger.error("Skill %s timed out after %ds", skill_name, SKILL_TIMEOUT_SECONDS)
            return {"error": f"Skill '{skill_name}' timed out after {SKILL_TIMEOUT_SECONDS}s"}
        except Exception as e:
            logger.exception("Error executing skill %s", skill_name)
            return {"error": f"Execution failed: {str(e)}"}

    def _resolve_handler(self, skill_dir: pathlib.Path) -> pathlib.Path | None:
        """Find the handler entry point for a skill.

        Checks manifest `_handler` field first, then conventional names.
        """
        # Check for manifest-declared handler
        manifest_path = skill_dir / "manifest.yaml"
        if manifest_path.is_file():
            try:
                import yaml
                with open(manifest_path, "r") as f:
                    manifest = yaml.safe_load(f) or {}
                declared = manifest.get("_handler") or manifest.get("entry", "")
                # Support formats like "handler.py:handle" or just "handler.py"
                filename = declared.split(":")[0].strip() if declared else ""
                if filename:
                    candidate = skill_dir / filename
                    if candidate.is_file():
                        return candidate
            except Exception:
                pass

        # Conventional handler filenames
        for candidate in ("handler.py", "skill.py", "main.py"):
            p = skill_dir / candidate
            if p.is_file():
                return p

        return None

    async def _run_handler(
        self,
        skill_name: str,
        skill_dir: pathlib.Path,
        handler_path: pathlib.Path,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        spec = importlib.util.spec_from_file_location(f"skill_{skill_name}", str(handler_path))
        if spec is None or spec.loader is None:
            return {"error": f"Could not load spec for {skill_name}"}

        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(skill_dir))
        try:
            spec.loader.exec_module(module)
        finally:
            if str(skill_dir) in sys.path:
                sys.path.remove(str(skill_dir))

        if not hasattr(module, "handle"):
            return {"error": f"Skill '{skill_name}' missing 'handle' function"}

        if inspect.iscoroutinefunction(module.handle):
            return await module.handle(inputs)
        else:
            return await asyncio.to_thread(module.handle, inputs)
