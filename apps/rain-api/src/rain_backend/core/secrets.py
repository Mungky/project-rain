"""Symmetric encryption helpers for at-rest secrets.

Used for: provider API keys (Anthropic, OpenAI, Google, Ollama Cloud) stored
in `user_preferences.api_keys`.

Key management: a single Fernet key is read from `SECRETS_ENCRYPTION_KEY` env
(or `settings.secrets_encryption_key`). Generate one with::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

If the key is absent we fall back to plaintext storage and log a loud warning
once. This keeps local-dev working without forcing a key, while production
deployments should always set the env var.

Storage format: encrypted values are prefixed with `fernet:` so we can detect
ciphertext vs legacy plaintext and migrate transparently.
"""

from __future__ import annotations

import logging

from rain_backend.settings import settings

logger = logging.getLogger(__name__)

_PREFIX = "fernet:"
_warned = False


def _get_fernet():
    global _warned
    key = settings.secrets_encryption_key
    if not key:
        if not _warned:
            logger.warning(
                "SECRETS_ENCRYPTION_KEY not set — provider API keys will be "
                "stored as plaintext. Set the env var in production."
            )
            _warned = True
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:  # noqa: BLE001
        logger.error("Invalid SECRETS_ENCRYPTION_KEY (will fall back to plaintext): %s", e)
        return None


def encrypt_str(value: str | None) -> str:
    """Return a fernet:<token> string, or the original value if no key is set
    or the input is falsy/whitespace."""
    if not value or not value.strip():
        return value or ""
    if value.startswith(_PREFIX):
        # already encrypted
        return value
    f = _get_fernet()
    if f is None:
        return value
    token = f.encrypt(value.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_str(value: str | None) -> str:
    """Return the cleartext for a fernet:<token> value, or pass through legacy
    plaintext."""
    if not value:
        return ""
    if not value.startswith(_PREFIX):
        return value  # legacy plaintext or just empty
    f = _get_fernet()
    if f is None:
        # Stored encrypted but no key available — refuse to leak ciphertext.
        return ""
    try:
        return f.decrypt(value[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to decrypt stored secret: %s", e)
        return ""


def redact(value: str | None) -> str:
    """Return a masked representation safe to send to the frontend."""
    if not value:
        return ""
    s = decrypt_str(value) if value.startswith(_PREFIX) else value
    if len(s) <= 8:
        return "•" * len(s)
    return s[:4] + "•" * (len(s) - 8) + s[-4:]
