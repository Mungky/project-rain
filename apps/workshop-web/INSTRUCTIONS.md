# INSTRUCTIONS.md — Frontend Agent

## Required Reading Before You Touch a Component
1. `/PRD.md` — full
2. `/CONTRACTS.md` — Contracts 1, 2, 8 are your input surface
3. `/frontend/SYSTEM_PROMPT.md`
4. This file
5. The latest WO in `/frontend/INBOX/`

## Your Folder Layout (build it as you go)

```
/frontend
├── INBOX/                          # WOs from Parent land here
├── README.md                       # dev, build, test, deploy
├── package.json
├── pnpm-lock.yaml                  # use pnpm, not npm
├── next.config.ts
├── tsconfig.json                   # strict mode mandatory
├── tailwind.config.ts
├── postcss.config.mjs
├── .env.local.example
├── public/
│   └── rain-logo.svg
├── src/
│   ├── app/                        # Next.js App Router
│   │   ├── layout.tsx              # Root layout, theme provider, query client
│   │   ├── page.tsx                # Landing → redirect to /chat
│   │   ├── chat/
│   │   │   ├── layout.tsx          # Sidebar + main
│   │   │   ├── page.tsx            # New conversation
│   │   │   └── [conversationId]/
│   │   │       └── page.tsx        # Existing conversation
│   │   ├── work/                   # Phase 3
│   │   │   └── [runId]/page.tsx
│   │   └── api/                    # Edge handlers if needed (rare)
│   ├── components/
│   │   ├── ui/                     # shadcn primitives, Rain-themed
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   └── ...
│   │   ├── chat/
│   │   │   ├── message-list.tsx
│   │   │   ├── message-bubble.tsx
│   │   │   ├── composer.tsx
│   │   │   ├── streaming-indicator.tsx
│   │   │   └── conversation-sidebar.tsx
│   │   ├── work/                   # Phase 3
│   │   │   ├── agent-graph.tsx
│   │   │   └── task-card.tsx
│   │   ├── system/
│   │   │   ├── health-badge.tsx
│   │   │   └── model-picker.tsx
│   │   └── identity/
│   │       ├── rain-backdrop.tsx   # animated rain motif (subtle)
│   │       └── glass-panel.tsx     # core glassmorphism wrapper
│   ├── lib/
│   │   ├── api-client.ts           # fetch wrapper with base URL, errors
│   │   ├── api-types.ts            # GENERATED — never edit by hand
│   │   ├── sse.ts                  # SSE consumer for chat streams
│   │   ├── ws.ts                   # WebSocket helper (Phase 3)
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── use-conversations.ts    # TanStack Query
│   │   ├── use-conversation.ts
│   │   ├── use-send-message.ts     # streams via SSE
│   │   ├── use-health.ts
│   │   └── use-models.ts
│   ├── stores/
│   │   ├── ui-store.ts             # Zustand: sidebar open, theme, model selected
│   │   └── composer-store.ts       # Zustand: draft text, attachments
│   ├── styles/
│   │   ├── globals.css             # Tailwind layers + theme tokens
│   │   └── motion.ts               # framer variants reused everywhere
│   └── tests/
│       ├── components/
│       └── e2e/                    # Playwright
└── e2e/
    ├── playwright.config.ts
    └── chat.spec.ts
```

## Skills You Have Loaded
See `/frontend/skills/`. Currently:
- `rain-visual-identity` — typography, color, motion, glassmorphism rules
- `streaming-chat-ui` — SSE consumption, optimistic UI, message rendering
- `nextjs-app-router-patterns` — server vs client components, layouts, suspense
- `state-discipline` — Zustand vs TanStack Query boundaries

## Standard Operating Procedures

### SOP-1: Implementing a New Feature
1. Read the WO. Identify which Backend endpoints it depends on.
2. Run `pnpm openapi:gen` to ensure types are current.
3. Write the data hook (TanStack Query or custom for SSE) in `/hooks/`.
4. Write the components in `/components/<domain>/`.
5. Wire into a route in `/app/`.
6. Add a component test for any non-trivial logic.
7. Add or update an E2E test for the user-visible happy path.
8. Run `pnpm lint && pnpm typecheck && pnpm test && pnpm e2e`.
9. CHANGELOG entry. Mark WO complete.

### SOP-2: Consuming a New Endpoint
1. Backend's WO completion notice tells you the endpoint is live.
2. `pnpm openapi:gen` (script: `openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts`).
3. Use the generated types directly:
   ```ts
   import type { paths } from "@/lib/api-types";
   type ListResponse = paths["/v1/conversations"]["get"]["responses"]["200"]["content"]["application/json"];
   ```
4. Wrap in a TanStack Query hook in `/hooks/`.

### SOP-3: Streaming a Chat Response (the critical path)
Use the SSE helper. Pattern:
```ts
// hooks/use-send-message.ts
export function useSendMessage(conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (content: string) => {
      const stream = sseStream(`/v1/conversations/${conversationId}/messages`, {
        method: "POST",
        body: { content },
      });
      let buffered = "";
      for await (const chunk of stream) {
        if (chunk.type === "token") {
          buffered += chunk.data as string;
          // optimistic-update the messages cache so UI re-renders
          queryClient.setQueryData(["conversation", conversationId], (old) =>
            applyStreamingToken(old, buffered)
          );
        }
        if (chunk.type === "done") return chunk.data;
        if (chunk.type === "error") throw new Error(chunk.data.message);
      }
    },
  });
}
```
Composer calls this on submit. Message list re-renders on each token. Result feels live.

### SOP-4: Adding a Component
- One file per component. Same name as the file.
- Props are a typed `interface ComponentNameProps`.
- No default exports for components — named exports only.
- If the component uses client APIs (hooks, browser-only), `"use client"` at the top.
- If it can be a Server Component, it should be (default in App Router).

### SOP-5: Phase 1 Walking Skeleton — Build Order
This is your Phase 1 execution sequence. Backend Agent's endpoints land in this order; you wire each as it arrives.

1. `package.json`, configs, base styles, theme tokens.
2. Root `layout.tsx` with QueryClientProvider, theme, fonts.
3. `glass-panel.tsx` and `rain-backdrop.tsx` — establish identity early.
4. `lib/api-client.ts` — fetch wrapper with error handling.
5. `hooks/use-health.ts` + `health-badge.tsx` — proves connectivity to Backend.
6. `chat/page.tsx` skeleton with sidebar + main layout.
7. `hooks/use-conversations.ts` + `conversation-sidebar.tsx`.
8. `[conversationId]/page.tsx` + `message-list.tsx` + `message-bubble.tsx`.
9. `composer.tsx` — input + send button.
10. `lib/sse.ts` — SSE consumer.
11. `hooks/use-send-message.ts` — wires composer to backend.
12. E2E test: open app → see existing conversation or create new → send "hi" → see response stream in.

## State management discipline (Zustand vs TanStack Query)

**TanStack Query** owns ALL server data:
- conversations list
- messages within a conversation
- available models
- health status
- skills list (Phase 2+)

**Zustand** owns ALL client UI state:
- sidebar open/closed
- selected model in composer
- composer draft text
- theme variant
- which agent task is expanded in Work Mode (Phase 3)

If you find yourself reaching for `useState` for anything that crosses component boundaries, it goes in Zustand.

If you find yourself caching server data in Zustand, you're doing it wrong — that's TanStack Query's job.

## TypeScript discipline
- `tsconfig.json` has `"strict": true` AND `"noUncheckedIndexedAccess": true`.
- No `any`. Use `unknown` and narrow.
- Branded types for IDs:
  ```ts
  type ConversationId = string & { __brand: "ConversationId" };
  ```
- Enums via `as const` objects, not TypeScript `enum`.

## Testing discipline
- Component tests for: anything with branching logic, hooks, complex render.
- Skip tests for: pure presentational components with no logic (dumb wrappers).
- E2E for every user-visible happy path. One per major feature minimum.
- Mock fetch for component tests (msw or vi.fn). Real fetch in E2E.

## Performance budget
- First Load JS for `/chat` route: < 200KB gzipped.
- Time to interactive on a fresh load: < 1.5s on a midrange laptop.
- Streaming first byte to first rendered token: < 250ms.

## Quality bar
- `pnpm lint` clean.
- `pnpm typecheck` clean (strict mode).
- All component tests green.
- All E2E green.
- No console errors/warnings in dev.
- Lighthouse Performance score ≥ 85 on `/chat`.

## Anti-patterns
- ❌ Using `any` to ship faster.
- ❌ Hand-writing API response types.
- ❌ Caching server data in Zustand.
- ❌ Hardcoded color values (`#1a2b3c`) — use Tailwind theme tokens.
- ❌ `localStorage` writes without a try/catch and a schema version.
- ❌ Animations on scroll (jank). Animate transforms and opacity only.
- ❌ Big component libraries (Material, Ant) — they fight Tailwind.
- ❌ `useEffect` for things that could be derived state or event handlers.

## When Stuck
1. Re-read the WO and the relevant Contract.
2. Check shadcn/ui docs for a primitive before building from scratch.
3. If Backend hasn't shipped what you need, write a WO request to Parent. Don't fake data shapes.
