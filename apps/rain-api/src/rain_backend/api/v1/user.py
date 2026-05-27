"""User preferences endpoints — provider config, API keys, system prompt."""

import logging
from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from rain_backend.api.deps import get_db
from db.schemas import UserPreference, Message, Conversation

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# ── Usage Schemas ─────────────────────────────────────────────────────────────

class UsageByModel(BaseModel):
    model: str
    tokens_in: int
    tokens_out: int
    messages: int


class UsageResponse(BaseModel):
    total_tokens_in: int
    total_tokens_out: int
    total_messages: int
    total_conversations: int
    by_model: list[UsageByModel]
    period: str


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    period: str = "all",
    db: AsyncSession = Depends(get_db)
) -> UsageResponse:
    """Return global usage metrics aggregated from all conversations."""
    
    # 1. Total conversations count
    conv_count_stmt = select(func.count(Conversation.id)).where(Conversation.user_id == DEFAULT_USER_ID)
    conv_count = (await db.execute(conv_count_stmt)).scalar() or 0

    # 2. Base query for messages
    msg_stmt = (
        select(
            Message.model,
            func.sum(Message.tokens_in).label("in_sum"),
            func.sum(Message.tokens_out).label("out_sum"),
            func.count(Message.id).label("msg_count")
        )
        .join(Conversation)
        .where(Conversation.user_id == DEFAULT_USER_ID)
        .group_by(Message.model)
    )

    # Filter by period if needed
    if period == "today":
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        msg_stmt = msg_stmt.where(Message.created_at >= start)
    elif period == "week":
        start = datetime.now(UTC) - timedelta(days=7)
        msg_stmt = msg_stmt.where(Message.created_at >= start)
    elif period == "month":
        start = datetime.now(UTC) - timedelta(days=30)
        msg_stmt = msg_stmt.where(Message.created_at >= start)

    results = await db.execute(msg_stmt)
    by_model = []
    total_in = 0
    total_out = 0
    total_msgs = 0

    for row in results:
        m_id = row[0] or "unknown"
        tin = int(row[1] or 0)
        tout = int(row[2] or 0)
        cnt = int(row[3] or 0)
        
        by_model.append(UsageByModel(
            model=m_id,
            tokens_in=tin,
            tokens_out=tout,
            messages=cnt
        ))
        total_in += tin
        total_out += tout
        total_msgs += cnt

    return UsageResponse(
        total_tokens_in=total_in,
        total_tokens_out=total_out,
        total_messages=total_msgs,
        total_conversations=conv_count,
        by_model=by_model,
        period=period
    )

_DEFAULT_PROVIDERS: dict[str, dict] = {
    "anthropic": {"enabled": False, "key": ""},
    "openai":    {"enabled": False, "key": ""},
    "google":    {"enabled": False, "key": ""},
    "ollama":    {"enabled": True,  "key": "", "base_url": "https://ollama.com"},
}


class ProviderUpdate(BaseModel):
    enabled: bool | None = None
    key: str | None = None
    base_url: str | None = None


class PreferencesUpdate(BaseModel):
    providers: dict[str, ProviderUpdate] | None = None
    custom_system_prompt: str | None = None
    hidden_models: list[str] | None = None


class PreferencesResponse(BaseModel):
    providers: dict[str, dict[str, Any]]
    custom_system_prompt: str | None
    hidden_models: list[str] = []


async def _get_or_create_pref(db: AsyncSession) -> UserPreference:
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == DEFAULT_USER_ID)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = UserPreference(
            user_id=DEFAULT_USER_ID,
            api_keys=dict(_DEFAULT_PROVIDERS),
        )
        db.add(pref)
        await db.flush()
    return pref


def _merged_providers(stored: dict | None) -> dict[str, dict]:
    """Merge stored provider config with defaults, ensuring all keys exist."""
    base = {k: dict(v) for k, v in _DEFAULT_PROVIDERS.items()}
    for name, cfg in (stored or {}).items():
        if name in base:
            base[name].update(cfg)
    return base


@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)) -> PreferencesResponse:
    """Return current user preferences including provider configurations."""
    pref = await _get_or_create_pref(db)
    await db.commit()
    raw = pref.api_keys or {}
    hidden = list(raw.get("hidden_models", []))
    return PreferencesResponse(
        providers=_merged_providers(raw),
        custom_system_prompt=pref.custom_system_prompt,
        hidden_models=hidden,
    )


@router.patch("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    body: PreferencesUpdate,
    db: AsyncSession = Depends(get_db),
) -> PreferencesResponse:
    """Update provider configs or system prompt."""
    pref = await _get_or_create_pref(db)
    providers = _merged_providers(pref.api_keys)

    if body.providers:
        for name, update in body.providers.items():
            if name not in providers:
                continue
            if update.enabled is not None:
                providers[name]["enabled"] = update.enabled
            if update.key is not None:
                providers[name]["key"] = update.key
                # auto-enable provider when a key is saved
                if update.key.strip():
                    providers[name]["enabled"] = True
            if update.base_url is not None:
                providers[name]["base_url"] = update.base_url

    if body.custom_system_prompt is not None:
        pref.custom_system_prompt = body.custom_system_prompt

    if body.hidden_models is not None:
        providers["hidden_models"] = body.hidden_models

    pref.api_keys = providers
    await db.commit()

    hidden = list(providers.get("hidden_models", []))
    return PreferencesResponse(
        providers=_merged_providers(providers),
        custom_system_prompt=pref.custom_system_prompt,
        hidden_models=hidden,
    )
