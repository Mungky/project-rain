---
name: rain-visual-identity
description: Use this skill when the Frontend Agent is making any visual decision — color, typography, spacing, motion, component shape, layout. Triggers on every new component, every styling refactor, every animation. Defines and enforces the Rain identity (deep blue/slate palette, glassmorphism, fluid motion, calm typography) so the product feels coherent across screens.
---

# Skill: rain-visual-identity

## The Identity in One Sentence
Rain feels like watching a thunderstorm through a clean window from inside a warm room: powerful, quiet, organized, slightly mysterious.

## Core Principles
1. **Calm beats loud.** No bouncing. No bright reds. No screaming alerts. Important info is communicated through contrast and weight, not color saturation.
2. **Fluid, not snappy.** Transitions ease in and out (300-500ms). Snap behavior is reserved for direct manipulations (drag, click).
3. **Glass, not flat.** Surfaces have depth via translucency and subtle blur — but always with enough contrast to remain readable.
4. **Type carries the brand.** A single, well-spaced typeface family does most of the work. Decoration is restrained.
5. **Motion is meaning.** If something moves, it should communicate state change. Decorative motion is rare and slow.

## Color Tokens (Tailwind theme extension)

```ts
// tailwind.config.ts (excerpt)
export default {
  theme: {
    extend: {
      colors: {
        // Rain palette — deep blue / slate, with a touch of warmth on accents
        ink: {
          50: "#f6f8fb",
          100: "#e9eef5",
          200: "#cdd7e4",
          300: "#a3b2c7",
          400: "#6f829a",
          500: "#4c6079",
          600: "#3a4c63",
          700: "#2d3c50",
          800: "#1f2a3a",
          900: "#131b27",
          950: "#0a1019",
        },
        storm: {
          // accent — desaturated indigo
          400: "#7e8cf3",
          500: "#5b6ce0",
          600: "#4453c3",
          700: "#36419e",
        },
        rain: {
          // accent secondary — soft cyan, used for streaming indicators, highlights
          300: "#9bdfe7",
          400: "#5cc6d3",
          500: "#2faab9",
        },
        warm: {
          // sparingly — for user message bubbles, success states
          400: "#e3c391",
          500: "#c9a872",
        },
      },
    },
  },
};
```

**Usage rules:**
- Backgrounds: `ink-50` to `ink-200` (light mode), `ink-900` to `ink-950` (dark mode).
- Text on background: `ink-900` (light), `ink-100` (dark). Body text contrast ratio ≥ 7:1 (AAA).
- Primary interactive: `storm-500` / `storm-600`.
- Streaming, "thinking" states: `rain-400`.
- User messages get `warm-400` accent stripe (subtle warmth).
- NEVER use pure white (`#fff`) or pure black (`#000`) on backgrounds. Use `ink-50` / `ink-950`.
- Status colors when needed: green = `emerald-500`, error = `rose-500` (NOT `red-500` which is too aggressive). Use sparingly.

## Typography

Single typeface family: **Inter** (variable). It's free, modern, supports tabular nums for token counts.

```css
/* globals.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400..700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  --font-feature-settings: "cv11", "ss01", "tnum"; /* Inter calibrations */
}

body {
  font-family: var(--font-sans);
  font-feature-settings: var(--font-feature-settings);
}
```

**Type scale (rem):**

| Use | Size | Weight | Tracking |
|---|---|---|---|
| Display (rare) | 2.25 (36px) | 600 | -0.02em |
| H1 (page title) | 1.5 (24px) | 600 | -0.01em |
| H2 (section) | 1.25 (20px) | 600 | -0.01em |
| H3 (subsection) | 1.0625 (17px) | 600 | 0 |
| Body | 0.9375 (15px) | 400 | 0 |
| Small (meta, timestamps) | 0.8125 (13px) | 400 | 0.01em |
| Code | 0.875 (14px) mono | 400 | 0 |

Line height: 1.6 for body, 1.3 for headings, 1.5 for code.

## Glassmorphism — the core surface

Every "panel" in Rain is glass:

```tsx
// components/identity/glass-panel.tsx
interface GlassPanelProps {
  children: React.ReactNode;
  variant?: "default" | "elevated" | "subtle";
  className?: string;
}

export function GlassPanel({ children, variant = "default", className }: GlassPanelProps) {
  return (
    <div
      className={cn(
        "relative rounded-xl border backdrop-blur-xl",
        "bg-ink-50/60 dark:bg-ink-900/60",
        "border-ink-200/50 dark:border-ink-700/50",
        variant === "elevated" && "shadow-lg shadow-ink-900/5",
        variant === "subtle" && "bg-ink-50/30 dark:bg-ink-900/30",
        className,
      )}
    >
      {children}
    </div>
  );
}
```

**Rules for glass:**
- Never stack glass on glass on glass (max 2 levels — opacity compounds badly).
- Always combine with `border` (1px, slightly lighter than the surface) — pure glass without border looks unfinished.
- Backdrop blur: `backdrop-blur-xl` (24px). Don't go higher; it's expensive on lower-end GPUs.
- Provide a non-glass fallback for `prefers-reduced-transparency`.

## Layout / Spacing

Spacing scale follows Tailwind's default (4px base). Common values:

| Use | Token |
|---|---|
| Inline gap (tight) | `gap-1.5` (6px) |
| Inline gap (default) | `gap-3` (12px) |
| Stack gap (default) | `gap-4` (16px) |
| Section gap | `gap-8` (32px) |
| Page padding | `px-6 py-4` (mobile) → `px-10 py-6` (desktop) |
| Panel padding (default) | `p-5` (20px) |
| Panel padding (snug) | `p-3` (12px) |

**Border radius:**
- Buttons, small inputs: `rounded-lg` (8px)
- Panels: `rounded-xl` (12px)
- Hero / large surfaces: `rounded-2xl` (16px)
- Pills / tags / badges: `rounded-full`

## Motion

Use Framer Motion. Centralize variants in `/styles/motion.ts`:

```ts
// styles/motion.ts
import type { Variants, Transition } from "framer-motion";

// Standard transitions
export const easeStandard: Transition = { duration: 0.32, ease: [0.22, 1, 0.36, 1] };
export const easeQuick: Transition = { duration: 0.18, ease: [0.4, 0, 0.2, 1] };
export const easeSlow: Transition = { duration: 0.48, ease: [0.22, 1, 0.36, 1] };

// Common variants
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
};

export const fade: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

// Streaming token appearance
export const tokenAppear: Variants = {
  hidden: { opacity: 0, filter: "blur(2px)" },
  visible: { opacity: 1, filter: "blur(0)" },
};
```

**Motion rules:**
- Animate `transform` and `opacity` only. Never `width`, `height`, `top` (jank).
- Respect `prefers-reduced-motion` — wrap motion in a check, or use Framer's `useReducedMotion`.
- Page transitions: 300-400ms ease-out.
- Token streaming: 100-150ms fade per token. Subtle, almost subliminal.
- Skeleton loaders: gentle pulse, not flashy shimmer.

## The Rain Backdrop (signature element)

A subtle, animated background that gives the whole app its "rain" feeling. Implement once in `/components/identity/rain-backdrop.tsx`. Used on the chat page only.

Approach: a fixed-position canvas with sparse, slow-falling vertical lines (1-2px wide, low opacity, varying speed). Density: ~30-50 lines visible at a time. Color: `rain-400` at 8-12% opacity.

Performance: requestAnimationFrame, throttled to 30fps. Pause when tab is not visible (`document.visibilityState`). Disable entirely when `prefers-reduced-motion`.

This element ships in Phase 1 — it's the visual signature.

## Component patterns

### Buttons
- Primary: `bg-storm-500 hover:bg-storm-600 text-ink-50`
- Secondary: `border border-ink-300 bg-transparent hover:bg-ink-100 text-ink-800` (and dark variant)
- Ghost: `hover:bg-ink-100 text-ink-700`
- Always have visible focus ring (`focus-visible:ring-2 focus-visible:ring-storm-400`).
- Min height 36px (touch-friendly).

### Inputs
- Border: `border-ink-300 dark:border-ink-700`
- Focus: `focus:border-storm-500 focus:ring-1 focus:ring-storm-500`
- Background: glass-panel-style, `bg-ink-50/40 dark:bg-ink-900/40`
- Placeholder: `placeholder:text-ink-400`

### Message bubbles
- User message: right-aligned, `bg-warm-400/15 border border-warm-400/30`
- Assistant message: left-aligned, `bg-ink-100/40 dark:bg-ink-800/40 border border-ink-200/40 dark:border-ink-700/40`
- Avatar: storm-colored for assistant, warm-colored for user. Small, subtle.
- Timestamps: `text-xs text-ink-400`
- Code blocks inside messages: `bg-ink-950 text-ink-100 rounded-lg` (always dark, even in light mode — readability).

### Streaming indicator
While the assistant is streaming, show a small pulsing `rain-400` dot in the bubble's footer. NOT a "..." spinner — too generic.

## Dark mode
- Mandatory. Default: follow system.
- Toggle in user settings. Persist via Zustand → localStorage with version tag.
- Test every component in both modes.

## Accessibility
- Color contrast: AAA on body text (≥ 7:1). AA on UI components (≥ 3:1).
- Every interactive element has a visible focus state.
- All icons in interactive controls have an aria-label.
- Streaming responses are announced to screen readers via `aria-live="polite"` on the message container.
- Keyboard shortcuts:
  - `Ctrl/Cmd + Enter`: send message
  - `Ctrl/Cmd + K`: focus composer
  - `Ctrl/Cmd + N`: new conversation
  - `Esc`: cancel streaming response

## Quality bar
- Every new component uses theme tokens, not raw hex codes.
- Glass surfaces use `<GlassPanel>`, not ad-hoc backdrop-blur classes.
- Motion goes through shared variants where possible.
- Both light and dark modes look correct.
- `prefers-reduced-motion` and `prefers-reduced-transparency` are respected.

## Anti-patterns
- ❌ Bright primary colors (red, orange, hot pink) anywhere except destructive confirmations.
- ❌ Hard shadows (`shadow-2xl` with high opacity). Rain shadows are diffuse and small.
- ❌ Bouncy spring animations.
- ❌ Three layers of glass stacked.
- ❌ `<div className="bg-[#1a2b3c]">` — always token, never literal.
- ❌ Tailwind `gap-7`, `text-[17px]` — pick from the standard scale or add it as a token.
- ❌ Two typefaces fighting (Inter + something else). One family does the work.
