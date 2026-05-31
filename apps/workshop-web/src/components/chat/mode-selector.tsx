"use client";

import { cn } from "@/lib/utils";
import {
  Sparkles,
  Swords,
  GraduationCap,
  Compass,
  Heart,
  SlidersHorizontal,
  ChevronDown,
} from "lucide-react";
import type { ModeOption } from "@/lib/api-types";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

const MODE_ICONS: Record<string, React.ElementType> = {
  default: Sparkles,
  discussion: Swords,
  teacher: GraduationCap,
  mentor: Compass,
  friend: Heart,
};

function iconFor(key: string): React.ElementType {
  return MODE_ICONS[key] ?? SlidersHorizontal;
}

export function ModeSelector({
  value,
  modes,
  onChange,
}: {
  value: string;
  modes: ModeOption[];
  onChange?: (mode: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const current = modes.find((m) => m.key === value) ?? modes[0];
  const Icon = iconFor(current?.key ?? "default");

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 px-4 py-2 rounded-full transition-all border",
          "bg-white/5 border-white/5 hover:border-white/20 text-white/60 hover:text-white",
          isOpen && "bg-white/10 border-white/20 text-white"
        )}
        title="Behavior mode"
      >
        <Icon size={14} className="opacity-70" />
        <span className="text-xs font-medium tracking-wide">{current?.label ?? "Default"}</span>
        <ChevronDown
          size={14}
          className={cn("transition-transform duration-200 opacity-30", isOpen && "rotate-180")}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="absolute bottom-full right-0 mb-3 w-52 z-50 overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/90 backdrop-blur-2xl shadow-2xl max-h-80 overflow-y-auto"
            >
              <div className="p-2 space-y-0.5">
                {modes.map((m) => {
                  const MIcon = iconFor(m.key);
                  const isActive = value === m.key;
                  return (
                    <button
                      key={m.key}
                      onClick={() => {
                        onChange?.(m.key);
                        setIsOpen(false);
                      }}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all",
                        isActive
                          ? "bg-white text-black"
                          : "text-white/50 hover:bg-white/5 hover:text-white"
                      )}
                    >
                      <MIcon size={14} />
                      <div className="flex flex-col items-start">
                        <span className="text-sm font-semibold">{m.label}</span>
                        {m.subtitle && (
                          <span
                            className={cn(
                              "text-[9px] uppercase tracking-widest opacity-50",
                              isActive ? "text-black" : "text-white"
                            )}
                          >
                            {m.subtitle}
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
