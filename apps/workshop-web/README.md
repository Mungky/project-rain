# Rain Frontend

The Next.js 16 web interface for Project Rain — a Local AI Operating System.

## Quick Start

### Prerequisites

- **Node.js** 18+ (LTS recommended)
- **pnpm** 9+ (`npm install -g pnpm`)
- **Backend** running on `http://localhost:8000` (or set `NEXT_PUBLIC_API_BASE_URL`)

### Installation

```bash
cd frontend
pnpm install
```

### Configuration

Copy the example environment file and adjust if needed:

```bash
cp .env.local.example .env.local
```

The defaults point to `http://localhost:8000`, which matches the Backend Agent's dev server.

### Development

```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) — you'll be redirected to `/chat`.

### Other Commands

| Command | Description |
|---|---|
| `pnpm dev` | Start dev server |
| `pnpm build` | Production build |
| `pnpm start` | Start production server |
| `pnpm lint` | Run ESLint |
| `pnpm typecheck` | Run TypeScript type checker |
| `pnpm test` | Run unit/component tests (Vitest) |
| `pnpm test:watch` | Run tests in watch mode |
| `pnpm e2e` | Run Playwright E2E tests |
| `pnpm openapi:gen` | Regenerate API types from Backend OpenAPI schema |

### API Type Generation

When the Backend adds or changes endpoints, regenerate the typed API client:

```bash
pnpm openapi:gen
```

This fetches the OpenAPI schema from `http://localhost:8000/openapi.json` and writes `src/lib/api-types.ts`. Never edit this file by hand.

## Architecture

- **Next.js 16 App Router** — Server Components by default, Client Components only where needed
- **Tailwind CSS 4** — Utility-first styling with Rain theme tokens
- **Zustand** — Client UI state (sidebar, theme, draft)
- **TanStack Query 5** — Server data (conversations, messages, health, models)
- **Framer Motion** — Fluid transitions (only transforms & opacity)
- **Vitest + Testing Library** — Component tests
- **Playwright** — End-to-end tests

### Folder Structure

```
src/
├── app/                    # Next.js App Router pages & layouts
├── components/
│   ├── ui/                 # Primitive components (Button, Input, …)
│   ├── chat/               # Chat-specific components
│   ├── system/             # System status components
│   └── identity/           # Rain visual identity (RainBackdrop, GlassPanel)
├── hooks/                  # TanStack Query hooks & custom hooks
├── lib/                    # Utilities, API client, SSE consumer, types
├── stores/                 # Zustand stores
└── styles/                 # Global CSS, motion variants
```

## Visual Identity

Rain uses a deep blue/slate palette with glassmorphism effects. Every surface is rendered through `<GlassPanel>`. The animated `<RainBackdrop>` provides the signature rain-motif background on the chat page.

See `/skills/rain-visual-identity/SKILL.md` for the full design system.

## State Discipline

- **Server data** → TanStack Query (never Zustand)
- **Global UI state** → Zustand stores with narrow selectors
- **Local component state** → `useState`
- **URL state** → `useSearchParams` / route params

See `/skills/state-discipline/SKILL.md` for detailed rules.

## Starting Your First Chat

1. Make sure the Backend is running at `http://localhost:8000` (or set `NEXT_PUBLIC_API_BASE_URL` in `.env.local`).
2. Start the dev server: `pnpm dev`
3. Open [http://localhost:3000](http://localhost:3000) — you'll be redirected to `/chat`.
4. Click **New Chat** in the sidebar to create a conversation.
5. Type a message in the composer at the bottom and press **Ctrl/Cmd + Enter** (or click **Send**).
6. The assistant's response will stream in token-by-token in real-time.
7. Press **Esc** or click **Stop** to abort a streaming response.
8. Conversations persist in the sidebar. Click any to resume, or click the delete icon to remove it.

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl/Cmd + Enter` | Send message |
| `Esc` | Cancel streaming response |