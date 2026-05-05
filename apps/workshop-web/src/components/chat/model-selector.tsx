"use client";

import { useModels } from "@/hooks/use-models";
import { useModelStore } from "@/stores/model-store";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { ChevronDown, Sparkles, Eye, Wrench, Brain, Zap, Image } from "lucide-react";
import type { ModelCapability } from "@/lib/api-types";

const CAP_ICONS: Record<ModelCapability, React.ReactNode> = {
  chat: null,
  tools: <Wrench size={9} />,
  vision: <Eye size={9} />,
  thinking: <Brain size={9} />,
  "image-gen": <Image size={9} />,
};

const CAP_COLORS: Record<ModelCapability, string> = {
  chat: "",
  tools: "text-blue-400/70",
  vision: "text-purple-400/70",
  thinking: "text-amber-400/70",
  "image-gen": "text-pink-400/70",
};

function CapBadge({ cap, active }: { cap: ModelCapability; active: boolean }) {
  const icon = CAP_ICONS[cap];
  if (!icon) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[8px] border",
        active
          ? "bg-black/20 border-black/10 text-black/60"
          : `border-white/10 bg-white/5 ${CAP_COLORS[cap]}`,
      )}
      title={cap}
    >
      {icon}
    </span>
  );
}

export function ModelSelector({
  isLocked = false,
  forcedModelId
}: {
  isLocked?: boolean;
  forcedModelId?: string | null;
}) {
  const { data: models, isLoading } = useModels();
  const { selectedModelId, setSelectedModelId } = useModelStore();
  const [isOpen, setIsOpen] = useState(false);

  const enabledModels = models?.filter((m) => m.enabled) ?? [];

  useEffect(() => {
    if (!isLoading && enabledModels.length > 0 && !selectedModelId) {
      setSelectedModelId(enabledModels[0]?.id ?? "");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, enabledModels.length, selectedModelId]);

  const effectiveModelId = isLocked ? (forcedModelId || selectedModelId) : selectedModelId;
  const activeModel = models?.find((m) => m.id === effectiveModelId);
  const modelName = activeModel?.display_name || activeModel?.name || "Select Agent";

  if (isLoading) return <div className="h-9 w-32 bg-white/5 animate-pulse rounded-full" />;
  if (isLocked) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-white/40 text-xs font-medium">
        <Sparkles size={12} className="text-white/20" />
        {modelName}
      </div>
    );
  }

  const DISPLAYED_CAPS: ModelCapability[] = ["vision", "tools", "thinking", "image-gen"];

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
        <Sparkles size={14} className="text-inherit opacity-50" />
        <span className="text-xs font-medium tracking-wide">{modelName}</span>
        {activeModel?.capabilities && (
          <span className="flex gap-0.5">
            {DISPLAYED_CAPS.filter((c) => activeModel.capabilities.includes(c)).map((c) => (
              <span key={c} className={cn("opacity-60", CAP_COLORS[c])}>{CAP_ICONS[c]}</span>
            ))}
          </span>
        )}
        <ChevronDown size={14} className={cn("transition-transform duration-200 opacity-30", isOpen && "rotate-180")} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="absolute bottom-full right-0 mb-3 w-72 z-50 overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/90 backdrop-blur-2xl shadow-2xl"
            >
              <div className="p-2 space-y-0.5 max-h-[280px] overflow-y-auto no-scrollbar">
                {enabledModels.map((m) => {
                  const isActive = selectedModelId === m.id;
                  return (
                    <button
                      key={m.id}
                      onClick={() => { setSelectedModelId(m.id); setIsOpen(false); }}
                      className={cn(
                        "w-full flex items-center justify-between px-3 py-2.5 rounded-xl transition-all",
                        isActive
                          ? "bg-white text-black"
                          : "text-white/50 hover:bg-white/5 hover:text-white"
                      )}
                    >
                      <div className="flex flex-col items-start min-w-0">
                        <span className="text-sm font-semibold truncate">{m.display_name || m.name}</span>
                        <span className={cn("text-[9px] uppercase tracking-widest opacity-50", isActive ? "text-black" : "text-white")}>
                          {m.provider}
                        </span>
                      </div>
                      <div className="flex gap-1 shrink-0 ml-2">
                        {DISPLAYED_CAPS.filter((c) => m.capabilities?.includes(c)).map((c) => (
                          <CapBadge key={c} cap={c} active={isActive} />
                        ))}
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
