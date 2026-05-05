// ── Tailwind Class Utilities ──────────────────────────────────────────────
// Parse, merge, and diff Tailwind CSS class strings for the visual style editor.

interface ParsedClasses {
  display: string | null;
  position: string | null;
  flexDirection: string | null;
  justifyContent: string | null;
  alignItems: string | null;
  gap: string | null;
  width: string | null;
  height: string | null;
  minWidth: string | null;
  minHeight: string | null;
  maxWidth: string | null;
  maxHeight: string | null;
  margin: string[];
  padding: string[];
  fontSize: string | null;
  fontWeight: string | null;
  textColor: string | null;
  textAlign: string | null;
  lineHeight: string | null;
  bgColor: string | null;
  borderWidth: string | null;
  borderColor: string | null;
  borderRadius: string | null;
  opacity: string | null;
  shadow: string | null;
  other: string[];
}

export type ClassChange = { type: keyof ParsedClasses; value: string | null };

// ── Prefix patterns per category ──────────────────────────────────────────

const DISPLAY_PREFIXES = ["block", "inline-block", "inline", "flex", "inline-flex", "grid", "inline-grid", "hidden", "contents", "table"];
const POSITION_PREFIXES = ["static", "fixed", "absolute", "relative", "sticky"];
const FLEX_DIR_PREFIXES = ["flex-row", "flex-row-reverse", "flex-col", "flex-col-reverse"];
const JUSTIFY_PREFIXES = ["justify-start", "justify-end", "justify-center", "justify-between", "justify-around", "justify-evenly", "justify-stretch"];
const ALIGN_PREFIXES = ["items-start", "items-end", "items-center", "items-baseline", "items-stretch"];
const GAP_REGEX = /^gap-/;
const WIDTH_REGEX = /^w-/;
const HEIGHT_REGEX = /^h-/;
const MIN_W_REGEX = /^min-w-/;
const MIN_H_REGEX = /^min-h-/;
const MAX_W_REGEX = /^max-w-/;
const MAX_H_REGEX = /^max-h-/;
const MARGIN_REGEX = /^m[trblxy]?-/;
const PADDING_REGEX = /^p[trblxy]?-/;
const FONT_SIZE_REGEX = /^text-(?!center$|left$|right$|justify$|start$|end$|inherit$|initial$)|^(text-xs|text-sm|text-base|text-lg|text-xl|text-2xl|text-3xl|text-4xl|text-5xl|text-6xl|text-7xl|text-8xl|text-9xl)/;
const FONT_WEIGHT_REGEX = /^(font-thin|font-extralight|font-light|font-normal|font-medium|font-semibold|font-bold|font-extrabold|font-black)/;
const TEXT_COLOR_REGEX = /^text-(?!center$|left$|right$|justify$|start$|end$|inherit$|initial$|xs$|sm$|base$|lg$|xl$|2xl$|3xl$|4xl$|5xl$|6xl$|7xl$|8xl$|9xl$)/;
const TEXT_ALIGN_PREFIXES = ["text-left", "text-center", "text-right", "text-justify", "text-start", "text-end"];
const LINE_HEIGHT_REGEX = /^(leading-|leading$)/;
const BG_COLOR_REGEX = /^bg-(?!auto$|cover$|contain$|center$|top$|bottom$|left$|right$|no-repeat$|repeat$|fixed$|scroll$|local$|origin-|clip-|blend-)/;
const BORDER_W_REGEX = /^border-(?!opacity|x$|y$|t$|r$|b$|l$|s$|e$|ss$|se$|ee$|es$|spacing|style|collapse|separate)|^border-t(?!-)|^border-r(?!-)|^border-b(?!-)|^border-l(?!-)/;
const BORDER_COLOR_REGEX = /^border-(transparent|current|inherit|white|black|slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)/;
const BORDER_RADIUS_REGEX = /^(rounded|rounded-[trbl][trbl]?|rounded-tl-|rounded-tr-|rounded-bl-|rounded-br-)/;
const OPACITY_REGEX = /^opacity-/;
const SHADOW_REGEX = /^(shadow|shadow-sm|shadow-md|shadow-lg|shadow-xl|shadow-2xl|shadow-inner|shadow-none)/;

// ── Parsing ───────────────────────────────────────────────────────────────

export function parseClasses(classString: string): ParsedClasses {
  const all = classString.split(/\s+/).filter(Boolean);

  const result: ParsedClasses = {
    display: null, position: null,
    flexDirection: null, justifyContent: null, alignItems: null, gap: null,
    width: null, height: null, minWidth: null, minHeight: null,
    maxWidth: null, maxHeight: null,
    margin: [], padding: [],
    fontSize: null, fontWeight: null, textColor: null,
    textAlign: null, lineHeight: null,
    bgColor: null, borderWidth: null, borderColor: null,
    borderRadius: null, opacity: null, shadow: null,
    other: [],
  };

  for (const c of all) {
    if (DISPLAY_PREFIXES.some((p) => c === p)) { result.display = c; }
    else if (POSITION_PREFIXES.some((p) => c === p)) { result.position = c; }
    else if (FLEX_DIR_PREFIXES.some((p) => c === p)) { result.flexDirection = c; }
    else if (JUSTIFY_PREFIXES.some((p) => c === p)) { result.justifyContent = c; }
    else if (ALIGN_PREFIXES.some((p) => c === p)) { result.alignItems = c; }
    else if (GAP_REGEX.test(c)) { result.gap = c; }
    else if (WIDTH_REGEX.test(c)) { result.width = c; }
    else if (HEIGHT_REGEX.test(c)) { result.height = c; }
    else if (MIN_W_REGEX.test(c)) { result.minWidth = c; }
    else if (MIN_H_REGEX.test(c)) { result.minHeight = c; }
    else if (MAX_W_REGEX.test(c)) { result.maxWidth = c; }
    else if (MAX_H_REGEX.test(c)) { result.maxHeight = c; }
    else if (MARGIN_REGEX.test(c)) { result.margin.push(c); }
    else if (PADDING_REGEX.test(c)) { result.padding.push(c); }
    else if (FONT_SIZE_REGEX.test(c)) { result.fontSize = c; }
    else if (FONT_WEIGHT_REGEX.test(c)) { result.fontWeight = c; }
    else if (TEXT_COLOR_REGEX.test(c)) { result.textColor = c; }
    else if (TEXT_ALIGN_PREFIXES.some((p) => c === p)) { result.textAlign = c; }
    else if (LINE_HEIGHT_REGEX.test(c)) { result.lineHeight = c; }
    else if (BG_COLOR_REGEX.test(c)) { result.bgColor = c; }
    else if (BORDER_W_REGEX.test(c)) { result.borderWidth = c; }
    else if (BORDER_COLOR_REGEX.test(c) && !/^border-[trbl]-/.test(c)) { result.borderColor = c; }
    else if (BORDER_RADIUS_REGEX.test(c)) { result.borderRadius = c; }
    else if (OPACITY_REGEX.test(c)) { result.opacity = c; }
    else if (SHADOW_REGEX.test(c)) { result.shadow = c; }
    else { result.other.push(c); }
  }

  return result;
}

// ── Merging ───────────────────────────────────────────────────────────────

export function mergeClasses(original: string[], changes: ClassChange[]): string[] {
  const parsed = parseClasses(original.join(" "));

  for (const change of changes) {
    const key = change.type;
    const value = change.value;

    if (key === "margin") {
      if (value !== null) parsed.margin = value.split(/\s+/).filter(Boolean);
      else parsed.margin = [];
    } else if (key === "padding") {
      if (value !== null) parsed.padding = value.split(/\s+/).filter(Boolean);
      else parsed.padding = [];
    } else if (key === "other") {
      // Don't override 'other'
    } else {
      (parsed as unknown as Record<string, unknown>)[key] = value;
    }
  }

  return buildClassList(parsed);
}

function buildClassList(p: ParsedClasses): string[] {
  const out: string[] = [];
  const singletons: (string | null)[] = [
    p.display, p.position, p.flexDirection, p.justifyContent, p.alignItems, p.gap,
    p.width, p.height, p.minWidth, p.minHeight, p.maxWidth, p.maxHeight,
    p.fontSize, p.fontWeight, p.textColor, p.textAlign, p.lineHeight,
    p.bgColor, p.borderWidth, p.borderColor, p.borderRadius, p.opacity, p.shadow,
  ];

  for (const s of singletons) {
    if (s) out.push(s);
  }
  out.push(...p.margin);
  out.push(...p.padding);
  out.push(...p.other);
  return out;
}

// ── Diff ──────────────────────────────────────────────────────────────────

export function computeClassDiff(original: string[], updated: string[]): { added: string[]; removed: string[] } {
  const origSet = new Set(original);
  const updSet = new Set(updated);

  const added = updated.filter((c) => !origSet.has(c));
  const removed = original.filter((c) => !updSet.has(c));

  return { added, removed };
}

// ── Formatting ────────────────────────────────────────────────────────────

export function classListToCode(classList: string[], indent: number = 0): string {
  const pad = "  ".repeat(indent);
  if (classList.length <= 3) {
    return `${pad}className="${classList.join(" ")}"`;
  }
  return `${pad}className={\n${pad}  \`${classList.join(" ")}\`\n${pad}}`;
}
