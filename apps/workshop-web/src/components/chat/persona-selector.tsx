"use client";

import { cn } from "@/lib/utils";
import { Cloud, Sparkles, Droplets, Zap, ChevronDown } from "lucide-react";
import type { Persona } from "@/lib/api-types";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

const PERSONA_CONFIG = {
  drizzle: {
    icon: Cloud,
    label: "Drizzle",
    subtitle: "Chat & Tools",
    activeClass: "bg-sky-500/20 border-sky-500/30 text-sky-300",
    lockedClass: "bg-sky-500/10 border-sky-500/20 text-sky-400/70",
  },
  nimbus: {
    icon: Sparkles,
    label: "Nimbus",
    subtitle: "Generative",
    activeClass: "bg-pink-500/20 border-pink-500/30 text-pink-300",
    lockedClass: "bg-pink-500/10 border-pink-500/20 text-pink-400/70",
  },
  shower: {
    icon: Droplets,
    label: "Shower",
    subtitle: "Quick Reply",
    activeClass: "bg-emerald-500/20 border-emerald-500/30 text-emerald-300",
    lockedClass: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400/70",
  },
  storm: {
    icon: Zap,
    label: "Storm",
    subtitle: "Deep Execute",
    activeClass: "bg-amber-500/20 border-amber-500/30 text-amber-300",
    lockedClass: "bg-amber-500/10 border-amber-500/20 text-amber-400/70",
  },
} as const satisfies Record<Persona, {
  icon: React.ElementType;
  label: string;
  subtitle: string;
  activeClass: string;
  lockedClass: string;
}>;

export function PersonaSelector({
  value,
  onChange,
  isLocked = false,
}: {
  value: Persona;
  onChange?: (persona: Persona) => void;
  isLocked?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const config = PERSONA_CONFIG[value];

  if (isLocked) {
    return (
      <div
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium",
          config.lockedClass,
        )}
      >
        <config.icon size={12} />
        {config.label}
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 px-4 py-2 rounded-full transition-all border",
          "bg-white/5 border-white/5 hover:border-white/20 text-white/60 hover:text-white",
          isOpen && "bg-white/10 border-white/20 text-white"
        )}
      >
        <config.icon size={14} className="opacity-70" />
        <span className="text-xs font-medium tracking-wide">{config.label}</span>
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
              className="absolute bottom-full right-0 mb-3 w-48 z-50 overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/90 backdrop-blur-2xl shadow-2xl"
            >
              <div className="p-2 space-y-0.5">
                {(["drizzle", "nimbus", "shower", "storm"] as Persona[]).map((p) => {
                  const pc = PERSONA_CONFIG[p];
                  const isActive = value === p;
                  return (
                    <button
                      key={p}
                      onClick={() => { onChange?.(p); setIsOpen(false); }}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all",
                        isActive
                          ? "bg-white text-black"
                          : "text-white/50 hover:bg-white/5 hover:text-white"
                      )}
                    >
                      <pc.icon size={14} />
                      <div className="flex flex-col items-start">
                        <span className="text-sm font-semibold">{pc.label}</span>
                        <span className={cn(
                          "text-[9px] uppercase tracking-widest opacity-50",
                          isActive ? "text-black" : "text-white"
                        )}>
                          {pc.subtitle}
                        </span>
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
