---
name: prompt-engineering-for-tiny-models
description: Use this skill when the Backend Agent is constructing prompts for local models (3B–8B parameter range running on the 4GB RTX 3050M). Triggers when writing the chat orchestrator, designing critic loops, building skill-routing prompts, or any time a prompt is sent to Ollama. This is the central "Match Opus" skill — the techniques here are how Rain's small model output reaches frontier-quality on bounded tasks.
---

# Skill: prompt-engineering-for-tiny-models

## Purpose
Frontier models (Opus, Gemini Ultra) succeed on freestyle, vague prompts. **Tiny models (3B) fail on those same prompts.** They need different inputs to produce comparable outputs. This skill encodes the techniques that make a 3B model competitive: decomposition, structure, retrieval, constraints, and critique.

This is the operational core of PRD §6 ("The Match Opus Bet"). Internalize it.

## When to use
- Writing any prompt that will be sent to a local model (Ollama).
- Designing the chat orchestrator's system prompt.
- Building critic loops (Phase 3).
- Designing prompts for skill selection / tool routing.
- Refactoring an existing prompt that produces inconsistent output.

## When NOT to use
- Sending raw user input to a frontier API (Anthropic, OpenAI) — those handle freestyle fine, optimize for cost not quality.
- Embedding/retrieval logic — that's a different concern.

## The Six Techniques

### 1. Decompose, don't ask big questions

❌ Bad: "Write a marketing plan for our new SaaS product."

✓ Good: Run three calls in sequence:
1. "List 5 target customer segments for a SaaS product with these features: [...]"
2. "For segment {X}, list 3 specific pain points this product addresses."
3. "Write a 3-paragraph email pitch addressing pain point {Y} for segment {X}."

Each call is small enough that a 3B model handles it well. The orchestrator stitches.

**Rule of thumb:** if a prompt asks for more than one kind of output (analysis + plan + write-up), split it.

### 2. Structure beats freestyle — use JSON mode

Ollama supports `format: "json"`. Use it for any non-prose output:

```python
req = ChatRequest(
    messages=[
        {"role": "system", "content": "You are a strict JSON generator. Output ONLY valid JSON, no preamble."},
        {"role": "user", "content": f"Classify this text into one of: bug, feature, question, other. Text: {text}\n\nReturn: {{\"category\": \"...\", \"confidence\": 0-1}}"}
    ],
    model="kimi-k2.6:cloud",
    response_format={"type": "json_object"},
    temperature=0.1,  # low for structured tasks
)
```

For more complex schemas, provide a JSON Schema in the system prompt and validate output with Pydantic. Retry on validation failure (max 2 retries).

### 3. Retrieve, then ask

A 3B model with the right 1KB of context outperforms an 8B model guessing. Always:
1. Embed the query.
2. Retrieve top-K (K=3-5) relevant chunks from Qdrant.
3. Insert as `system` or `user` message before the actual question.

Template:
```
SYSTEM: You answer based ONLY on the CONTEXT below. If the answer is not in CONTEXT, say "I don't know based on the provided information."

CONTEXT:
[chunk 1]
---
[chunk 2]
---
[chunk 3]

USER: <actual question>
```

The "say I don't know" instruction is the single biggest hallucination reducer for small models.

### 4. Critic loop — three passes for the price of one

For tasks where quality matters (writing, code, analysis), use draft → critique → revise:

```python
async def quality_response(user_request: str) -> str:
    # Pass 1: Draft (fast, cheap)
    draft = await llm.complete(
        f"Write a draft response to: {user_request}\n\nKeep it concise."
    )

    # Pass 2: Critique (specific, structured)
    critique = await llm.complete(
        f"Critique this response. List up to 3 specific issues. Be concrete.\n\n"
        f"Request: {user_request}\n\nResponse: {draft}\n\n"
        f"Output JSON: {{\"issues\": [\"...\", \"...\"]}}",
        response_format={"type": "json_object"},
    )

    issues = json.loads(critique)["issues"]
    if not issues:
        return draft

    # Pass 3: Revise
    revised = await llm.complete(
        f"Revise the response to address these specific issues: {issues}\n\n"
        f"Original request: {user_request}\n\nDraft: {draft}\n\nRevised:"
    )
    return revised
```

On RTX 3050M with `qwen2.5:3b`, three passes ≈ 6-10 seconds. Quality jump is large.

### 5. Few-shot for behavior shaping (3 examples beats 100 words of instruction)

A small model follows examples better than abstract rules.

❌ Verbose, ineffective:
```
SYSTEM: You should be concise but thorough. Avoid excessive caveats. Don't apologize. Get to the point. Don't restate the question. Use plain language. Avoid jargon unless...
```

✓ Few-shot, effective:
```
SYSTEM: Answer briefly and directly. Examples:

Q: What is the capital of France?
A: Paris.

Q: How do I reverse a string in Python?
A: `s[::-1]`

Q: Should I use SQLite or PostgreSQL?
A: SQLite for single-user/embedded; PostgreSQL for everything else.

Q: <user's actual question>
A:
```

### 6. Offload to skills, not to the model

If the task is deterministic, the LLM should not do it.

❌ Bad: "Calculate 23.7% of $4582 plus tax of 8%"
✓ Good: LLM produces `{"action": "calculate", "expression": "4582 * 0.237 * 1.08"}`, the skill executor runs it, result fed back to LLM for narration.

❌ Bad: "What's the weather in Jakarta?"
✓ Good: LLM produces `{"action": "weather", "location": "Jakarta"}`, skill calls API, result narrated.

The model's job is **routing and narrating**, not computing.

## Model Choice on 4GB VRAM

Recommended primary models (Q4_K_M quantization):

| Model | Size | Best for |
|---|---|---|
| `kimi-k2.6:cloud` | ~2.0GB | Default. Strong instruction following, good JSON mode. |
| `llama3.2:3b-instruct-q4_K_M` | ~2.0GB | Backup. Better at long-form prose. |
| `phi3.5:3.8b-mini-instruct-q4_K_M` | ~2.4GB | Code tasks. |
| `nomic-embed-text` | ~300MB CPU | Embeddings only. Run on CPU. |

**Never load two LLMs at once.** Use Ollama's `keep_alive: "1m"` to evict idle models quickly.

## Temperature Cookbook

| Task | Temperature |
|---|---|
| Classification, extraction, JSON | 0.0 - 0.2 |
| Code generation | 0.1 - 0.3 |
| Q&A from retrieved context | 0.2 - 0.4 |
| General chat | 0.5 - 0.7 |
| Brainstorming, creative writing | 0.7 - 0.9 |

Default: 0.4. Tune from there.

## System Prompt Template (Chat Mode)

```
You are Rain, a local AI assistant running on the user's own machine.

Behavior:
- Answer directly. Lead with the answer, then explain.
- If you don't know, say so. Do not invent facts.
- For code, output runnable code first, then a brief explanation.
- For lists of more than 3 items, use a bulleted list.
- Match the user's language (English/Indonesian).

Available tools: {tool_list}
When you want to use a tool, output ONLY: {{"tool": "name", "args": {...}}}
```

Keep it under 200 words. Long system prompts confuse small models.

## Quality bar
- Every prompt template lives in code (a constant or template file), not inline strings scattered across handlers.
- Every prompt has a corresponding test that asserts on output structure (not exact content).
- Temperature is set explicitly per call site, never default.
- JSON-mode outputs are validated with Pydantic; retry on failure.
- Decomposed flows have a planner unit test that mocks each LLM call.

## Anti-patterns
- ❌ One mega-prompt asking for analysis + plan + write-up + summary.
- ❌ Free-text output for downstream programmatic consumption (use JSON mode).
- ❌ Same temperature for all tasks.
- ❌ Letting the model do arithmetic, date math, or unit conversion.
- ❌ Vague system prompts ("be helpful, be concise, be friendly...").
- ❌ Skipping the critic loop because "the draft was probably fine."
