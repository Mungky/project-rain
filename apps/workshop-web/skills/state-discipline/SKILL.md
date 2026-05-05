---
name: state-discipline
description: Use this skill when the Frontend Agent needs to decide where a piece of state lives — useState, Zustand, TanStack Query, URL, or React context. Triggers when adding any stateful logic, refactoring a component that has grown messy, or debugging "why is this component re-rendering so often?". Enforces the boundaries that prevent the codebase from sliding into a tangled state mess.
---

# Skill: state-discipline
## The Five Buckets of State

Every piece of state in Rain belongs in exactly one of these:

| Bucket | Where | Examples |
|---|---|---|
| **Server state** | TanStack Query | conversations, messages, models list, health, skills list |
| **URL state** | `useSearchParams`, `useParams` | current conversationId, current view filter, modal open flag (sometimes) |
| **Global UI state** | Zustand | sidebar open, theme preference, selected model in composer, current Work Mode run being viewed |
| **Local component state** | `useState` | controlled input value within a single component, hover state, expanded/collapsed of one card |
| **Derived state** | `useMemo` or compute inline | filtered list, sum of token counts, formatted timestamps |

If you can't figure out which bucket a piece of state belongs in, you probably have two pieces of state masquerading as one. Split it.

## When to use this skill
- Adding any stateful logic.
- A component is re-rendering when it shouldn't.
- Two components keep getting out-of-sync state.
- You're tempted to lift state "just one more level."
- A component has 6+ `useState` calls.

## When NOT to use
- Pure functions, presentational components — no state to discipline.

## TanStack Query: server state ONLY

If the data lives on the server, it goes in TanStack Query. Period.

```ts
// hooks/use-conversations.ts
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import type { components } from "@/lib/api-types";

type Conversation = components["schemas"]["ConversationResponse"];

export const conversationKeys = {
  all: ["conversations"] as const,
  list: () => [...conversationKeys.all, "list"] as const,
  detail: (id: string) => [...conversationKeys.all, "detail", id] as const,
};

export function useConversations() {
  return useQuery({
    queryKey: conversationKeys.list(),
    queryFn: () => apiGet<Conversation[]>("/v1/conversations"),
  });
}
```

**Conventions:**
- `queryKey` factories live next to the hook, exported. Reuse them — never build `["conversations", id]` ad-hoc.
- Mutations use `useMutation` with `onSuccess: invalidateQueries(...)`.
- Optimistic updates via `setQueryData` for snappy UX (see `streaming-chat-ui` skill).
- `staleTime` is set globally to 30s in the QueryClient, override per-query as needed.

**Forbidden:** copying server data into Zustand or `useState`. The moment you do, you have two sources of truth.

## Zustand: global client UI state ONLY

If the data is client-only AND needs to be shared across components, Zustand.

```ts
// stores/ui-store.ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface UIState {
  sidebarOpen: boolean;
  selectedModel: string | null;
  theme: "light" | "dark" | "system";

  toggleSidebar: () => void;
  setSelectedModel: (model: string | null) => void;
  setTheme: (theme: UIState["theme"]) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      selectedModel: null,
      theme: "system",

      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setSelectedModel: (model) => set({ selectedModel: model }),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "rain-ui",
      storage: createJSONStorage(() => localStorage),
      version: 1,
      migrate: (persisted: any, version: number) => {
        // handle schema upgrades here when the shape changes
        if (version === 0) {
          return { ...persisted, theme: "system" };
        }
        return persisted;
      },
    },
  ),
);
```

**Conventions:**
- One store per concern (`useUIStore`, `useComposerStore`, etc.). NOT one giant `useStore` for everything.
- Persist only what should survive reload. Sidebar state? Yes. In-flight mutation? No.
- ALWAYS set `version` and implement `migrate`. Without it, the next time you change shape, users see white screens.
- Selectors at the call site, never broad reads:
  ```ts
  // ❌ Bad — re-renders on ANY change
  const store = useUIStore();
  // ✓ Good — re-renders only when sidebarOpen changes
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  ```
- For multiple values, use `shallow` comparison:
  ```ts
  import { useShallow } from "zustand/react/shallow";
  const { theme, sidebarOpen } = useUIStore(
    useShallow((s) => ({ theme: s.theme, sidebarOpen: s.sidebarOpen })),
  );
  ```

**Forbidden:** copying server data into Zustand. If you find yourself writing `setConversations(data)` in a query's `onSuccess`, you've taken a wrong turn — let TanStack Query own that data.

## URL state: when shareable / refresh-survivable matters

For state that should:
- Survive page refresh
- Be linkable / shareable (URL bar)
- Be navigable via browser back/forward

→ URL state.

```tsx
"use client";
import { useSearchParams, useRouter, usePathname } from "next/navigation";

function FilterBar() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const filter = searchParams.get("filter") ?? "all";

  const setFilter = (next: string) => {
    const sp = new URLSearchParams(searchParams);
    sp.set("filter", next);
    router.replace(`${pathname}?${sp.toString()}`);
  };

  return <select value={filter} onChange={(e) => setFilter(e.target.value)}>...</select>;
}
```

**For Rain specifically:**
- Current conversation ID → URL (it's `/chat/[conversationId]`)
- Selected agent run in Work Mode → URL (`/work/[runId]`)
- Filters or pagination on a list view → URL search params
- "Settings modal open" → probably URL search param too (`?settings=1`) so back button closes it

## useState: local component state

For state that:
- Doesn't need to be shared across components
- Doesn't need to survive unmount

→ `useState`.

```tsx
function CollapsibleCard() {
  const [expanded, setExpanded] = useState(false);
  return (
    <div onClick={() => setExpanded((e) => !e)}>
      {expanded ? <FullView /> : <Summary />}
    </div>
  );
}
```

**Red flags that mean you should NOT be using `useState`:**
- You're passing `setX` down two or more levels via props → lift to Zustand or use context.
- Multiple sibling components need to read the same value → lift.
- The value should survive unmount (e.g., user types, closes the page, comes back) → URL or Zustand-persist.

## Derived state: don't store, compute

```tsx
// ❌ Bad — derived state stored in useState, can fall out of sync
const [conversations, setConversations] = useState(...);
const [activeCount, setActiveCount] = useState(0);
useEffect(() => {
  setActiveCount(conversations.filter((c) => !c.deleted_at).length);
}, [conversations]);

// ✓ Good — compute inline (or memoize if expensive)
const activeCount = useMemo(
  () => conversations.filter((c) => !c.deleted_at).length,
  [conversations],
);
```

If it can be derived from existing state, derive it. Don't store it. Stored derived state is the #1 source of out-of-sync bugs.

## Context: the "I need DI but rarely changing" case

React Context is for values that:
- Many components need
- Rarely change (changing causes ALL consumers to re-render)
- Are "ambient" — feature flags, current user, theme

For Rain: `next-themes` already provides theme via context. We don't add more contexts unless we have to. Zustand handles the "many components need this" case better for things that change.

## Re-render audit checklist

When a component re-renders too often:

1. Is it consuming a Zustand store with a broad selector? → narrow it.
2. Is it inside a context whose value changes often? → split the context.
3. Is its parent passing a fresh object/array as prop every render? → memoize the prop or `React.memo` the child.
4. Is a TanStack Query refetching when it shouldn't? → check `staleTime` and `refetchOnWindowFocus`.
5. Is it inside a `useEffect` chain that triggers itself? → restructure.

## Common patterns

### Composer draft (where does the text live?)
- Single-component? `useState` in Composer.
- Need to clear from outside (e.g., when conversation switches)? → Zustand `useComposerStore` keyed by conversation, with a clear action.

### "Currently selected model"
- Same model across the whole session? → Zustand `useUIStore`.
- Different per-conversation? → URL or Zustand keyed by conversation.

### "Conversation list with optimistic new conversation"
- Conversations are server state → TanStack Query.
- Adding a new one → mutation with `onMutate` for optimistic update, `onSuccess` for invalidate.
- DON'T copy the list into Zustand to "manage it more easily."

### "Streaming assistant message"
- It's server-derived but live-updating → still TanStack Query, mutated via `setQueryData` as tokens arrive (see `streaming-chat-ui`).

## Quality bar
- Every store has a clear, narrow purpose. No mega-stores.
- Persisted Zustand stores have a `version` and a `migrate` function.
- Selectors are narrow. Components subscribe to the smallest slice they need.
- No `useState` is duplicating data already in TanStack Query or Zustand.
- No derived state stored — always computed.

## Anti-patterns
- ❌ Copying server data into Zustand or `useState`.
- ❌ One giant `useStore` with everything in it.
- ❌ Broad selectors (`const store = useStore()`) causing thrashing re-renders.
- ❌ Persisting in-flight UI state to localStorage.
- ❌ Reaching for context to share Zustand-able state.
- ❌ `useState` for things that should live in the URL.
- ❌ `useEffect` chains to keep two pieces of state in sync (sign you should derive instead).
