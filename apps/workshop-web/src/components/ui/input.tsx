import { cn } from "@/lib/utils";
import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "w-full rounded-lg border bg-ink-50/40 dark:bg-ink-900/40",
        "border-ink-300 dark:border-ink-700",
        "px-3 py-2 min-h-[36px] text-sm text-ink-900 dark:text-ink-100",
        "placeholder:text-ink-400",
        "focus:border-storm-500 focus:ring-1 focus:ring-storm-500 focus:outline-none",
        "transition-colors",
        className,
      )}
      {...props}
    />
  );
}