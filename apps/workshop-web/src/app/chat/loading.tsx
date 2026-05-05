import Image from "next/image";

export default function ChatLoading() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center space-y-4">
      <div className="relative">
        <Image
          src="/rain-logo.svg"
          alt="Loading..."
          width={64}
          height={64}
          className="invert dark:invert-0 animate-pulse opacity-50"
        />        <div className="absolute inset-0 bg-white/20 dark:bg-black/20 blur-2xl -z-10" />
      </div>
      <p className="text-xs font-mono uppercase tracking-[0.2em] text-ink-400 animate-pulse">Initializing</p>
    </div>
  );
}