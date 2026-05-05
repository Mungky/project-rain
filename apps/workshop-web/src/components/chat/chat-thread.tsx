"use client";

import { cn } from "@/lib/utils";
import { useConversation, conversationKeys } from "@/hooks/use-conversations";
import { useQueryClient } from "@tanstack/react-query";
import { MessageList } from "@/components/chat/message-list";
import { Composer } from "@/components/chat/composer";
import { useFeedback } from "@/hooks/use-feedback";
import { useCopyClipboard } from "@/hooks/use-copy-clipboard";
import { useComposerStore } from "@/stores/composer-store";
import { useStreamingStore } from "@/stores/streaming-store";
import { ContextExtractorBadge } from "./context-extractor-badge";
import type { FeedbackRating } from "@/lib/api-types";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import { useUIStore } from "@/stores/ui-store";
import { useOnlineStatus } from "@/hooks/use-online-status";
import { useEffect } from "react";
import { WifiOff } from "lucide-react";

interface ChatThreadProps {
  conversationId: string;
}

export function ChatThread({ conversationId }: ChatThreadProps) {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useConversation(conversationId);
  const feedbackMutation = useFeedback();
  const { copiedId, copy } = useCopyClipboard();
  const setShowRain = useUIStore((s) => s.setShowRain);
  const isOnline = useOnlineStatus();

  const messages = data?.messages ?? [];
  const isNewSession = messages.length === 0;

  useEffect(() => {
    // Show rain only if it's a new session (0 messages)
    setShowRain(isNewSession);
    
    // Cleanup: turn rain back on when leaving
    return () => setShowRain(true);
  }, [isNewSession, setShowRain]);

  const handleFeedback = (messageId: string, feedback: FeedbackRating) => {
    feedbackMutation.mutate({ messageId, feedback });
  };

  const handleCopy = async (text: string, id: string) => {
    await copy(text, id);
  };

  const handleEdit = (messageId: string, content: string) => {
    // Cancel any ongoing streaming
    const { activeStreams, clearStreaming } = useStreamingStore.getState();
    const controller = activeStreams[conversationId];
    if (controller) {
      controller.abort();
      clearStreaming(conversationId);
    }

    // Remove the user message and the assistant response after it from cache
    const qk = conversationKeys.detail(conversationId);
    queryClient.setQueryData(qk, (old: { messages: { id: string }[] } | undefined) => {
      const msgs = old?.messages ?? [];
      const idx = msgs.findIndex((m) => m.id === messageId);
      if (idx === -1) return old;
      // Remove this user message and the assistant message that follows
      const cutEnd = idx + 2 <= msgs.length ? idx + 2 : idx + 1;
      return { ...old, messages: msgs.slice(0, idx).concat(msgs.slice(cutEnd)) };
    });

    useComposerStore.getState().setDraft(content);
    useComposerStore.getState().requestFocus();
  };

  const handleRetry = (messageId: string) => {
    const qk = conversationKeys.detail(conversationId);
    const state = queryClient.getQueryData(qk) as { messages: { id: string; role: string; content: string }[] } | undefined;
    const msgs = state?.messages ?? [];
    const idx = msgs.findIndex((m) => m.id === messageId);
    if (idx === -1) return;
    // Find the preceding user message to retry
    const prevUser = msgs.slice(0, idx).reverse().find((m) => m.role === "user");
    if (!prevUser) return;
    // Remove the error assistant message
    queryClient.setQueryData(qk, (old: { messages: { id: string }[] } | undefined) => {
      const oldMsgs = old?.messages ?? [];
      return { ...old, messages: oldMsgs.filter((m) => m.id !== messageId) };
    });
    // Set draft to the user message content so they can re-send
    useComposerStore.getState().setDraft(prevUser.content);
    useComposerStore.getState().requestFocus();
  };

  const handleContinue = (_messageId: string) => {
    // Re-send with "continue" instruction
    useComposerStore.getState().setDraft("Continue");
    useComposerStore.getState().requestFocus();
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="w-full max-w-2xl space-y-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className={cn("flex", i % 2 === 1 ? "justify-end" : "justify-start")}>
              <div
                className="rounded-2xl p-6 space-y-3 overflow-hidden relative"
                style={{
                  width: i % 2 === 1 ? "60%" : "80%",
                  background: "linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%)",
                  backgroundSize: "200% 100%",
                  animation: "shimmer 1.8s ease-in-out infinite",
                }}
              >
                <div className="h-3 rounded-full bg-white/5 w-3/4" />
                <div className="h-3 rounded-full bg-white/5 w-1/2" />
                <div className="h-3 rounded-full bg-white/5 w-5/6" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-center">
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Connection Interrupted</h2>
          <p className="text-sm text-white/50 max-w-xs mx-auto">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 relative">
      {/* Offline banner */}
      {!isOnline && (
        <div className="flex items-center justify-center gap-2 px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 text-amber-400/80 text-xs font-mono">
          <WifiOff size={12} />
          You are offline. Messages will not send until connection is restored.
        </div>
      )}

      {/* Header (Only show if not new session) */}
      <AnimatePresence>
        {!isNewSession && (
          <motion.div
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="absolute top-0 right-0 px-6 py-4 flex items-center z-20 pointer-events-none"
          >
            <ContextExtractorBadge />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-hidden relative flex flex-col">
        {isNewSession ? (
          <div className="flex-1 flex items-center justify-center">
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="w-full max-w-2xl px-6 space-y-12"
            >
              <div className="flex flex-col items-center text-center space-y-6">
                <Image src="/rain-logo.svg" alt="Rain" width={64} height={64} className="opacity-80 invert dark:invert-0" />
                <div className="space-y-2">
                  <h1 className="text-3xl font-bold tracking-tighter text-white">What&apos;s on your mind?</h1>
                  <p className="text-white/40 text-sm">Select an agent and start a new session.</p>
                </div>
              </div>

              {/* Suggestion chips */}
              <div className="flex flex-wrap justify-center gap-2">
                {[
                  "Explain quantum computing",
                  "Write a Python script",
                  "Summarize this article",
                  "Debug my code",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      useComposerStore.getState().setDraft(suggestion);
                      useComposerStore.getState().requestFocus();
                    }}
                    className="px-4 py-2 rounded-full text-xs text-white/50 bg-white/5 border border-white/10 hover:bg-white/10 hover:text-white/80 hover:border-white/20 transition-all duration-200"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
              
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-white/10 to-transparent rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000"></div>
                <Composer
                  conversationId={conversationId}
                  isCentered={true}
                  initialPersona={data?.persona}
                />
              </div>
            </motion.div>
          </div>
        ) : (
          <>
            <MessageList
              messages={messages}
              onFeedback={handleFeedback}
              onEdit={handleEdit}
              onCopy={handleCopy}
              copiedId={copiedId}
              onRetry={handleRetry}
              onContinue={handleContinue}
            />
            <div className="p-6">
              <Composer
                conversationId={conversationId}
                isCentered={false}
                forcedPersona={data?.persona}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}