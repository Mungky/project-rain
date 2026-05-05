"""Tag-based model rotation for Rain.

Each registered model in model_capability_overrides has a list of task tags.
The router detects the task type from the incoming message and picks the best model.
Multiple models with the same tag are rotated round-robin.
"""

import re
import logging
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.schemas.model_capability_override import ModelCapabilityOverride

logger = logging.getLogger(__name__)

# Round-robin counters per (persona, tag) — in-process only, resets on restart
_rotation_counters: dict[str, int] = defaultdict(int)

# Canonical tag list (order = priority when multiple tags detected)
ALL_TAGS = [
    "vision",
    "document",
    "math",
    "coding",
    "creative_writing",
    "instruction",
    "hard_prompt_en",
    "hard_prompt",
    "multi_turn",
    "english",
    "general_knowledge",
    "text",
    "default",
]

# ── Heuristic tag detection ────────────────────────────────────────────────────

_MATH_SYMBOLS = re.compile(r"[∫∑√∞≈≤≥∂±×÷∈∉⊂⊃∪∩]")
_MATH_WORDS    = re.compile(
    r"\b(calcul|integral|derivative|equation|formula|solve|proof|matrix|eigenvalue|hitung|kalkulus|persamaan|rumus|turunan|integral|vektor|matriks|statistik)\b",
    re.I,
)
_CODE_FENCE  = re.compile(r"```|\bdef \b|\bclass \b|\bimport \b|\bfunction\b|\bconst \b|\blet \b|\bvar \b")
_CODE_WORDS  = re.compile(
    r"\b(code|bug|debug|syntax|compile|runtime|error|stack trace|algorithm|kode|program|fungsi|variabel|loop|array|object|API|endpoint)\b",
    re.I,
)
_CREATIVE    = re.compile(
    r"\b(write|story|poem|novel|creative|fiction|dialogue|script|cerita|puisi|tulis|karangan|fiksi|naratif)\b",
    re.I,
)
_INSTRUCTION = re.compile(
    r"\b(step[- ]by[- ]step|instructions?|guide|tutorial|how to|cara|langkah|petunjuk|instruksi|panduan)\b",
    re.I,
)

# English detection: count ASCII letters vs non-ASCII (Indonesian/CJK etc.)
def _english_ratio(text: str) -> float:
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters == 0:
        return 1.0
    return ascii_letters / total_letters


def detect_tag(
    message: str,
    has_images: bool = False,
    has_docs: bool = False,
    history_length: int = 0,
) -> str:
    """Detect the primary task tag from the message context."""
    if has_images:
        return "vision"
    if has_docs:
        return "document"

    stripped = message.strip()
    length = len(stripped)

    if _MATH_SYMBOLS.search(message) or _MATH_WORDS.search(message):
        return "math"
    if _CODE_FENCE.search(message) or _CODE_WORDS.search(message):
        return "coding"
    if _CREATIVE.search(message):
        return "creative_writing"
    if _INSTRUCTION.search(message):
        return "instruction"

    is_english = _english_ratio(stripped) > 0.85
    is_long_complex = length > 350 and (stripped.count("?") > 1 or "\n" in stripped)

    if is_long_complex:
        return "hard_prompt_en" if is_english else "hard_prompt"
    if history_length > 12:
        return "multi_turn"
    if is_english:
        return "english"
    return "default"


# ── Model selection ────────────────────────────────────────────────────────────

async def select_model(
    message: str,
    persona: str,
    db: AsyncSession,
    has_images: bool = False,
    has_docs: bool = False,
    history_length: int = 0,
    fallback: str | None = None,
    hidden_models: list[str] | None = None,
) -> str | None:
    """Pick the best model for this message, rotating among equals.

    Returns model_id or None if nothing is registered.
    """
    primary_tag = detect_tag(message, has_images, has_docs, history_length)
    logger.debug("model_router: persona=%s tag=%s", persona, primary_tag)

    # Load all registered models for this persona
    result = await db.execute(
        select(ModelCapabilityOverride).where(ModelCapabilityOverride.persona == persona)
    )
    overrides = result.scalars().all()

    # Filter out hidden/disabled models
    hidden = set(hidden_models or [])
    overrides = [o for o in overrides if o.model_id not in hidden]

    if not overrides:
        return fallback

    # Build tag → [model_id] mapping
    tag_map: dict[str, list[str]] = defaultdict(list)
    for o in overrides:
        for tag in (o.tags or []):
            tag_map[tag].append(o.model_id)

    # Try primary tag, then fall back through the priority list
    probe_order = [primary_tag] + [t for t in ALL_TAGS if t != primary_tag]
    for tag in probe_order:
        candidates = tag_map.get(tag, [])
        if candidates:
            key = f"{persona}:{tag}"
            idx = _rotation_counters[key] % len(candidates)
            _rotation_counters[key] += 1
            chosen = candidates[idx]
            logger.info("model_router: selected %s (tag=%s, idx=%d/%d)", chosen, tag, idx, len(candidates))
            return chosen

    # Last resort: first registered model for persona
    return overrides[0].model_id if overrides else fallback
