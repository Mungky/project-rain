import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface GlassPanelProps {
  children: ReactNode;
  variant?: "default" | "elevated" | "subtle";
  className?: string;
}

export function GlassPanel({
  children,
  variant = "default",
  className,
}: GlassPanelProps) {
  return (
    <div
      className={cn(
        "relative rounded-xl border transition-all duration-300",
        "bg-ink-50/80 dark:bg-ink-950/80 backdrop-blur-md",
        "border-ink-200 dark:border-white/20",
        variant === "elevated" && "shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.2)]",
        variant === "subtle" && "bg-ink-50/40 dark:bg-ink-950/40 backdrop-blur-sm",
        className,
      )}
    >
      {children}
    </div>
  );
}