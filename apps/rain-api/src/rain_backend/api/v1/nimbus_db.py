"""Nimbus client/project database — CRUD + filename matching."""

import re
import logging
from datetime import datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from rain_backend.api.deps import get_current_user, get_db, require_admin
from db.schemas import NimbusClient, NimbusProject, User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["nimbus-db"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ClientOut(BaseModel):
    code: str
    name: str
    aliases: List[str]
    active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class ClientCreate(BaseModel):
    code: str
    name: str
    aliases: List[str] = []


class ClientUpdate(BaseModel):
    name: str | None = None
    aliases: List[str] | None = None
    active: bool | None = None


class ProjectOut(BaseModel):
    id: str
    client_code: str
    code: str
    name: str
    default_folder_category: str
    active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    client_code: str
    code: str
    name: str
    default_folder_category: str = "MISC"


class ProjectUpdate(BaseModel):
    name: str | None = None
    default_folder_category: str | None = None
    active: bool | None = None


class MatchResult(BaseModel):
    client_code: str | None
    client_name: str | None
    project_code: str | None
    project_name: str | None
    default_folder_category: str
    confidence: float  # 0.0 – 1.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """Uppercase tokens split on non-alphanumeric chars, length >= 2."""
    return {t for t in re.split(r"[^A-Za-z0-9]+", text.upper()) if len(t) >= 2}


def _match_score(filename_tokens: set[str], terms: list[str]) -> float:
    """Return fraction of terms found in filename tokens."""
    if not terms:
        return 0.0
    hits = sum(1 for t in terms if t.upper() in filename_tokens)
    return hits / len(terms)


def _best_match(
    filename: str,
    clients: list[NimbusClient],
    projects: list[NimbusProject],
) -> MatchResult:
    tokens = _tokenize(filename)

    best_client: NimbusClient | None = None
    best_client_score = 0.0

    for c in clients:
        if not c.active:
            continue
        terms = [c.code] + (c.aliases or []) + c.name.split()
        score = _match_score(tokens, terms)
        if score > best_client_score:
            best_client_score = score
            best_client = c

    if best_client is None or best_client_score == 0:
        return MatchResult(
            client_code=None, client_name=None,
            project_code=None, project_name=None,
            default_folder_category="MISC", confidence=0.0,
        )

    # Find best project for matched client
    client_projects = [p for p in projects if p.client_code == best_client.code and p.active]
    best_project: NimbusProject | None = None
    best_project_score = 0.0

    for p in client_projects:
        terms = [p.code] + p.name.split()
        score = _match_score(tokens, terms)
        if score > best_project_score:
            best_project_score = score
            best_project = p

    return MatchResult(
        client_code=best_client.code,
        client_name=best_client.name,
        project_code=best_project.code if best_project else None,
        project_name=best_project.name if best_project else None,
        default_folder_category=best_project.default_folder_category if best_project else "MISC",
        confidence=round((best_client_score + best_project_score) / 2, 2),
    )


# ── Client endpoints ──────────────────────────────────────────────────────────

@router.get("/clients", response_model=list[ClientOut])
async def list_clients(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ClientOut]:
    result = await db.execute(
        select(NimbusClient).where(NimbusClient.active == True).order_by(NimbusClient.code)  # noqa: E712
    )
    return [ClientOut.model_validate(c) for c in result.scalars().all()]


@router.get("/clients/all", response_model=list[ClientOut])
async def list_all_clients(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ClientOut]:
    result = await db.execute(select(NimbusClient).order_by(NimbusClient.code))
    return [ClientOut.model_validate(c) for c in result.scalars().all()]


@router.post("/clients", response_model=ClientOut, status_code=201)
async def create_client(
    body: ClientCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ClientOut:
    existing = await db.execute(select(NimbusClient).where(NimbusClient.code == body.code.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Client '{body.code}' sudah ada")
    client = NimbusClient(
        code=body.code.upper(),
        name=body.name,
        aliases=[a.upper() for a in body.aliases],
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return ClientOut.model_validate(client)


@router.patch("/clients/{code}", response_model=ClientOut)
async def update_client(
    code: str,
    body: ClientUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ClientOut:
    result = await db.execute(select(NimbusClient).where(NimbusClient.code == code.upper()))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client tidak ditemukan")
    if body.name is not None:
        client.name = body.name
    if body.aliases is not None:
        client.aliases = [a.upper() for a in body.aliases]
    if body.active is not None:
        client.active = body.active
    await db.commit()
    await db.refresh(client)
    return ClientOut.model_validate(client)


@router.delete("/clients/{code}", status_code=204)
async def delete_client(
    code: str,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(NimbusClient).where(NimbusClient.code == code.upper()))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client tidak ditemukan")
    await db.delete(client)
    await db.commit()


# ── Project endpoints ─────────────────────────────────────────────────────────

@router.get("/clients/{client_code}/projects", response_model=list[ProjectOut])
async def list_projects(
    client_code: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectOut]:
    result = await db.execute(
        select(NimbusProject)
        .where(NimbusProject.client_code == client_code.upper(), NimbusProject.active == True)  # noqa: E712
        .order_by(NimbusProject.code)
    )
    return [ProjectOut.model_validate(p) for p in result.scalars().all()]


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    # Ensure client exists
    client_res = await db.execute(select(NimbusClient).where(NimbusClient.code == body.client_code.upper()))
    if not client_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Client '{body.client_code}' tidak ditemukan")
    project = NimbusProject(
        client_code=body.client_code.upper(),
        code=body.code.upper(),
        name=body.name,
        default_folder_category=body.default_folder_category.upper(),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectOut.model_validate(project)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    result = await db.execute(select(NimbusProject).where(NimbusProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    if body.name is not None:
        project.name = body.name
    if body.default_folder_category is not None:
        project.default_folder_category = body.default_folder_category.upper()
    if body.active is not None:
        project.active = body.active
    await db.commit()
    await db.refresh(project)
    return ProjectOut.model_validate(project)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(NimbusProject).where(NimbusProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    await db.delete(project)
    await db.commit()


# ── Filename matching ─────────────────────────────────────────────────────────

@router.get("/match", response_model=MatchResult)
async def match_filename(
    filename: str = "",
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchResult:
    """Return best-guess client + project from a filename."""
    if not filename:
        return MatchResult(client_code=None, client_name=None, project_code=None,
                           project_name=None, default_folder_category="MISC", confidence=0.0)

    clients_res = await db.execute(select(NimbusClient))
    projects_res = await db.execute(select(NimbusProject))
    return _best_match(filename, list(clients_res.scalars()), list(projects_res.scalars()))
