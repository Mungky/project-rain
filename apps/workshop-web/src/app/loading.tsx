export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 rounded-full border-2 border-storm-500 border-t-transparent animate-spin" />
        <p className="text-sm text-ink-400">Loading…</p>
      </div>
    </div>
  );
}