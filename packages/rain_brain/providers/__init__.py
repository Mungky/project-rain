"""Provider adapter implementations.

Follows Contract 7 Provider Adapter Interface.
"""

from typing import Type
from rain_brain.providers.base import Provider, ChatRequest, ChatChunk
from rain_brain.providers.ollama import OllamaProvider
from rain_brain.providers.anthropic import AnthropicProvider
from rain_brain.providers.openai import OpenAIProvider
from rain_brain.providers.google import GoogleProvider
from rain_brain.config import brain_settings

__all__ = [
    "Provider",
    "ChatRequest",
    "ChatChunk",
    "get_provider",
    "build_providers",
    "PROVIDERS",
    "OllamaProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GoogleProvider"
]

PROVIDERS: dict[str, Type[Provider]] = {
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "google": GoogleProvider,
}


def get_provider(name: str) -> Provider | None:
    """Get an initialized provider instance by name."""
    if name == "ollama":
        return OllamaProvider(base_url=brain_settings.ollama_base_url, api_key=brain_settings.ollama_api_key)
    if name == "anthropic" and brain_settings.anthropic_api_key:
        return AnthropicProvider(api_key=brain_settings.anthropic_api_key)
    if name == "openai" and brain_settings.openai_api_key:
        return OpenAIProvider(api_key=brain_settings.openai_api_key)
    if name == "google" and brain_settings.google_api_key:
        return GoogleProvider(api_key=brain_settings.google_api_key)
    return None


async def build_providers(settings) -> dict[str, Provider]:
    """Build enabled providers based on configuration."""
    providers: dict[str, Provider] = {}
    
    # Ollama is always enabled
    providers["ollama"] = OllamaProvider(base_url=brain_settings.ollama_base_url, api_key=brain_settings.ollama_api_key)
    
    # Phase 2+ providers based on config
    if brain_settings.anthropic_api_key:
        providers["anthropic"] = AnthropicProvider(api_key=brain_settings.anthropic_api_key)
        
    if brain_settings.openai_api_key:
        providers["openai"] = OpenAIProvider(api_key=brain_settings.openai_api_key)
        
    if brain_settings.google_api_key:
        providers["google"] = GoogleProvider(api_key=brain_settings.google_api_key)
    
    return providers
