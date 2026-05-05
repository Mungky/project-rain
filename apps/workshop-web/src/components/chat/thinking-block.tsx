"use client";

import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, Brain, Globe, Code, FileSearch, Wrench } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

import type { ReactStep, ToolEvent } from "@/lib/api-types";

interface ThinkingBlockProps {
  content: string;
  streaming?: boolean;
  reactSteps?: ReactStep[] | null;
  toolEvents?: ToolEvent[] | null;
}

const TOOL_ICONS: Record<string, React.ReactNode> = {
  "web-search": <Globe size={10} />,
  "web-search-searxng": <Globe size={10} />,
  "web-reader": <FileSearch size={10} />,
  "python-executor": <Code size={10} />,
};

function toolIcon(name: string) {
  return TOOL_ICONS[name] ?? <Wrench size={10} />;
}

function toolLabel(name: string): string {
  return name
    .replace(/-searxng$/, "")
    .replace(/-/g, " ")
    .replace(/_/g, " ");
}

export function ThinkingBlock({ content, streaming = false, reactSteps, toolEvents }: ThinkingBlockProps) {
  const hasReact = Boolean(reactSteps && reactSteps.length > 0);
  const hasTools = Boolean(toolEvents && toolEvents.length > 0);
  const hasReasoning = Boolean(content && content.trim().length > 0);
  const hasContent = hasReact || hasReasoning || hasTools;

  const [expanded, setExpanded] = useState(false);
  const [elapsedSecs, setElapsedSecs] = useState(0);
  const [hasEverHadContent, setHasEverHadContent] = useState(false);
  const hasStreamedRef = useRef(false);
  const prefersReducedMotion = useReducedMotion();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startRef = useRef<number | null>(null);

  // Track whether content ever appeared, so we keep showing the block after streaming ends
  useEffect(() => {
    if (hasContent) setHasEverHadContent(true);
  }, [hasContent]);

  // Auto-collapse when streaming finishes
  // Only auto-collapse if the component was in streaming mode (not after a re-fetch remount)
  useEffect(() => {
    if (streaming) hasStreamedRef.current = true;
    if (!streaming && hasStreamedRef.current && expanded) {
      // Small delay so user can see the final content before collapsing
      const timer = setTimeout(() => setExpanded(false), 1500);
      return () => clearTimeout(timer);
    }
  }, [streaming, expanded]);

  useEffect(() => {
    if (streaming && !startRef.current) {
      startRef.current = Date.now();
      timerRef.current = setInterval(() => {
        setElapsedSecs(Math.floor((Date.now() - startRef.current!) / 1000));
      }, 1000);
    }
    if (!streaming && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [streaming]);

  // Parse lines starting with - or * or just text as steps
  const thoughtSteps = content
    .split("\n")
    .map(line => line.trim().replace(/^[-*]\s*/, ""))
    .filter(line => line.length > 0);

  // Derive a short summary from the most recent thought step
  const lastStep = thoughtSteps.length > 0 ? thoughtSteps[thoughtSteps.length - 1] : null;
  const latestSummary = lastStep
    ? lastStep.slice(0, 80) + (lastStep.length > 80 ? "…" : "")
    : null;

  // Estimate progress based on elapsed time (0–30s range, caps at 95%)
  const progressPct = streaming ? Math.min((elapsedSecs / 30) * 100, 95) : 100;

  // Show the block during streaming OR after content has appeared
  if (!streaming && !hasEverHadContent && !hasContent) return null;

  const headerLabel = streaming
    ? elapsedSecs > 0
      ? `Thinking… ${elapsedSecs}s`
      : "Thinking…"
    : "Thought process";

  return (
    <div className="mb-4">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-2 text-[11px] font-bold rounded-xl px-3 py-2 text-white/40 hover:text-white/70 hover:bg-white/5 transition-all group border border-white/5 bg-white/[0.02]"
      >
        <Brain
          className={cn(
            "w-3.5 h-3.5 transition-colors shrink-0",
            streaming ? "text-amber-400 animate-pulse" : "text-white/30",
          )}
        />
        <span className="uppercase tracking-widest">{headerLabel}</span>
        {latestSummary && (
          <span className="text-[9px] text-white/20 italic truncate max-w-[280px] hidden sm:inline-block">
            — {latestSummary}
          </span>
        )}
        <ChevronDown
          className={cn(
            "w-3 h-3 transition-transform duration-200 shrink-0",
            expanded && "rotate-180",
          )}
        />
      </button>

      {/* Cosmetic progress bar */}
      {streaming && (
        <div className="h-[2px] w-full bg-white/5 rounded-full overflow-hidden mt-1">
          <motion.div
            className="h-full bg-gradient-to-r from-amber-500/30 via-amber-400/20 to-transparent rounded-full"
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
      )}

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-2 ml-3 pl-4 border-l border-white/10 space-y-4 py-2">
              
              {/* Combine Tool Usage and Reasoning into a single step-by-step list */}
              <div className="space-y-3.5">
                {/* 1. Real-time Skill usage events */}
                {toolEvents?.map((event, i) => (
                  <motion.div 
                    key={`tool-${i}`} 
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-3"
                  >
                    <div className="relative flex items-center justify-center w-4 h-4 shrink-0">
                      {event.status === "calling" ? (
                        <div className="w-2.5 h-2.5 rounded-full border-2 border-white/10 border-t-amber-400 animate-spin" />
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-amber-400/60 shadow-[0_0_8px_rgba(251,191,36,0.3)]" />
                      )}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className={cn(
                        "text-[11px] font-medium leading-relaxed",
                        event.status === "calling" ? "text-white/80" : "text-white/40"
                      )}>
                        Using Skill: <span className="font-mono opacity-80">{toolLabel(event.name)}</span>
                      </span>
                      {event.status === "calling" && (
                         <span className="text-[9px] text-white/20 animate-pulse italic">Waiting for result…</span>
                      )}
                    </div>
                  </motion.div>
                ))}

                {/* 2. Internal planning/reasoning steps */}
                {thoughtSteps.map((step, i) => {
                  const isLast = i === thoughtSteps.length - 1;
                  const isThinking = isLast && streaming;
                  
                  return (
                    <motion.div 
                      key={`step-${i}`} 
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-center gap-3"
                    >
                      <div className="relative flex items-center justify-center w-4 h-4 shrink-0">
                        {isThinking ? (
                          <div className="w-2.5 h-2.5 rounded-full border-2 border-white/10 border-t-white/60 animate-spin" />
                        ) : (
                          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400/40 shadow-[0_0_8px_rgba(52,211,153,0.3)]" />
                        )}
                      </div>
                      <span className={cn(
                        "text-[11px] font-medium leading-relaxed",
                        isThinking ? "text-white/80" : "text-white/40"
                      )}>
                        {step}
                      </span>
                    </motion.div>
                  );
                })}
              </div>

              {/* 3. Fallback loading state */}
              {streaming && !thoughtSteps.length && !hasTools && (
                 <div className="flex items-center gap-3 animate-pulse">
                    <div className="w-4 h-4 flex items-center justify-center">
                        <div className="w-2.5 h-2.5 rounded-full border-2 border-white/10 border-t-white/40 animate-spin" />
                    </div>
                    <span className="text-[11px] font-medium text-white/30">Formulating approach…</span>
                 </div>
              )}

              {/* 4. Legacy ReAct Steps (for compatibility/deep detail) */}
              {hasReact && !hasTools && (
                <div className="space-y-2.5 pt-2 border-t border-white/[0.03]">
                  {reactSteps!.map((step, idx) => (
                    <div key={idx} className="flex flex-wrap gap-1.5">
                      {step.tools.map((t, i) => (
                        <div key={i} className="px-2 py-1 rounded bg-white/5 text-[9px] text-white/30 font-mono">
                          {toolLabel(t.name)}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
