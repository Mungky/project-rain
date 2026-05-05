"""Image generation endpoint — supports OpenAI and Google Imagen."""

import base64
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from rain_backend.api.deps import get_db
from rain_brain.providers.model_registry import get_model_capabilities, get_model_provider
from db.schemas import UserPreference

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

VALID_SIZES_OPENAI = {"1024x1024", "1792x1024", "1024x1792"}
VALID_QUALITIES_OPENAI = {"standard", "hd"}


class ImageGenRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    model: str
    size: str = "1024x1024"
    quality: str = "standard"
    n: int = Field(default=1, ge=1, le=4)


class ImageGenResponse(BaseModel):
    images: list[str]  # list of data URIs or URLs
    model: str
    provider: str


async def _get_api_key(provider: str, db: AsyncSession) -> str | None:
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == DEFAULT_USER_ID)
    )
    pref = result.scalar_one_or_none()
    if not pref or not pref.api_keys:
        return None
    return pref.api_keys.get(provider, {}).get("key", "").strip() or None


@router.post("", response_model=ImageGenResponse)
async def generate_image(
    body: ImageGenRequest,
    db: AsyncSession = Depends(get_db),
) -> ImageGenResponse:
    """Generate images from a text prompt."""
    caps = get_model_capabilities(body.model)
    if "image-gen" not in caps:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "capability_mismatch",
                "message": f"Model '{body.model}' does not support image generation. "
                           f"Select a model with the 'image-gen' capability.",
            },
        )

    provider_name = get_model_provider(body.model)
    if not provider_name:
        raise HTTPException(status_code=400, detail={"code": "unknown_model", "message": f"Unknown model: {body.model}"})

    api_key = await _get_api_key(provider_name, db)

    if provider_name == "openai":
        return await _openai_generate(body, api_key)
    elif provider_name == "google":
        return await _google_generate(body, api_key)
    else:
        raise HTTPException(
            status_code=400,
            detail={"code": "unsupported_provider", "message": f"Image generation not supported for provider '{provider_name}'."},
        )


async def _openai_generate(body: ImageGenRequest, api_key: str | None) -> ImageGenResponse:
    try:
        import openai as _openai
        client = _openai.AsyncOpenAI(api_key=api_key)

        size = body.size if body.size in VALID_SIZES_OPENAI else "1024x1024"
        quality = body.quality if body.quality in VALID_QUALITIES_OPENAI else "standard"

        response = await client.images.generate(
            model=body.model,
            prompt=body.prompt,
            size=size,
            quality=quality,
            n=body.n,
            response_format="b64_json",
        )

        images = []
        for item in response.data:
            if item.b64_json:
                images.append(f"data:image/png;base64,{item.b64_json}")
            elif item.url:
                images.append(item.url)

        return ImageGenResponse(images=images, model=body.model, provider="openai")

    except _openai.AuthenticationError:
        raise HTTPException(status_code=401, detail={"code": "invalid_api_key", "message": "OpenAI API key is invalid."})
    except Exception as e:
        logger.error("OpenAI image gen failed: %s", e)
        raise HTTPException(status_code=500, detail={"code": "image_gen_error", "message": str(e)})


async def _google_generate(body: ImageGenRequest, api_key: str | None) -> ImageGenResponse:
    """Generate image via Gemini image models."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(model_name=body.model)
        response = await model.generate_content_async(
            body.prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="image/png",
            ),
        )

        images = []
        for part in response.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                b64 = base64.b64encode(part.inline_data.data).decode()
                mime = part.inline_data.mime_type or "image/png"
                images.append(f"data:{mime};base64,{b64}")

        if not images:
            raise HTTPException(status_code=500, detail={"code": "no_image", "message": "Model returned no image data."})

        return ImageGenResponse(images=images, model=body.model, provider="google")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Google image gen failed: %s", e)
        raise HTTPException(status_code=500, detail={"code": "image_gen_error", "message": str(e)})
