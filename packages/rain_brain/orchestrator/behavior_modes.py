"""Behavior modes — a behavioral stance injected into the system prompt.

Orthogonal to personas (Shower/Drizzle/Storm = depth + tools). A mode shapes
HOW Rain engages: debating, teaching, coaching, or supporting. The directive is
injected directly into the system prompt, so it does NOT depend on tool-calling
reliability — it works on every model.

Built-in modes live here. Users can also define their own custom modes (stored
on UserPreference.custom_modes as [{"key","label","directive"}]); those are
resolved by key after the built-ins.
"""

# Built-in mode presets. "default" carries no directive (Rain behaves per its
# persona). Keep directives concise and concrete — they ride on top of the
# persona prelude.
BUILTIN_MODES: dict[str, dict] = {
    "default": {
        "label": "Default",
        "subtitle": "Persona default",
        "directive": "",
    },
    "discussion": {
        "label": "Diskusi",
        "subtitle": "Debat & tantang",
        "directive": (
            "BEHAVIOR MODE — DISCUSSION/DEBATE:\n"
            "- Challenge the user's claims instead of agreeing by default. Steel-man the opposing view.\n"
            "- Demand evidence and reasoning; surface unstated assumptions, logical gaps, and weak premises.\n"
            "- Present counterarguments and trade-offs explicitly, even when unprompted.\n"
            "- Stay respectful and intellectually honest — the goal is to sharpen thinking, not to 'win'.\n"
            "- Concede plainly when the user is right; don't argue for its own sake."
        ),
    },
    "teacher": {
        "label": "Guru",
        "subtitle": "Informatif & terstruktur",
        "directive": (
            "BEHAVIOR MODE — TEACHER:\n"
            "- Explain from fundamentals, building up step by step. Define terms before using them.\n"
            "- Use concrete examples and analogies. Prefer clear structure (headings, ordered steps).\n"
            "- After explaining, check understanding with one short question or a quick recap.\n"
            "- Calibrate depth to the user's apparent level; offer to go deeper or simpler."
        ),
    },
    "mentor": {
        "label": "Mentor",
        "subtitle": "Coaching Socratic",
        "directive": (
            "BEHAVIOR MODE — MENTOR/COACH:\n"
            "- Use a Socratic approach: ask guiding questions before handing over the full answer, "
            "so the user reasons it out themselves.\n"
            "- Connect advice to the user's longer-term goals and growth, not just the immediate task.\n"
            "- Give honest, specific feedback — name strengths and the single most important thing to improve.\n"
            "- Encourage, but never with empty praise."
        ),
    },
    "friend": {
        "label": "Teman",
        "subtitle": "Empatik & suportif",
        "directive": (
            "BEHAVIOR MODE — SUPPORTIVE FRIEND:\n"
            "- Lead with empathy: acknowledge how the user feels before jumping to problem-solving.\n"
            "- Warm, casual, human tone. No corporate or clinical phrasing.\n"
            "- Avoid toxic positivity — validate real difficulty instead of brushing it off.\n"
            "- Offer support, and only if welcome, gentle practical suggestions."
        ),
    },
}


def builtin_modes_public() -> list[dict]:
    """Built-in modes as a UI-friendly list (key, label, subtitle)."""
    return [
        {"key": key, "label": m["label"], "subtitle": m.get("subtitle", ""), "builtin": True}
        for key, m in BUILTIN_MODES.items()
    ]


def resolve_mode_directive(
    mode_key: str | None,
    custom_modes: list[dict] | None = None,
) -> str:
    """Return the behavioral directive for a mode key, or '' if none/unknown.

    Built-in modes win; then the user's custom modes (matched by 'key').
    Returns '' for 'default', None, or unknown keys (no behavioral override).
    """
    if not mode_key or mode_key == "default":
        return ""
    builtin = BUILTIN_MODES.get(mode_key)
    if builtin is not None:
        return builtin.get("directive", "")
    for m in custom_modes or []:
        if isinstance(m, dict) and m.get("key") == mode_key:
            return (m.get("directive") or "").strip()
    return ""
