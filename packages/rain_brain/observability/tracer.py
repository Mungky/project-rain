"""Langfuse observability wrapper with graceful no-op fallback.

If LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not set, every call
returns a _Noop object that silently discards all method calls — the rest
of the codebase never needs to check whether tracing is active.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class _Noop:
    """Silent sink — absorbs any attribute access and any call."""

    def __getattr__(self, _name: str) -> "_Noop":
        return _Noop()

    def __call__(self, *args: Any, **kwargs: Any) -> "_Noop":
        return _Noop()

    def __enter__(self) -> "_Noop":
        return self

    def __exit__(self, *_: Any) -> None:
        pass


class RainTracer:
    """Thin wrapper around the Langfuse SDK.

    Exposes trace / span / generation factories.  All methods fall back to
    _Noop when Langfuse is not configured or the SDK is unavailable.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._enabled = False
        self._init()

    def _init(self) -> None:
        try:
            from rain_brain.config import brain_settings

            pk = brain_settings.langfuse_public_key
            sk = brain_settings.langfuse_secret_key
            host = brain_settings.langfuse_host

            if not pk or not sk:
                logger.debug("Langfuse keys not set — observability disabled")
                return

            from langfuse import Langfuse  # type: ignore[import]

            self._client = Langfuse(
                public_key=pk,
                secret_key=sk,
                host=host,
            )
            self._enabled = True
            logger.info("Langfuse observability enabled → %s", host)

        except ImportError:
            logger.debug("langfuse package not installed — observability disabled")
        except Exception as e:
            logger.warning("Langfuse init failed: %s — tracing disabled", e)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def trace(self, **kwargs: Any) -> Any:
        """Start a new top-level trace and return the trace object."""
        if self._enabled and self._client:
            try:
                return self._client.trace(**kwargs)
            except Exception as e:
                logger.debug("Langfuse trace() failed: %s", e)
        return _Noop()

    def flush(self) -> None:
        """Flush pending events — call before shutdown or test teardown."""
        if self._enabled and self._client:
            try:
                self._client.flush()
            except Exception as e:
                logger.debug("Langfuse flush() failed: %s", e)


tracer = RainTracer()
