---
name: nextjs-app-router-patterns
description: Use this skill when the Frontend Agent is working with the Next.js App Router structure — layouts, pages, server vs client components, suspense boundaries, route handlers, or metadata. Triggers on any new file in /app/, on layout refactors, on Suspense/loading boundary decisions, and when deciding "should this be a Server Component or Client Component?".
---

# Skill: nextjs-app-router-patterns

## Purpose
Use Next.js 16's App Router idiomatically. Get the server/client component boundary right (perf, bundle size, hydration cost). Use layouts for shared shell. Use Suspense for streaming. Don't accidentally turn the whole app into a client-side bundle.

## When to use
- Adding any file under `/app/`.
- Choosing between Server Component (default) and Client Component.
- Designing layouts and route groups.
- Setting up loading.tsx / error.tsx / not-found.tsx.
- Adding metadata for SEO (even though Rain is a local app, good metadata is still useful).

## When NOT to use
- Pure component design (no routing involved) → just write the component.
- API consumption → use TanStack Query hooks.

## Core mental model

**Server Component (default):**
- Runs at request time on the server (or build time if static).
- Cannot use hooks, state, event handlers, browser APIs.
- Can `await` anything.
- Zero JS shipped to client (huge perf win).

**Client Component (`"use client"` directive):**
- Runs on both server (initial HTML) and client (hydration + interactivity).
- Can use hooks, state, effects, refs, browser APIs.
- All its imports become part of the client bundle.

**Decision rule:** Default to Server Component. Reach for Client only when you need: `useState`, `useEffect`, event handlers, browser APIs, third-party libs that use any of those, or context providers that wrap interactivity.

**The leaf rule:** push `"use client"` to the leaves, not the trunk. A Server Component can render Client Components — but a Client Component cannot import a Server Component (unless passed as `children`).

## Folder layout for Rain

```
src/app/
├── layout.tsx                     # Root layout — providers (QueryClient, Theme), html shell
├── page.tsx                       # → redirect to /chat
├── globals.css
├── loading.tsx                    # Default loading shell
├── error.tsx                      # Root error boundary
├── not-found.tsx
├── chat/
│   ├── layout.tsx                 # Sidebar + main grid; shared across all /chat/*
│   ├── page.tsx                   # /chat — empty state, "start a conversation"
│   ├── loading.tsx                # /chat-specific skeleton
│   └── [conversationId]/
│       ├── page.tsx               # /chat/{id} — message thread
│       └── loading.tsx
├── work/                          # Phase 3
│   ├── layout.tsx
│   └── [runId]/
│       └── page.tsx
└── api/                           # ONLY if absolutely needed (rare — backend is FastAPI)
    └── ...
```

## Root layout pattern

`src/app/layout.tsx` (Server Component):

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Rain",
  description: "Local AI Operating System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-ink-50 dark:bg-ink-950 text-ink-900 dark:text-ink-100 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

`src/app/providers.tsx` (Client Component — wraps the app in providers):

```tsx
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: 1,
      },
    },
  }));

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </ThemeProvider>
  );
}
```

**Why split:** RootLayout stays a Server Component (no JS overhead for the shell). Providers is a Client Component because providers use context and hooks.

## Chat layout pattern

`src/app/chat/layout.tsx` (can be Server Component if sidebar is server-rendered):

```tsx
import { ConversationSidebar } from "@/components/chat/conversation-sidebar";
import { GlassPanel } from "@/components/identity/glass-panel";
import { RainBackdrop } from "@/components/identity/rain-backdrop";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <RainBackdrop />
      <div className="relative grid grid-cols-[280px_1fr] gap-4 h-screen p-4">
        <GlassPanel className="overflow-hidden">
          <ConversationSidebar />
        </GlassPanel>
        <main className="flex flex-col min-h-0">
          {children}
        </main>
      </div>
    </div>
  );
}
```

`ConversationSidebar` is a Client Component (it uses TanStack Query). `GlassPanel` is a Server Component (no interactivity). The layout itself stays a Server Component.

## Page pattern

`src/app/chat/[conversationId]/page.tsx`:

```tsx
import { ChatThread } from "@/components/chat/chat-thread";

interface Params {
  conversationId: string;
}

export default async function ConversationPage({ params }: { params: Promise<Params> }) {
  const { conversationId } = await params;
  return <ChatThread conversationId={conversationId} />;
}
```

`ChatThread` is a Client Component (uses hooks). The page itself is a Server Component (just a thin wrapper unwrapping params).

**Note:** Next.js 15+ makes `params` a Promise. Always `await` it.

## Suspense and loading.tsx

A `loading.tsx` adjacent to `page.tsx` becomes the React Suspense fallback while the page's data resolves.

`src/app/chat/[conversationId]/loading.tsx`:

```tsx
export default function Loading() {
  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="h-8 w-2/3 rounded-md bg-ink-200/50 dark:bg-ink-700/50 animate-pulse" />
      <div className="h-20 rounded-xl bg-ink-200/50 dark:bg-ink-700/50 animate-pulse" />
      <div className="h-20 rounded-xl bg-ink-200/50 dark:bg-ink-700/50 animate-pulse" />
    </div>
  );
}
```

Skeletons follow the actual layout shape — not generic spinners. Pulse, don't shimmer (calmer).

## Error boundaries

`src/app/error.tsx`:

```tsx
"use client";  // error.tsx must be a Client Component

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-8">
      <h2 className="text-xl font-semibold">Something went wrong.</h2>
      <p className="text-ink-500 max-w-md text-center">{error.message}</p>
      <button onClick={reset} className="px-4 py-2 rounded-lg bg-storm-500 text-ink-50">
        Try again
      </button>
    </div>
  );
}
```

Place a `error.tsx` at: root (catches everything), `/chat/error.tsx` (catches chat-specific errors so the rest of the app stays intact).

## Server vs Client decision flowchart

```
Does the component need:
  - useState / useReducer?           → Client
  - useEffect / useLayoutEffect?     → Client
  - Event handlers (onClick, etc)?   → Client
  - Browser APIs (localStorage, ...)? → Client
  - A library that uses any of above? → Client
  - React context (consumer)?         → Client (the consumer; provider can be inside a Client wrapper)
  - Otherwise?                        → Server (default)
```

**Common mistake:** marking a component Client just because it has children that are Client. NO. The Server component renders fine; only the leaves go Client.

## Static-rendered routes

Rain's content is per-user/dynamic, so most routes are dynamic. But some can be static:

- `/` (the redirect-to-chat shell)
- `/about`, `/help` if they exist

For these: nothing special needed. Next.js statically renders Server Components that don't read dynamic data.

## Route handlers (only if needed)

Next.js can serve API routes at `/app/api/...`. **Avoid this for Rain** — Backend Agent is FastAPI. The only legit use:

- A thin proxy if CORS becomes a problem (it shouldn't, since both are localhost in dev).
- A WebSocket relay (no — Next.js App Router doesn't natively support WS handlers; use the FastAPI WS directly).

If you find yourself reaching for `/app/api/`, ask Parent Agent first. It usually means a contract is missing on the Backend side.

## Metadata

Even for a local app, set good metadata in layouts:

```tsx
export const metadata: Metadata = {
  title: { default: "Rain", template: "%s · Rain" },
  description: "Local AI Operating System",
  themeColor: "#0a1019",  // ink-950 for dark mode address bar
};
```

In dynamic routes:
```tsx
export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { conversationId } = await params;
  // Optionally fetch the conversation title
  return { title: `Conversation` };
}
```

## Streaming SSR

App Router supports streaming SSR. For Rain's chat page, this means: the layout (sidebar) renders immediately, the message thread streams in when its data is ready. Suspense boundaries are how you control the streaming chunks.

```tsx
import { Suspense } from "react";

export default function ChatPage() {
  return (
    <>
      <ChatHeader />                              {/* renders immediately */}
      <Suspense fallback={<MessageListSkeleton />}>
        <MessageThread />                         {/* streams in */}
      </Suspense>
    </>
  );
}
```

## Don't fight the App Router

Common temptations to resist:
- Putting `"use client"` at the top of layout.tsx "to be safe" — kills SSR perf.
- Fetching data in client components when you could fetch in a Server Component.
- Building a global store for things that are URL state (use the URL).

## Quality bar
- Default new components to Server Component until you need Client.
- `"use client"` at the leaves, not the trunk.
- Every async data path has a `loading.tsx` or `<Suspense>` boundary.
- Every route has an `error.tsx` somewhere up the tree.
- Metadata defined at the appropriate layout level.
- No `getServerSideProps` / `getStaticProps` (those are Pages Router; we're on App Router).

## Anti-patterns
- ❌ `"use client"` at the root layout.
- ❌ Fetching data in `useEffect` when a Server Component could await it.
- ❌ Marking a parent Client because a child is Client.
- ❌ Building API routes in `/app/api/` to proxy Backend (just call Backend directly).
- ❌ Returning `null` to "hide" loading instead of using Suspense.
- ❌ Ignoring the `params: Promise<...>` change in Next.js 15+.
