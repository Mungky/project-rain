"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { SlashCommand } from "@/lib/slash-commands";

interface SlashCommandMenuProps {
  commands: SlashCommand[];
  selectedIndex: number;
  onSelect: (command: SlashCommand) => void;
  onClose: () => void;
}

export function SlashCommandMenu({
  commands,
  selectedIndex,
  onSelect,
  onClose,
}: SlashCommandMenuProps) {
  if (commands.length === 0) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 8, scale: 0.96 }}
        transition={{ duration: 0.15, ease: "easeOut" }}
        className="absolute bottom-full left-0 mb-3 w-64 z-50 overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/95 backdrop-blur-2xl shadow-2xl"
      >
        <div className="p-1.5">
          <div className="px-3 py-2 border-b border-white/5">
            <span className="text-[10px] font-medium text-white/25 uppercase tracking-widest">
              Slash Commands
            </span>
          </div>
          <div className="py-1 max-h-64 overflow-y-auto">
            {commands.map((cmd, idx) => (
              <button
                key={cmd.name}
                onClick={() => onSelect(cmd)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all ${
                  idx === selectedIndex
                    ? "bg-white text-black"
                    : "text-white/60 hover:bg-white/5 hover:text-white"
                }`}
              >
                <cmd.icon size={15} className="shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="text-sm font-semibold">{cmd.name}</span>
                  <span className="text-[10px] opacity-50 leading-tight">
                    {cmd.description}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
