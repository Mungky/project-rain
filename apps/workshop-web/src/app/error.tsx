"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-8">
      <h2 className="text-xl font-semibold text-ink-900 dark:text-ink-100">
        Something went wrong.
      </h2>
      <p className="text-ink-500 max-w-md text-center">{error.message}</p>
      <button
        onClick={reset}
        className="px-4 py-2 rounded-lg bg-storm-500 text-ink-50 hover:bg-storm-600 transition-colors focus-visible:ring-2 focus-visible:ring-storm-400"
      >
        Try again
      </button>
    </div>
  );
}