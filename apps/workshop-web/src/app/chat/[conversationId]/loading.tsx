export default function ConversationLoading() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 rounded-full border-2 border-storm-500 border-t-transparent animate-spin" />
        <p className="text-sm text-ink-400">Loading conversation…</p>
      </div>
    </div>
  );
}