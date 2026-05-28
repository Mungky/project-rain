"use client";

import { Brain } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { useContextExtractorStore } from "@/stores/context-extractor-store";

const labels = {
  idle: "standby",
  extracting: "thinking...",
  synced: "context synced",
  error: "error",
};

const colors = {
  idle: "text-white/25",
  extracting: "text-amber-400/70",
  synced: "text-emerald-400/80",
  error: "text-red-400/70",
};

export function ContextExtractorBadge() {
  const status = useContextExtractorStore((s) => s.status);
  // Hide entirely when idle — "STANDBY" without context confused users into
  // thinking it was a persona/connection state. Re-appears when actually
  // extracting/synced/errored.
  if (status === "idle") return null;

  return (
    <div className="flex flex-col items-center gap-0.5">
      <Brain
        size={15}
        className={cn(
          "transition-colors duration-500",
          colors[status],
          status === "extracting" && "animate-pulse",
        )}
      />
      <AnimatePresence mode="wait">
        <motion.span
          key={status}
          initial={{ opacity: 0, y: 2 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -2 }}
          transition={{ duration: 0.2 }}
          className={cn(
            "text-[8px] font-mono tracking-widest uppercase",
            colors[status],
          )}
        >
          {labels[status]}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}
