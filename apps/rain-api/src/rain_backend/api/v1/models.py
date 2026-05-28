"""Model listing and management endpoints."""

import logging
import hashlib
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from rain_backend.api.deps import get_db, get_providers
from db.schemas.dto_common import ModelResponse
from rain_brain.providers import OllamaProvider, AnthropicProvider, OpenAIProvider, GoogleProvider
from db.schemas import UserPreference

logger = logging.getLogger(__name__)
router = APIRouter()


class PingRequest(BaseModel):
    model_id: str
    provider: str
    persona: str | None = None


class PingResponse(BaseModel):
    reachable: bool
    model_id: str
    provider: str
    error: str | None = None

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


# Cache of (provider_name, config-hash) → instantiated provider. Without this
# the chat / models / ping endpoints all created a fresh httpx.AsyncClient per
# request and never closed it → file-descriptor leak under load.
_PROVIDER_CACHE: dict[tuple[str, str], object] = {}


def _cfg_signature(name: str, base_url: str | None, api_key: str | None) -> str:
    """Stable opaque key for a provider config — never logs the raw key."""
    raw = f"{name}|{base_url or ''}|{api_key or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def _build_fresh_provider(name: str, cfg: dict):
    """Build (or fetch cached) provider instance from user-stored config,
    falling back to env settings when DB config is missing/default."""
    from rain_backend.core.secrets import decrypt_str
    try:
        if name == "ollama":
            from rain_brain.config import brain_settings
            base_url = cfg.get("base_url") or "http://localhost:11434"
            if base_url == "http://localhost:11434" and brain_settings.ollama_base_url != base_url:
                base_url = brain_settings.ollama_base_url
            stored = (cfg.get("key") or "").strip()
            api_key = decrypt_str(stored) if stored else None
            if not api_key:
                api_key = brain_settings.ollama_api_key
            sig = (name, _cfg_signature(name, base_url, api_key))
            if sig not in _PROVIDER_CACHE:
                _PROVIDER_CACHE[sig] = OllamaProvider(base_url=base_url, api_key=api_key)
            return _PROVIDER_CACHE[sig]

        stored = (cfg.get("key") or "").strip()
        key = decrypt_str(stored) if stored else ""
        if not key:
            return None
        sig = (name, _cfg_signature(name, None, key))
        if sig in _PROVIDER_CACHE:
            return _PROVIDER_CACHE[sig]
        if name == "anthropic":
            inst = AnthropicProvider(api_key=key)
        elif name == "openai":
            inst = OpenAIProvider(api_key=key)
        elif name == "google":
            inst = GoogleProvider(api_key=key)
        else:
            return None
        _PROVIDER_CACHE[sig] = inst
        return inst
    except Exception as e:
        logger.warning("Failed to build provider %s: %s", name, e)
    return None


@router.get("", response_model=list[ModelResponse])
async def list_models(
    db: AsyncSession = Depends(get_db),
    startup_providers: dict = Depends(get_providers),
) -> list[ModelResponse]:
    """List models from enabled providers. Reads toggle state + API keys from DB."""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == DEFAULT_USER_ID)
    )
    pref = result.scalar_one_or_none()
    provider_cfg: dict = pref.api_keys if pref and pref.api_keys else {}

    all_models: list[ModelResponse] = []
    hidden_models: set[str] = set(provider_cfg.get("hidden_models", []))

    # Load user capability overrides once (mainly for Ollama). Fails gracefully if table missing.
    from rain_brain.providers.model_registry import get_model_capabilities
    capability_overrides: dict[str, list[str]] = {}
    display_name_overrides: dict[str, str] = {}
    try:
        from db.schemas.model_capability_override import ModelCapabilityOverride
        overrides_result = await db.execute(select(ModelCapabilityOverride))
        for o in overrides_result.scalars().all():
            capability_overrides[o.model_id] = o.capabilities
            if o.display_name:
                display_name_overrides[o.model_id] = o.display_name
    except Exception as e:
        logger.debug("Could not load capability overrides (table may not exist yet): %s", e)

    for name, startup_provider in startup_providers.items():
        cfg = provider_cfg.get(name, {})
        default_enabled = (name == "ollama")
        if not cfg.get("enabled", default_enabled):
            continue

        # If user has a DB-stored key, prefer it over the startup provider
        user_key = cfg.get("key", "").strip()
        active_provider = startup_provider
        if user_key and name != "ollama":
            fresh = await _build_fresh_provider(name, cfg)
            if fresh:
                active_provider = fresh

        try:
            models = await active_provider.list_models()
            for model_id in models:
                caps = capability_overrides.get(model_id) or get_model_capabilities(model_id)
                all_models.append(ModelResponse(
                    id=model_id,
                    name=model_id,
                    display_name=display_name_overrides.get(model_id),
                    provider=name,
                    enabled=model_id not in hidden_models,
                    capabilities=caps,
                ))
        except Exception as e:
            logger.warning("list_models failed for %s: %s", name, e)

    return all_models


@router.post("/ping", response_model=PingResponse)
async def ping_model(
    body: PingRequest,
    db: AsyncSession = Depends(get_db),
    startup_providers: dict = Depends(get_providers),
) -> PingResponse:
    """Test whether a model is reachable and usable with the stored credentials."""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == DEFAULT_USER_ID)
    )
    pref = result.scalar_one_or_none()
    provider_cfg: dict = pref.api_keys if pref and pref.api_keys else {}
    cfg = provider_cfg.get(body.provider, {})

    provider = await _build_fresh_provider(body.provider, cfg)
    if provider is None:
        provider = startup_providers.get(body.provider)
    if provider is None:
        return PingResponse(
            reachable=False,
            model_id=body.model_id,
            provider=body.provider,
            error=f"Provider '{body.provider}' is not configured.",
        )

    try:
        available = await provider.list_models()
        if body.model_id not in available:
            return PingResponse(
                reachable=False,
                model_id=body.model_id,
                provider=body.provider,
                error=f"Model '{body.model_id}' not found in {body.provider}.",
            )
            
        # Try generating a response to test tools and reasoning
        from rain_brain.providers.base import ChatRequest

        tools = None
        if body.persona == "drizzle" or body.persona == "storm":
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_internet",
                        "description": "Search the internet for information",
                        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "query_database",
                        "description": "Query the rain database",
                        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
                    }
                }
            ]

        # Shower: no tools, simple text-only ping
        if body.persona == "shower":
            tools = None
            
        req = ChatRequest(
            messages=[{"role": "user", "content": "Ping! Just reply with 'Pong'."}],
            model=body.model_id,
            max_tokens=10,
            stream=True,
            tools=tools
        )
        
        # Test if the model throws an error with the given capabilities
        async for chunk in provider.chat(req):
            if chunk.type == "error":
                err_data = chunk.data
                err_msg = err_data.get("message") if isinstance(err_data, dict) else str(err_data)
                
                # If Ollama throws 500, it might be because the model doesn't support tools.
                # Let's try a fallback ping without tools to verify if the model is just incompatible with Drizzle.
                if (body.persona == "drizzle" or body.persona == "storm") and "500" in err_msg and body.provider == "ollama":
                    fallback_req = ChatRequest(
                        messages=[{"role": "user", "content": "Ping"}],
                        model=body.model_id,
                        max_tokens=10,
                        stream=True,
                        tools=None
                    )
                    fallback_success = False
                    async for fallback_chunk in provider.chat(fallback_req):
                        if fallback_chunk.type != "error":
                            fallback_success = True
                        break
                    
                    if fallback_success:
                        return PingResponse(
                            reachable=False,
                            model_id=body.model_id,
                            provider=body.provider,
                            error="Model is running but crashed when given tools. Drizzle requires a model that natively supports Tool Calling / Function Calling.",
                        )

                return PingResponse(
                    reachable=False,
                    model_id=body.model_id,
                    provider=body.provider,
                    error=err_msg,
                )
            break # Just need to see if it starts successfully without an immediate error

        return PingResponse(reachable=True, model_id=body.model_id, provider=body.provider)

    except Exception as e:
        return PingResponse(
            reachable=False,
            model_id=body.model_id,
            provider=body.provider,
            error=str(e),
        )
