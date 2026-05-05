"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { cn } from "@/lib/utils";
import { Copy, Check, Hash, ArrowUpDown, ArrowUp, ArrowDown, ExternalLink } from "lucide-react";
import { useState, useCallback, createContext, useContext, useEffect, useRef } from "react";
import { useArtifactsStore } from "@/stores/artifacts-store";

const BOX_CHARS = new Set("┌─┬┐│└┴┘├┼┤▶←→↑↓▼▲◄►╔╗╚╝║═╠╣╦╩╬▐▌█▓░▒⟨⟩⎡⎤⎣⎦⎢⎥┝┥┨┷┾╀╂╄╆╊╌╍╎╏▄▀");
const BOX_RE = /[┌─┬┐│└┴┘├┼┤▶←→↑↓▼▲◄►╔╗╚╝║═╠╣╦╩╬▐▌█▓░▒]/;

function hasBoxChar(line: string): boolean {
  for (const ch of line) {
    if (BOX_CHARS.has(ch)) return true;
  }
  return false;
}

function looksLikeDiagramBlock(lines: string[], start: number): { end: number } {
  let gapCount = 0;
  let i = start;
  let lastDiagram = start;
  while (i < lines.length && gapCount < 2) {
    const line: string = lines[i] ?? "";
    if (hasBoxChar(line)) {
      gapCount = 0;
      lastDiagram = i;
    } else if (/^\s*$/.test(line)) {
      gapCount++;
    } else if (/^\s+[│┃║┤├┬┴┼╋]\s/.test(line) || /^\s+[│┃║]/.test(line)) {
      gapCount = 0;
      lastDiagram = i;
    } else {
      gapCount++;
    }
    if (gapCount >= 2) break;
    i++;
  }
  return { end: lastDiagram };
}

function wrapAsciiDiagrams(content: string): string {
  if (!BOX_RE.test(content)) return content;

  const lines = content.split("\n");
  const result: string[] = [];
  let i = 0;

  while (i < lines.length) {
    if (hasBoxChar(lines[i] ?? "")) {
      const { end } = looksLikeDiagramBlock(lines, i);
      const blockLines = lines.slice(i, end + 1);
      result.push("```text", ...blockLines, "```");
      i = end + 1;
    } else {
      result.push(lines[i] ?? "");
      i++;
    }
  }
  return result.join("\n");
}

interface MarkdownContentProps {
  content: string;
  className?: string;
}

// Sort context to allow th elements to read sort state
interface SortCtx {
  sortKey: number | null;
  sortDir: "asc" | "desc";
  onSort: (idx: number) => void;
}
const SortContext = createContext<SortCtx | null>(null);
function useSortContext() {
  return useContext(SortContext);
}

const Th = ({ children }: any) => {
  const sortCtx = useSortContext();
  const thRef = useRef<HTMLTableCellElement>(null);

  // Extract column index from DOM after mount
  const [colIdx, setColIdx] = useState<number | null>(null);

  useEffect(() => {
    const th = thRef.current;
    if (!th || !sortCtx || colIdx !== null) return;
    const row = th.closest("tr");
    if (!row) return;
    const idx = Array.from(row.children).indexOf(th);
    setColIdx(idx);
  }, [sortCtx, colIdx]);

  const isSorted = sortCtx && colIdx !== null && sortCtx.sortKey === colIdx;

  return (
    <th
      ref={thRef}
      onClick={sortCtx && colIdx !== null ? () => sortCtx.onSort(colIdx) : undefined}
      className={cn(
        sortCtx && "cursor-pointer select-none hover:bg-white/5 transition-colors",
      )}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        {isSorted ? (
          sortCtx.sortDir === "asc" ? <ArrowUp size={10} className="opacity-50" /> : <ArrowDown size={10} className="opacity-50" />
        ) : (
          sortCtx && <ArrowUpDown size={10} className="opacity-20" />
        )}
      </span>
    </th>
  );
};

const CodeBlock = ({ className, children, ...props }: any) => {
  const match = /language-(\w+)/.exec(className || "");
  const codeText = String(children).replace(/\n$/, "");
  const [copied, setCopied] = useState(false);
  const [showLines, setShowLines] = useState(false);

  const isBlock = match || codeText.includes("\n");
  const lang = match?.[1] ?? "text";

  const handleCopy = () => {
    navigator.clipboard.writeText(codeText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenArtifact = () => {
    const openArtifact = useArtifactsStore.getState().openArtifact;
    openArtifact({
      id: `code-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      title: lang,
      language: lang,
      code: codeText,
    });
  };

  return isBlock ? (
    <div className="relative group my-6 rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
      <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono uppercase tracking-widest text-white/30">{lang}</span>
          <button
            onClick={() => setShowLines(!showLines)}
            className={cn(
              "text-[10px] flex items-center gap-1 transition-colors",
              showLines ? "text-white/60" : "text-white/20 hover:text-white/50"
            )}
          >
            <Hash size={11} />
          </button>
          <button
            onClick={handleOpenArtifact}
            className="text-[10px] flex items-center gap-1 text-white/20 hover:text-white/50 transition-colors"
            title="Open in Artifacts"
          >
            <ExternalLink size={11} />
          </button>
        </div>
        <button onClick={handleCopy} className="text-white/30 hover:text-white transition-colors">
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>
      <pre
        data-language={lang}
        data-code={codeText}
        data-line-numbers={showLines ? "true" : "false"}
        className="!m-0"
      >
        <SyntaxHighlighter
          style={vscDarkPlus as any}
          language={lang}
          PreTag="div"
          customStyle={{
            margin: 0,
            padding: "1.5rem",
            background: "transparent",
            fontSize: "0.8125rem",
            lineHeight: "1.6",
            fontFamily: 'var(--font-mono)',
          }}
          {...props}
        >
          {codeText}
        </SyntaxHighlighter>
      </pre>
    </div>
  ) : (
    <code className="bg-white/10 px-1.5 py-0.5 rounded-md font-mono text-[0.8125rem] text-white/90 border border-white/5" {...props}>
      {children}
    </code>
  );
};

/** Interactive checkbox list item — each checkbox maintains its own state */
function CheckboxItem({ children }: { children: React.ReactNode }) {
  const childArr = Array.isArray(children) ? children : [children];
  return (
    <span className="inline-flex items-start gap-2">
      {childArr.map((child: any, i: number) => {
        if (
          typeof child === "object" &&
          child?.props?.node?.tagName === "input" &&
          child?.props?.checked !== undefined
        ) {
          return <InlineCheckbox key={i} defaultChecked={child.props.checked} label={child.props.children} />;
        }
        return <span key={i}>{child}</span>;
      })}
    </span>
  );
}

function InlineCheckbox({ defaultChecked, label }: { defaultChecked: boolean; label?: string }) {
  const [checked, setChecked] = useState(defaultChecked);
  return (
    <label className="inline-flex items-center gap-1.5 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => setChecked(e.target.checked)}
        className="pointer-events-auto"
      />
      <span className={cn("transition-all duration-200", checked && "line-through opacity-40")}>
        {label}
      </span>
    </label>
  );
}

/** Table wrapper with sortable column headers */
function SortableTable({ children }: { children: any }) {
  const [sortKey, setSortKey] = useState<number | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const tableRef = useRef<HTMLTableElement>(null);

  const handleSort = useCallback((colIdx: number) => {
    setSortKey((prev) => {
      const newDir = prev === colIdx && sortDir === "asc" ? "desc" : "asc";
      setSortDir(newDir);
      return colIdx;
    });
  }, [sortDir]);

  // Perform DOM sort when key/dir change
  useEffect(() => {
    if (sortKey === null || !tableRef.current) return;
    const tbody = tableRef.current.querySelector("tbody");
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll("tr"));
    rows.sort((a, b) => {
      const aVal = (a.children[sortKey] as HTMLElement)?.innerText?.trim() ?? "";
      const bVal = (b.children[sortKey] as HTMLElement)?.innerText?.trim() ?? "";
      const aNum = parseFloat(aVal);
      const bNum = parseFloat(bVal);
      const cmp = !isNaN(aNum) && !isNaN(bNum) ? aNum - bNum : aVal.localeCompare(bVal);
      return sortDir === "asc" ? cmp : -cmp;
    });
    rows.forEach((r) => tbody.appendChild(r));
  }, [sortKey, sortDir]);

  return (
    <SortContext.Provider value={{ sortKey, sortDir, onSort: handleSort }}>
      <div className="overflow-x-auto my-6 rounded-xl border border-white/10">
        <table ref={tableRef} className="w-full text-sm text-left border-collapse">
          {children}
        </table>
      </div>
    </SortContext.Provider>
  );
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  const processed = wrapAsciiDiagrams(content);
  return (
    <div className={cn("prose-rain max-w-none break-words", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          h1: ({ children }) => <h1>{children}</h1>,
          h2: ({ children }) => <h2>{children}</h2>,
          h3: ({ children }) => <h3>{children}</h3>,
          h4: ({ children }) => <h4>{children}</h4>,
          h5: ({ children }) => <h5>{children}</h5>,
          h6: ({ children }) => <h6>{children}</h6>,

          p: ({ children }) => <p>{children}</p>,
          ul: ({ children }) => <ul>{children}</ul>,
          ol: ({ children }) => <ol>{children}</ol>,

          li: ({ children, className: liClass, ...rest }) => {
            // Check if this list item contains a checkbox input
            const childArr = Array.isArray(children) ? children : [children];
            const hasCheckbox = childArr.some(
              (child: any) => typeof child === "object" && child?.props?.node?.tagName === "input"
            );
            if (hasCheckbox) {
              return (
                <li className="list-none">
                  <CheckboxItem>{children}</CheckboxItem>
                </li>
              );
            }
            return <li className={cn(liClass)} {...rest}>{children}</li>;
          },

          blockquote: ({ children }) => <blockquote>{children}</blockquote>,

          code: (props) => <CodeBlock {...props} />,

          table: ({ children }) => <SortableTable>{children}</SortableTable>,
          thead: ({ children }) => <thead>{children}</thead>,
          th: ({ children }) => <Th>{children}</Th>,
          td: ({ children }) => <td>{children}</td>,
          tr: ({ children }) => <tr>{children}</tr>,

          hr: () => <hr className="my-8 border-white/10" />,

          img: ({ src, alt }) => {
            if (!src) return null;
            return (
              <figure className="my-8 text-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={src}
                  alt={alt ?? ""}
                  loading="lazy"
                  decoding="async"
                  className="rounded-2xl border border-white/10 shadow-2xl max-w-full h-auto mx-auto cursor-zoom-in hover:scale-[1.02] transition-transform duration-200"
                  onClick={(e) => {
                    // Lightbox hook — dispatches to lightbox store if available
                    const imgs = e.currentTarget.closest(".prose-rain")?.querySelectorAll("img");
                    if (imgs) {
                      const idx = Array.from(imgs).indexOf(e.currentTarget);
                      window.dispatchEvent(
                        new CustomEvent("lightbox-open", {
                          detail: { images: Array.from(imgs).map((img) => ({ src: img.src, alt: img.alt })), index: idx },
                        })
                      );
                    }
                  }}
                />
                {alt && !alt.startsWith("!") && (
                  <figcaption className="mt-2 text-xs text-white/30 italic">{alt}</figcaption>
                )}
              </figure>
            );
          },

          // Additional elements
          dl: ({ children }) => <dl>{children}</dl>,
          dt: ({ children }) => <dt>{children}</dt>,
          dd: ({ children }) => <dd>{children}</dd>,
          sup: ({ children }) => <sup>{children}</sup>,
          sub: ({ children }) => <sub>{children}</sub>,
          abbr: ({ children, title }) => <abbr title={title}>{children}</abbr>,
          details: ({ children }) => <details>{children}</details>,
          summary: ({ children }) => <summary>{children}</summary>,
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}