import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-black text-white dark:bg-white dark:text-black hover:bg-zinc-800 dark:hover:bg-zinc-200 shadow-sm transition-all active:scale-[0.98]",
  secondary:
    "border border-ink-200 bg-transparent hover:bg-ink-100 text-ink-950 dark:border-ink-800 dark:hover:bg-ink-900 dark:text-ink-50",
  ghost: "hover:bg-ink-100 text-ink-700 dark:hover:bg-ink-900 dark:text-ink-300",
};

export function Button({
  variant = "primary",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg px-4 py-2 min-h-[36px] text-sm font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-storm-400",
        "disabled:opacity-50 disabled:pointer-events-none",
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}