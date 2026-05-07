"use client";

import { useHealth } from "@/hooks/use-health";
import { cn } from "@/lib/utils";

export function HealthBadge() {
  const { data, isError, isLoading } = useHealth();

  // Use backend's single source of truth: status === "ok" means everything is green
  const ok = !isLoading && !isError && data?.status === "ok";

  return (
    <div
      className={cn(
        "fixed bottom-4 right-4 z-50 flex items-center gap-2 px-3 py-1.5 rounded-full",
        "border backdrop-blur-md text-xs font-medium",
        "bg-ink-50/60 dark:bg-ink-900/60 border-ink-200/50 dark:border-ink-700/50",
      )}
      role="status"
      aria-label={ok ? "All systems operational" : "System degraded"}
    >
      <span
        className={cn(
          "inline-block w-2 h-2 rounded-full",
          isLoading && "bg-ink-400 animate-pulse",
          ok && "bg-emerald-500",
          !ok && !isLoading && "bg-rose-500",
        )}
      />
      <span className="text-ink-700 dark:text-ink-300">
        {isLoading ? "Checking…" : ok ? "OK" : "Degraded"}
      </span>
    </div>
  );
}
