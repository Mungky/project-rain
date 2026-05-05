import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-8">
      <h2 className="text-xl font-semibold">Not Found</h2>
      <p className="text-ink-500">This page doesn&apos;t exist.</p>
      <Link
        href="/chat"
        className="px-4 py-2 rounded-lg bg-storm-500 text-ink-50 hover:bg-storm-600 transition-colors"
      >
        Go to Chat
      </Link>
    </div>
  );
}