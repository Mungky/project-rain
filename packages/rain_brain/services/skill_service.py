"""Service layer for skill management and discovery."""

import json
import logging
import yaml
import pathlib
import shutil
import tempfile
import subprocess
import os
import stat
import traceback
from uuid import UUID
from typing import List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from db.schemas.skill import Skill as SkillModel

logger = logging.getLogger(__name__)


def remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree to handle read-only files on Windows.
    Changes file permission to writeable and retries the operation.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


class SkillService:
    """Service for managing and discovering skills."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    def _get_registry_path(self) -> pathlib.Path:
        """Helper to get the absolute path to skills_registry."""
        # Moving registry outside 'backend' to prevent Uvicorn reload triggers
        base_dir = pathlib.Path(__file__).resolve().parents[3]
        registry_path = base_dir / "skills_registry"
        if not registry_path.exists():
            registry_path.mkdir(parents=True, exist_ok=True)
        return registry_path

    async def get_enabled_skills(self) -> List[SkillModel]:
        """Fetch all enabled skills from the database."""
        query = select(SkillModel).where(SkillModel.enabled == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_skill_by_name(self, name: str) -> SkillModel | None:
        """Fetch a skill by its unique name."""
        query = select(SkillModel).where(SkillModel.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def get_tools_for_llm(self, skills: List[SkillModel]) -> List[Dict[str, Any]]:
        """Convert skill manifests into LLM-compatible tool definitions."""
        tools = []
        for skill in skills:
            manifest = skill.manifest_json or {}
            tool = {
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": manifest.get("description", f"Execute the {skill.name} skill."),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }

            inputs = manifest.get("inputs", {})
            for key, val in inputs.items():
                tool["function"]["parameters"]["properties"][key] = {
                    "type": val.get("type", "string"),
                    "description": val.get("description", ""),
                }
                if val.get("required", False):
                    tool["function"]["parameters"]["required"].append(key)

            tools.append(tool)
        return tools

    @staticmethod
    def _find_handler(skill_dir: pathlib.Path) -> pathlib.Path | None:
        """Locate the handler entry point for a skill directory.

        Checks (in order): handler.py, skill.py, main.py.
        Returns the path if found, None otherwise.
        """
        for candidate in ("handler.py", "skill.py", "main.py"):
            p = skill_dir / candidate
            if p.is_file():
                return p
        return None

    async def purge_invalid_skills(self, registry_path: str) -> None:
        """Remove DB entries for skills that have no handler in the registry."""
        path = pathlib.Path(registry_path)
        all_skills_result = await self.db.execute(select(SkillModel))
        for skill in all_skills_result.scalars().all():
            skill_dir = path / skill.name
            if not skill_dir.is_dir() or not self._find_handler(skill_dir):
                logger.info("Purging invalid skill from DB: %s (no handler found)", skill.name)
                await self.db.execute(delete(SkillModel).where(SkillModel.name == skill.name))
        await self.db.commit()

    async def sync_registry(self, registry_path: str = "./skills_registry"):
        """Sync the local skills registry folder with the database."""
        path = pathlib.Path(registry_path)
        if not path.exists():
            logger.warning(f"Skills registry path {registry_path} does not exist.")
            return

        for skill_dir in path.iterdir():
            if not skill_dir.is_dir():
                continue

            manifest_path = skill_dir / "manifest.yaml"
            handler_path = self._find_handler(skill_dir)

            # Require at least a manifest OR a handler to register a skill
            if not manifest_path.is_file() and not handler_path:
                continue

            # Try loading manifest; auto-generate if missing but handler exists
            manifest: dict = {}
            if manifest_path.is_file():
                try:
                    with open(manifest_path, "r") as f:
                        manifest = yaml.safe_load(f) or {}
                except Exception as e:
                    logger.error("Failed to parse manifest for %s: %s", skill_dir.name, e)
                    continue

            if handler_path and not manifest.get("name"):
                # Auto-derive name from directory if manifest missing or incomplete
                manifest["name"] = skill_dir.name

            if handler_path and not manifest.get("version"):
                manifest["version"] = "0.0.1"

            name = manifest.get("name")
            version = manifest.get("version")

            if not name:
                logger.debug("Skipping %s — no name in manifest or directory", skill_dir.name)
                continue

            # Store the handler filename so executor can find it
            if handler_path:
                manifest["_handler"] = handler_path.name

            try:
                # Check if exists
                existing = await self.get_skill_by_name(name)
                if not existing:
                    logger.info(f"Registering new skill: {name} v{version}")
                    new_skill = SkillModel(
                        name=name,
                        version=version or "0.0.1",
                        manifest_json=manifest,
                        enabled=True
                    )
                    self.db.add(new_skill)
                else:
                    # Update manifest if version changed
                    if existing.version != version:
                        logger.info(f"Updating skill {name} to v{version}")
                        existing.version = version
                        existing.manifest_json = manifest

                await self.db.commit()
            except Exception as e:
                logger.error(f"Failed to sync skill {skill_dir.name}: {e}")
                await self.db.rollback()

    async def install_skill(self, git_url: str) -> SkillModel:
        """Install a skill from a Git repository."""
        try:
            registry_path = self._get_registry_path()
            logger.info(f"Received installation request for: {git_url}")
            
            # Robust Sanitization & Flag Extraction
            import re
            
            # 1. Try to extract name from --skill flag
            skill_name_match = re.search(r'--skill\s+([^\s]+)', git_url)
            requested_name = skill_name_match.group(1) if skill_name_match else None
            
            # 2. Extract ONLY the URL
            url_match = re.search(r'https?://[^\s\?#]+', git_url)
            if url_match:
                # Clean up the URL for git
                actual_git_url = url_match.group(0).rstrip('/')
                logger.info(f"Sanitized URL to: {actual_git_url}")
            else:
                logger.error(f"Could not find a valid URL in input: {git_url}")
                raise ValueError(f"Invalid URL provided: {git_url}")

            # Note: We use onexc instead of onerror for Python 3.12+
            rmtree_kwargs = {"onexc": remove_readonly} if hasattr(shutil.rmtree, "__code__") and "onexc" in shutil.rmtree.__code__.co_varnames else {"onerror": remove_readonly}

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = pathlib.Path(tmp_dir)
                
                # 1. Clone
                try:
                    logger.info(f"Executing: git clone --depth 1 {actual_git_url}")
                    subprocess.run(
                        ["git", "clone", "--depth", "1", actual_git_url, "cloned_skill"],
                        cwd=tmp_dir,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    logger.info("Clone successful")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Git clone failed: {e.stderr}")
                    raise ValueError(f"Failed to clone repository: {e.stderr}")

                cloned_path = tmp_path / "cloned_skill"
                
                # Remove .git folder
                git_folder = cloned_path / ".git"
                if git_folder.exists():
                    shutil.rmtree(git_folder, **rmtree_kwargs)

                manifest_path = cloned_path / "manifest.yaml"
                
                # 2. Validate & Auto-Generate if missing
                if not manifest_path.exists():
                    logger.warning(f"manifest.yaml not found. Auto-generating...")
                    
                    # Name Priority: 1. --skill flag, 2. repo name from URL
                    final_skill_name = requested_name if requested_name else actual_git_url.split("/")[-1].replace(".git", "")
                    
                    description = f"Generic skill imported from {actual_git_url}"
                    readme_path = cloned_path / "README.md"
                    if readme_path.exists():
                        try:
                            with open(readme_path, "r", encoding="utf-8") as f:
                                first_line = f.readline().strip().lstrip("#").strip()
                                if first_line: description = first_line
                        except Exception: pass
                    
                    manifest = {
                        "name": final_skill_name,
                        "version": "0.0.1-autogen",
                        "description": description,
                        "inputs": {"query": {"type": "string", "description": "Input", "required": True}}
                    }
                    with open(manifest_path, "w", encoding="utf-8") as f:
                        yaml.dump(manifest, f)
                    logger.info(f"Auto-generated manifest for {final_skill_name}")
                
                with open(manifest_path, "r") as f:
                    manifest = yaml.safe_load(f)
                
                # If we have a requested name from --skill, override the manifest name to match the directory preference
                if requested_name:
                    manifest["name"] = requested_name
                    # Save it back to manifest.yaml so registry sync uses the correct name
                    with open(manifest_path, "w", encoding="utf-8") as f:
                        yaml.dump(manifest, f)
                
                name = manifest.get("name")
                
                # 3. Move to registry (Atomic-ish)
                dest_path = registry_path / name
                
                # If destination exists, we move it to a backup first instead of immediate delete
                # to prevent data loss if the process is killed during copy
                if dest_path.exists():
                    logger.info(f"Backing up existing skill folder for {name}")
                    backup_path = registry_path / f"{name}.bak"
                    if backup_path.exists():
                        shutil.rmtree(backup_path, **rmtree_kwargs)
                    os.rename(dest_path, backup_path)
                
                try:
                    shutil.copytree(cloned_path, dest_path)
                    logger.info(f"Successfully copied {name} to registry")
                    # Remove backup if copy succeeded
                    backup_path = registry_path / f"{name}.bak"
                    if backup_path.exists():
                        shutil.rmtree(backup_path, **rmtree_kwargs)
                except Exception as e:
                    logger.error(f"Copy failed, restoring backup: {e}")
                    backup_path = registry_path / f"{name}.bak"
                    if backup_path.exists():
                        if dest_path.exists(): shutil.rmtree(dest_path, **rmtree_kwargs)
                        os.rename(backup_path, dest_path)
                    raise
                
                # 4. Sync
                await self.sync_registry(str(registry_path))
                
                # 5. Return the new skill
                skill = await self.get_skill_by_name(name)
                if not skill:
                    raise RuntimeError(f"Skill {name} was not registered after installation")
                
                # Manual attribute setting to avoid lazy-load issues after commit
                setattr(skill, 'description', manifest.get("description"))
                
                return skill

        except Exception as e:
            logger.error(f"CRITICAL ERROR in install_skill: {str(e)}\n{traceback.format_exc()}")
            raise

    async def uninstall_skill(self, skill_name: str) -> bool:
        """Uninstall a skill by name."""
        registry_path = self._get_registry_path()
        dest_path = registry_path / skill_name
        
        # Determine rmtree handler
        rmtree_kwargs = {"onexc": remove_readonly} if hasattr(shutil.rmtree, "__code__") and "onexc" in shutil.rmtree.__code__.co_varnames else {"onerror": remove_readonly}

        # 1. Delete from registry
        if dest_path.exists():
            shutil.rmtree(dest_path, **rmtree_kwargs)
        else:
            logger.warning(f"Skill folder {skill_name} not found in registry")
        
        # 2. Delete from DB
        try:
            query = delete(SkillModel).where(SkillModel.name == skill_name)
            await self.db.execute(query)
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete skill {skill_name} from database: {e}")
            await self.db.rollback()
            return False
