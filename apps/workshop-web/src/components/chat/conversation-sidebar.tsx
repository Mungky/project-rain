"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useConversations, useCreateConversation, useDeleteConversation } from "@/hooks/use-conversations";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { usePersonaStore } from "@/stores/persona-store";
import { useStreamingStore } from "@/stores/streaming-store";
import { useShallow } from "zustand/react/shallow";
import { useUIStore } from "@/stores/ui-store";
import { MessageSquarePlus } from "lucide-react";
import type { Persona } from "@/lib/api-types";

const PERSONA_BAR_COLORS: Record<Persona, string> = {
  drizzle: "bg-sky-400",
  shower: "bg-emerald-400",
  storm: "bg-amber-400",
};

export function ConversationSidebar() {
  const { data: conversations, isLoading } = useConversations();
  const createMutation = useCreateConversation();
  const deleteMutation = useDeleteConversation();
  const router = useRouter();
  const pathname = usePathname();
  const { toggleSettings } = useUIStore();
  const streamingIds = useStreamingStore(
    useShallow((s) => Object.keys(s.activeStreams))
  );

  const handleNewChat = () => {
    const persona = usePersonaStore.getState().selectedPersona;
    createMutation.mutate({ persona }, {
      onSuccess: (conv) => {
        router.push(`/chat/${conv.id}`);
      },
    });
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    deleteMutation.mutate(id);
  };

  const activeId = pathname.match(/\/chat\/([^/]+)/)?.[1];

  const sorted = [...(conversations ?? [])].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );

  return (
    <div className="flex-1 min-h-0 flex flex-col bg-transparent">
      <div className="p-4">
        <Button
          onClick={handleNewChat}
          className="w-full justify-start gap-2"
          variant="secondary"
          disabled={createMutation.isPending}
        >
          <MessageSquarePlus size={15} />
          New Chat
        </Button>
      </div>
      
      <nav className="flex-1 min-h-0 overflow-y-auto no-scrollbar px-2 py-2 space-y-0.5" aria-label="Conversations">
        {isLoading && (
          <div className="px-4 py-2 space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-8 bg-ink-100 dark:bg-ink-900 animate-pulse rounded" />
            ))}
          </div>
        )}
        {!isLoading && sorted.length === 0 && (
          <p className="px-4 py-2 text-xs text-ink-400 italic text-center">No history yet.</p>
        )}
        {sorted.map((conv) => (
          <Link
            key={conv.id}
            href={`/chat/${conv.id}`}
            className={cn(
              "group flex items-center gap-2 rounded-md pl-2 pr-3 py-2 text-sm transition-all",
              activeId === conv.id
                ? "bg-ink-100 dark:bg-ink-900 text-ink-950 dark:text-ink-50 font-medium"
                : "text-ink-500 hover:text-ink-950 dark:hover:text-ink-50 hover:bg-ink-50/50 dark:hover:bg-ink-900/50",
            )}
          >
            <span
              className={cn(
                "w-[3px] self-stretch rounded-sm shrink-0",
                PERSONA_BAR_COLORS[conv.persona] ?? "bg-ink-300",
                streamingIds.includes(conv.id) && "animate-[pulse-bar_2s_ease-in-out_infinite]"
              )}
            />
            <span className="flex-1 truncate">
              {conv.title ?? "Untitled Chat"}
            </span>
            <button
              onClick={(e) => handleDelete(conv.id, e)}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-ink-200 dark:hover:bg-ink-800 transition-opacity text-ink-400 hover:text-rose-500"
              aria-label={`Delete conversation ${conv.title ?? "Untitled"}`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
            </button>
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t border-ink-200 dark:border-ink-800 space-y-1">
        <button
          onClick={toggleSettings}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-ink-500 hover:text-ink-950 dark:hover:text-ink-50 hover:bg-ink-50/50 dark:hover:bg-ink-900/50 transition-all"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          Settings
        </button>
      </div>
    </div>
  );
}