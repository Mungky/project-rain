---
name: streaming-chat-ui
description: Use this skill when the Frontend Agent is implementing or modifying the chat UI's streaming behavior — SSE consumption, optimistic updates, message rendering, the composer, or anything in the streaming critical path. Triggers on the Phase 1 chat skeleton, message bubble rendering, SSE error handling, and Phase 3 WebSocket consumption for Work Mode.
---

# Skill: streaming-chat-ui

## Purpose
The chat experience is the product's first impression. A 3B model on a 4GB GPU is fast enough to feel snappy IF the frontend is built right. The wrong implementation makes it feel like a slow LLM. The right implementation makes the same model feel real-time.

This skill encodes the streaming pipeline end to end.

## When to use
- Phase 1: building the chat page from scratch.
- Anywhere SSE is consumed.
- Phase 3: extending to WebSocket for Work Mode.
- Debugging "feels laggy" complaints about chat.

## When NOT to use
- Static, non-streaming UI elements → just use TanStack Query.
- Visual polish unrelated to streaming → use `rain-visual-identity` skill.

## Architectural overview

```
User types → Composer → useSendMessage mutation
                          ↓
                    POST /v1/conversations/{id}/messages
                          ↓
                    SSE response stream
                          ↓
              For each {type, data} chunk:
                "token"  → append to in-flight message buffer → setQueryData
                "tool_call" → render tool call card
                "done"   → replace in-flight with persisted message
                "error"  → show error toast, mark message as failed
                          ↓
                    Message list re-renders incrementally
```

## The SSE consumer

`/lib/sse.ts`:

```ts
import type { components } from "@/lib/api-types";

export type ChatChunk = components["schemas"]["ChatChunk"];

export interface SSEStreamOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

export async function* sseStream(
  url: string,
  opts: SSEStreamOptions = {},
): AsyncGenerator<ChatChunk, void, void> {
  const response = await fetch(url, {
    method: opts.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });

  if (!response.ok) {
    throw new Error(`SSE request failed: ${response.status}`);
  }
  if (!response.body) {
    throw new Error("SSE response has no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE messages end with \n\n
      let separatorIndex: number;
      while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);

        // Each event has lines starting with "data: "
        const dataLine = rawEvent
          .split("\n")
          .find((line) => line.startsWith("data: "));
        if (!dataLine) continue;
        const json = dataLine.slice("data: ".length);

        try {
          const chunk = JSON.parse(json) as ChatChunk;
          yield chunk;
        } catch (e) {
          console.error("Bad SSE chunk:", json);
          // Don't kill the stream — keep going
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
```

**Why a generator:** the consumer can `for await (const chunk of stream)` and naturally pause / cancel via AbortController.

**Why we don't use `EventSource`:** EventSource doesn't support POST requests with bodies. Backend's chat endpoint is POST.

## The send-message hook

`/hooks/use-send-message.ts`:

```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { sseStream, type ChatChunk } from "@/lib/sse";
import { conversationKeys } from "@/hooks/use-conversation";
import { apiUrl } from "@/lib/api-client";

interface SendMessageInput {
  conversationId: string;
  content: string;
  model?: string;
  signal?: AbortSignal;
}

export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ conversationId, content, model, signal }: SendMessageInput) => {
      // Optimistic: add the user message immediately
      const userMessageId = `tmp-user-${crypto.randomUUID()}`;
      queryClient.setQueryData(conversationKeys.detail(conversationId), (old: any) => ({
        ...old,
        messages: [
          ...(old?.messages ?? []),
          {
            id: userMessageId,
            role: "user",
            content,
            created_at: new Date().toISOString(),
          },
        ],
      }));

      // Add a placeholder assistant message that we'll fill as tokens arrive
      const assistantMessageId = `tmp-asst-${crypto.randomUUID()}`;
      queryClient.setQueryData(conversationKeys.detail(conversationId), (old: any) => ({
        ...old,
        messages: [
          ...(old?.messages ?? []),
          {
            id: assistantMessageId,
            role: "assistant",
            content: "",
            streaming: true,
            created_at: new Date().toISOString(),
          },
        ],
      }));

      let buffered = "";
      const stream = sseStream(apiUrl(`/v1/conversations/${conversationId}/messages`), {
        method: "POST",
        body: { content, model },
        signal,
      });

      for await (const chunk of stream) {
        if (chunk.type === "token") {
          buffered += chunk.data as string;
          // Mutate the assistant placeholder in place
          queryClient.setQueryData(conversationKeys.detail(conversationId), (old: any) => ({
            ...old,
            messages: old.messages.map((m: any) =>
              m.id === assistantMessageId ? { ...m, content: buffered } : m
            ),
          }));
        } else if (chunk.type === "done") {
          // Replace temp IDs with real ones from server
          await queryClient.invalidateQueries({
            queryKey: conversationKeys.detail(conversationId),
          });
          return chunk.data;
        } else if (chunk.type === "error") {
          queryClient.setQueryData(conversationKeys.detail(conversationId), (old: any) => ({
            ...old,
            messages: old.messages.map((m: any) =>
              m.id === assistantMessageId
                ? { ...m, content: buffered, streaming: false, error: (chunk.data as any).message }
                : m
            ),
          }));
          throw new Error((chunk.data as any).message);
        }
      }
    },
  });
}
```

**Key moves:**
1. Optimistic user message before the request — feels instant.
2. Placeholder assistant message with `streaming: true` flag — UI knows to show the streaming indicator.
3. Token chunks update the placeholder in-place (TanStack Query's setQueryData is fast).
4. On `done`, invalidate to fetch the canonical persisted state.
5. On `error`, freeze whatever was buffered, mark error, surface to user.

## The composer

`/components/chat/composer.tsx`:

```tsx
"use client";
import { useRef, useState } from "react";
import { useSendMessage } from "@/hooks/use-send-message";
import { Button } from "@/components/ui/button";
import { GlassPanel } from "@/components/identity/glass-panel";

interface ComposerProps {
  conversationId: string;
}

export function Composer({ conversationId }: ComposerProps) {
  const [draft, setDraft] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const { mutate, isPending } = useSendMessage();

  const send = () => {
    const content = draft.trim();
    if (!content || isPending) return;
    setDraft("");
    abortRef.current = new AbortController();
    mutate({ conversationId, content, signal: abortRef.current.signal });
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + Enter sends
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      send();
    }
    // Esc cancels in-flight stream
    if (e.key === "Escape" && isPending) {
      abortRef.current?.abort();
    }
  };

  return (
    <GlassPanel className="p-3 flex items-end gap-2">
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask Rain anything…"
        rows={1}
        className="flex-1 bg-transparent resize-none outline-none text-ink-900 dark:text-ink-100 placeholder:text-ink-400 max-h-40"
      />
      <Button onClick={send} disabled={isPending || !draft.trim()}>
        {isPending ? "Streaming…" : "Send"}
      </Button>
    </GlassPanel>
  );
}
```

**Key UX details:**
- Cmd/Ctrl+Enter sends (matches every modern chat UX).
- Esc aborts the in-flight stream (user controls).
- Textarea auto-grows up to a max-height (CSS, no JS).
- Send button disabled while pending — but composer remains editable so user can queue next message mentally.

## Message rendering

`/components/chat/message-list.tsx`:

```tsx
"use client";
import { useEffect, useRef } from "react";
import { MessageBubble } from "./message-bubble";

interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  streaming?: boolean;
  error?: string;
  created_at: string;
}

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll only if user is already near the bottom
  useEffect(() => {
    const el = bottomRef.current?.parentElement;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 200;
    if (nearBottom) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4" aria-live="polite">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

`/components/chat/message-bubble.tsx`:

```tsx
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { fadeUp, easeStandard } from "@/styles/motion";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="visible"
      transition={easeStandard}
      className={cn(
        "flex",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[85%] rounded-xl px-4 py-3 border",
          isUser
            ? "bg-warm-400/15 border-warm-400/30"
            : "bg-ink-100/40 dark:bg-ink-800/40 border-ink-200/40 dark:border-ink-700/40",
        )}
      >
        <MessageContent content={message.content} />
        {message.streaming && <StreamingDot />}
        {message.error && (
          <div className="mt-2 text-xs text-rose-500">{message.error}</div>
        )}
      </div>
    </motion.div>
  );
}

function StreamingDot() {
  return (
    <span
      className="inline-block ml-2 w-2 h-2 rounded-full bg-rain-400 animate-pulse"
      aria-label="Assistant is responding"
    />
  );
}
```

**MessageContent** renders markdown. Use `react-markdown` + `remark-gfm`. For code blocks, use `shiki` (no client-side bundle bloat — pre-rendered on-demand).

## Auto-scroll discipline

The hard rule: **auto-scroll only when the user is already at/near the bottom.** Never scroll-yank a user who has scrolled up to read.

The check above (`scrollHeight - scrollTop - clientHeight < 200`) handles this. 200px is the "near bottom" threshold.

## Performance

For long conversations (>100 messages):
- Virtualize the list with `@tanstack/react-virtual` (lightweight, hooks-based).
- Memoize `MessageBubble` with `React.memo` keyed on `message.id` and `message.content`.
- During streaming, only the last bubble re-renders (others are memoized).

Don't virtualize until message count > 50; the overhead isn't worth it for short chats.

## Cancellation (Phase 1 minimum)

User must be able to stop a runaway response:
- Esc key when composer is focused (already wired above).
- Stop button visible during `isPending`.
- AbortController cancels the fetch; the SSE generator's `finally` releases the reader.

Backend: should detect connection close and stop generating. Coordinate with Backend Agent that `request.is_disconnected()` is checked in the streaming loop.

## Phase 3: WebSocket for Work Mode

When Phase 3 lands, Work Mode uses WebSocket (not SSE) because the server pushes events not tied to a single response. Pattern:

```ts
// /lib/ws.ts
export function workModeSocket(runId: string) {
  const ws = new WebSocket(`${WS_URL}/ws/agent-runs/${runId}`);
  return new ReadableStream<{ event: string; data: unknown }>({
    start(controller) {
      ws.onmessage = (e) => controller.enqueue(JSON.parse(e.data));
      ws.onerror = (e) => controller.error(e);
      ws.onclose = () => controller.close();
    },
    cancel() { ws.close(); },
  });
}
```

The agent graph component subscribes, builds a node tree from events, animates nodes appearing.

## Quality bar
- First token visible to user within 250ms of submit.
- No janky scroll behavior during stream.
- Cancellation works (verify with network tab).
- aria-live region announces streaming responses to screen readers.
- Memoized message bubbles — only the actively-streaming one re-renders during a stream.

## Anti-patterns
- ❌ Re-fetching the entire conversation on every token.
- ❌ Auto-scroll that yanks the user when they've scrolled up.
- ❌ Blocking the UI during stream (no spinners covering the message).
- ❌ Discarding partial output on error (always show what was buffered before failure).
- ❌ Using `EventSource` (no POST body support).
- ❌ Polling for completion when streaming is available.
