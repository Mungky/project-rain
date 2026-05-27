"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { MessageBubble } from "./message-bubble";
import type { MessageResponse, FeedbackRating } from "@/lib/api-types";
import { ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface DisplayMessage extends MessageResponse {
  streaming?: boolean;
  error?: string;
  _optimistic?: boolean;
  _cancelled?: boolean;
}

interface MessageListProps {
  messages: DisplayMessage[];
  onFeedback?: (messageId: string, rating: FeedbackRating) => void;
  onEdit?: (messageId: string, content: string) => void;
  onCopy?: (text: string, id: string) => Promise<void>;
  copiedId?: string | null;
  onRetry?: (messageId: string) => void;
  onContinue?: (messageId: string) => void;
}

export function MessageList({
  messages,
  onFeedback,
  onEdit,
  onCopy,
  copiedId,
  onRetry,
  onContinue,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  
  // Track initial load and previous message count for scrolling behavior
  const isFirstRender = useRef(true);
  const prevMessagesLength = useRef(0);

  const isStreaming = messages.some((m) => m.streaming);

  // Reset scroll lock when streaming finishes so next generation can scroll
  useEffect(() => {
    if (!isStreaming) {
      setUserScrolledUp(false);
    }
  }, [isStreaming]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // Handle initial load or session switch (instantly scroll to bottom)
    if (isFirstRender.current || (prevMessagesLength.current === 0 && messages.length > 0)) {
      // Small timeout to allow DOM to render messages before scrolling
      setTimeout(() => {
        bottomRef.current?.scrollIntoView({ behavior: "auto" });
      }, 0);
      isFirstRender.current = false;
      prevMessagesLength.current = messages.length;
      return;
    }
    prevMessagesLength.current = messages.length;

    // Auto scroll during streaming: use instant scroll, not smooth.
    // Smooth on every token stacks animations → jittery shake.
    if (isStreaming && !userScrolledUp) {
      const el = containerRef.current;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    }
  }, [messages, isStreaming, userScrolledUp]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    
    setShowScrollBtn(fromBottom > 300);

    // If streaming and user scrolls up significantly, pause auto-scroll
    if (isStreaming) {
      if (fromBottom > 50) {
        setUserScrolledUp(true);
      } else {
        // Resume if they scroll back to bottom
        setUserScrolledUp(false);
      }
    }
  }, [isStreaming]);

  const scrollToBottom = () => {
    setUserScrolledUp(false);
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="absolute inset-0 overflow-y-auto no-scrollbar px-4 md:px-8 py-10"
        aria-live="polite"
      >
        <div className="max-w-4xl mx-auto space-y-2">
          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              onFeedback={onFeedback}
              onEdit={onEdit}
              onCopy={onCopy}
              copiedId={copiedId}
              onRetry={onRetry}
              onContinue={onContinue}
            />
          ))}
          <div ref={bottomRef} className="h-4" />
        </div>
      </div>

      <AnimatePresence>
        {showScrollBtn && !isStreaming && (
          <motion.button
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
            onClick={scrollToBottom}
            className="absolute bottom-4 right-6 p-2 rounded-full bg-white/10 border border-white/10 text-white/50 hover:bg-white/20 hover:text-white/80 backdrop-blur-sm transition-all z-10"
          >
            <ChevronDown size={16} />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}

export type { DisplayMessage };