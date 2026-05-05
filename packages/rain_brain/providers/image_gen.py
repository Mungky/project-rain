"""Provider-agnostic image generation for Nimbus persona."""

import asyncio
import base64
import logging
from typing import AsyncIterator

from rain_brain.providers.base import ChatChunk

logger = logging.getLogger(__name__)


async def generate_image(
    prompt: str,
    model: str,
    providers: dict,
    api_keys: dict | None = None,
) -> AsyncIterator[ChatChunk]:
    """Generate an image and yield SSE chunks. Images returned as markdown data URIs."""
    if model.startswith("gemini"):
        async for chunk in _gemini_image(prompt, model, providers, api_keys):
            yield chunk
    elif model.startswith(("dall-e", "gpt-image")):
        async for chunk in _openai_image(prompt, model, providers, api_keys):
            yield chunk
    else:
        yield ChatChunk(
            type="error",
            data={
                "code": "nimbus_unsupported",
                "message": (
                    f"Model '{model}' does not support image generation. "
                    "Configure a Gemini or DALL-E model for the Nimbus persona in Settings."
                ),
            },
        )


async def _gemini_image(
    prompt: str,
    model: str,
    providers: dict,
    api_keys: dict | None,
) -> AsyncIterator[ChatChunk]:
    """Generate image via Google Gemini (gemini-2.0-flash-exp or imagen)."""
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import google.generativeai as genai

        api_key = None
        if api_keys:
            api_key = api_keys.get("google", {}).get("key", "").strip() or None
        if not api_key:
            google_provider = providers.get("google")
            if google_provider:
                api_key = getattr(google_provider, "_api_key", None)

        if not api_key:
            yield ChatChunk(
                type="error",
                data={
                    "code": "no_api_key",
                    "message": "No Google API key configured. Add one in Settings → API Credentials.",
                },
            )
            return

        genai.configure(api_key=api_key)

        yield ChatChunk(type="token", data="_Generating image..._\n\n")

        gemini_model = genai.GenerativeModel(model)
        async with asyncio.timeout(120):
            response = await gemini_model.generate_content_async(
                prompt,
                generation_config={"response_modalities": ["IMAGE", "TEXT"]},
            )

        found_image = False
        text_parts: list[str] = []

        for part in response.parts:
            if (
                hasattr(part, "inline_data")
                and part.inline_data
                and part.inline_data.mime_type.startswith("image/")
            ):
                data_b64 = base64.b64encode(bytes(part.inline_data.data)).decode()
                data_uri = f"data:{part.inline_data.mime_type};base64,{data_b64}"
                yield ChatChunk(type="token", data=f"![Generated image]({data_uri})\n")
                found_image = True
            elif hasattr(part, "text") and part.text:
                text_parts.append(part.text)

        if text_parts:
            yield ChatChunk(type="token", data="\n" + "".join(text_parts))

        if not found_image:
            yield ChatChunk(
                type="token",
                data="_(No image returned. Check that the model supports image generation and the prompt is valid.)_",
            )

        yield ChatChunk(type="done", data={"model": model})

    except asyncio.TimeoutError:
        yield ChatChunk(
            type="error",
            data={"code": "nimbus_timeout", "message": "Image generation timed out after 120s."},
        )
    except Exception as e:
        logger.error("Gemini image gen error: %s", e)
        yield ChatChunk(
            type="error",
            data={"code": "nimbus_error", "message": str(e)},
        )


async def _openai_image(
    prompt: str,
    model: str,
    providers: dict,
    api_keys: dict | None,
) -> AsyncIterator[ChatChunk]:
    """Generate image via OpenAI DALL-E or gpt-image-1."""
    try:
        from openai import AsyncOpenAI

        api_key = None
        if api_keys:
            api_key = api_keys.get("openai", {}).get("key", "").strip() or None
        if not api_key:
            openai_provider = providers.get("openai")
            if openai_provider:
                api_key = getattr(openai_provider, "_api_key", None)

        if not api_key:
            yield ChatChunk(
                type="error",
                data={
                    "code": "no_api_key",
                    "message": "No OpenAI API key configured. Add one in Settings → API Credentials.",
                },
            )
            return

        yield ChatChunk(type="token", data="_Generating image..._\n\n")

        client = AsyncOpenAI(api_key=api_key)
        # gpt-image-1 does not accept response_format; dall-e-* models do
        gen_kwargs: dict = {"model": model, "prompt": prompt, "n": 1}
        if model.startswith("dall-e"):
            gen_kwargs["response_format"] = "b64_json"

        async with asyncio.timeout(120):
            response = await client.images.generate(**gen_kwargs)

        img_data = response.data[0]
        b64 = img_data.b64_json
        if b64 is None:
            # gpt-image-1 may return url instead — fetch and re-encode
            import httpx
            async with httpx.AsyncClient() as hc:
                img_bytes = (await hc.get(img_data.url, timeout=30)).content
            b64 = base64.b64encode(img_bytes).decode()
        data_uri = f"data:image/png;base64,{b64}"
        yield ChatChunk(type="token", data=f"![Generated image]({data_uri})\n")
        yield ChatChunk(type="done", data={"model": model})

    except asyncio.TimeoutError:
        yield ChatChunk(
            type="error",
            data={"code": "nimbus_timeout", "message": "Image generation timed out after 120s."},
        )
    except Exception as e:
        logger.error("OpenAI image gen error: %s", e)
        yield ChatChunk(
            type="error",
            data={"code": "nimbus_error", "message": str(e)},
        )
