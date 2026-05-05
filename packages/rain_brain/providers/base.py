"""Provider Adapter Interface (Contract 7).

All LLM providers must implement this protocol.
"""

from typing import Protocol, AsyncIterator, Literal, Any
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request for chat completion."""
    messages: list[dict[str, Any]]
    model: str
    temperature: float = 0.7
    max_tokens: int = 8192
    stream: bool = True
    response_format: dict | None = None
    tools: list[dict] | None = None


class ChatChunk(BaseModel):
    """Streaming chunk for chat responses."""
    type: Literal["token", "reasoning", "tool_call", "tool_result", "neural_context", "react_step", "correction", "done", "error"]
    data: list | dict | str


class Provider(Protocol):
    """Protocol for LLM providers."""
    name: str

    async def list_models(self) -> list[str]:
        """List available models from this provider."""
        ...

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Stream chat completion."""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...

    async def health(self) -> bool:
        """Check if provider is healthy."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...