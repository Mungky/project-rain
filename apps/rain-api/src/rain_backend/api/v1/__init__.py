"""API v1 endpoints."""

from rain_backend.api.v1.auth import router as auth_router
from rain_backend.api.v1.nimbus import router as nimbus_router
from rain_backend.api.v1.health import router as health_router
from rain_backend.api.v1.conversations import router as conversations_router
from rain_backend.api.v1.messages import router as messages_router
from rain_backend.api.v1.documents import router as documents_router
from rain_backend.api.v1.models import router as models_router
from rain_backend.api.v1.skills import router as skills_router
from rain_backend.api.v1.user import router as user_router
from rain_backend.api.v1.context import router as context_router
from rain_backend.api.v1.prompts import router as prompts_router
from rain_backend.api.v1.image_gen import router as image_gen_router
from rain_backend.api.v1.agent_runs import router as agent_runs_router
from rain_backend.api.v1.few_shot import router as few_shot_router
from rain_backend.api.v1.session_registry import router as session_registry_router
from rain_backend.api.v1.nimbus_db import router as nimbus_db_router

__all__ = [
    "auth_router",
    "nimbus_router",
    "nimbus_db_router",
    "health_router",
    "conversations_router",
    "messages_router",
    "documents_router",
    "models_router",
    "skills_router",
    "user_router",
    "context_router",
    "prompts_router",
    "image_gen_router",
    "agent_runs_router",
    "few_shot_router",
    "session_registry_router",
]

