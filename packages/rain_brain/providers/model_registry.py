"""Central model registry — capabilities per model.

Capabilities:
  chat      - text chat
  tools     - function/tool calling
  vision    - image input (multimodal)
  thinking  - extended reasoning / thinking mode
  image-gen - image generation output
"""

from typing import Literal

ModelCapability = Literal["chat", "tools", "vision", "thinking", "image-gen"]

# Format: { provider: { model_id: [capabilities] } }
MODEL_REGISTRY: dict[str, dict[str, list[str]]] = {
    "anthropic": {
        "claude-opus-4-7":           ["chat", "tools", "vision", "thinking"],
        "claude-sonnet-4-6":         ["chat", "tools", "vision"],
        "claude-haiku-4-5-20251001": ["chat", "tools", "vision"],
    },
    "openai": {
        "gpt-4o":       ["chat", "tools", "vision"],
        "gpt-4o-mini":  ["chat", "tools", "vision"],
        "o3":           ["chat", "tools", "thinking"],
        "o4-mini":      ["chat", "tools", "thinking"],
        "dall-e-3":     ["image-gen"],
        "gpt-image-1":  ["image-gen"],
    },
    "google": {
        "gemini-2.5-pro-preview-05-06":  ["chat", "tools", "vision", "thinking"],
        "gemini-2.5-flash-preview-04-17": ["chat", "tools", "vision", "thinking"],
        "gemini-2.0-flash":               ["chat", "tools", "vision"],
        "gemini-3.1-flash-image-preview": ["chat", "tools", "vision", "image-gen"],
        "gemini-3.1-pro-preview":         ["chat", "tools", "vision", "thinking"],
        "gemini-1.5-pro":                 ["chat", "tools", "vision"],
        "gemini-1.5-flash":               ["chat", "tools", "vision"],
    },
    "ollama": {
        # Ollama models are dynamic — capabilities set by user via Settings
    },
}


def get_provider_models(provider: str) -> list[str]:
    """Return list of model IDs for a provider."""
    return list(MODEL_REGISTRY.get(provider, {}).keys())


def get_model_capabilities(model_id: str) -> list[str]:
    """Return capability list for a model. Falls back to ['chat', 'tools'] if unknown."""
    for provider_models in MODEL_REGISTRY.values():
        if model_id in provider_models:
            return provider_models[model_id]
    # Default: assume modern models support both chat and tools.
    # This prevents silent tool failure for newly added / custom models.
    return ["chat", "tools"]


def get_model_provider(model_id: str) -> str | None:
    """Return provider name for a model, or None if unknown."""
    for provider, models in MODEL_REGISTRY.items():
        if model_id in models:
            return provider
    return None


def has_capability(model_id: str, capability: str) -> bool:
    """Check if a model has a specific capability."""
    return capability in get_model_capabilities(model_id)
