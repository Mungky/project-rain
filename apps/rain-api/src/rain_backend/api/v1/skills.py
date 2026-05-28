"""Skill listing and management endpoints."""

import pathlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from rain_backend.api.deps import get_db
from rain_brain.services.skill_service import SkillService
from db.schemas.dto_skill import SkillListResponse, Skill, InstallSkillRequest
from db.schemas.skill import Skill as SkillModel


router = APIRouter(tags=["skills"])


@router.get("", response_model=list[Skill])
async def list_skills(
    db: AsyncSession = Depends(get_db),
) -> list[Skill]:
    """List all installed skills."""
    service = SkillService(db)
    skills = await service.get_enabled_skills() # This gets from DB
    
    return [Skill.model_validate(s) for s in skills]


@router.post("", response_model=Skill, status_code=status.HTTP_201_CREATED)
@router.post("/install", response_model=Skill, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def install_skill(
    body: InstallSkillRequest,
    db: AsyncSession = Depends(get_db),
) -> Skill:
    """Install a new skill from a Git URL.

    Gated by ENABLE_SKILL_INSTALL env var: cloning + executing arbitrary
    Python from a remote repo is effectively RCE in the API container.
    Keep this disabled in prod until the runner is sandboxed.
    """
    from rain_backend.settings import settings as _s
    if not _s.enable_skill_install:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "skill_install_disabled",
                    "message": "Skill installation from remote git is disabled in this deployment."},
        )
    service = SkillService(db)
    try:
        skill = await service.install_skill(body.git_url)
        return Skill.model_validate(skill)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_skill", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": f"Failed to install skill: {str(e)}"},
        )


@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_skills(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-scan skills_registry/ and register any new skills to the database."""
    service = SkillService(db)
    registry_path = pathlib.Path(__file__).resolve().parents[5] / "skills_registry"
    await service.sync_registry(registry_path=str(registry_path))
    skills = await service.get_enabled_skills()
    return {"synced": True, "total": len(skills), "skills": [s.name for s in skills]}


class SkillToggleBody(BaseModel):
    enabled: bool


@router.patch("/{skill_name}", response_model=Skill)
async def toggle_skill(
    skill_name: str,
    body: SkillToggleBody,
    db: AsyncSession = Depends(get_db),
) -> Skill:
    """Enable or disable a skill by name."""
    result = await db.execute(select(SkillModel).where(SkillModel.name == skill_name))
    skill = result.scalar_one_or_none()
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "skill_not_found", "message": f"Skill '{skill_name}' not found"},
        )
    skill.enabled = body.enabled
    await db.commit()
    await db.refresh(skill)
    return Skill.model_validate(skill)


@router.delete("/{skill_name}", status_code=status.HTTP_204_NO_CONTENT)
async def uninstall_skill(
    skill_name: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Uninstall a skill by name."""
    service = SkillService(db)
    success = await service.uninstall_skill(skill_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "skill_not_found", "message": f"Skill {skill_name} not found"},
        )
