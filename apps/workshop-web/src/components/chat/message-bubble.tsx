import { memo } from "react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { messageAppear } from "@/styles/motion";
import { StreamingIndicator } from "./streaming-indicator";
import { ThinkingBlock } from "./thinking-block";
import type { MessageResponse, FeedbackRating } from "@/lib/api-types";
import { MarkdownContent } from "./markdown-content";
import { FileText, Copy, Check, RefreshCw, ExternalLink } from "lucide-react";
import { useArtifactsStore } from "@/stores/artifacts-store";
import { apiUrl } from "@/lib/api-client";

interface DisplayMessage extends MessageResponse {
  streaming?: boolean;
  error?: string;
  attached_file_names?: string[];
  _corrected?: boolean;
  _cancelled?: boolean;
}

interface MessageBubbleProps {
  message: DisplayMessage;
  onFeedback?: (messageId: string, rating: FeedbackRating) => void;
  onEdit?: (messageId: string, content: string) => void;
  copiedId?: string | null;
  onCopy?: (text: string, id: string) => void;
  onRetry?: (messageId: string) => void;
  onContinue?: (messageId: string) => void;
}

function MessageBubbleInner({
  message,
  onFeedback,
  onEdit,
  copiedId,
  onCopy,
  onRetry,
  onContinue,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isCopied = copiedId === message.id;

  return (
    <motion.div
      variants={messageAppear}
      initial="hidden"
      animate="visible"
      className={cn("flex w-full mb-6", isUser ? "justify-end" : "justify-start")}
      role="article"
      aria-label={`${isUser ? "You" : "Assistant"} message`}
    >
      <div
        className={cn(
          "max-w-[85%] rounded-[2rem] px-6 py-4 border group relative transition-all duration-500",
          isUser
            ? "bg-white/[0.07] text-white/90 border-white/10"
            : "text-white/90 border-transparent",
        )}
      >
        {!isUser && (message.reasoning_content || (message.react_steps && message.react_steps.length > 0) || (message.tool_events && message.tool_events.length > 0) || message.streaming) && (
          <ThinkingBlock
            content={message.reasoning_content ?? ""}
            streaming={!!message.streaming}
            answerStarted={!!message.content}
            reactSteps={message.react_steps}
            toolEvents={message.tool_events}
          />
        )}
        {isUser && message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {message.attachments.map((att) =>
              att.mime.startsWith("image/") ? (
                <a
                  key={att.id}
                  href={apiUrl(`/v1/documents/${att.id}/view`)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-xl overflow-hidden border border-white/10 hover:border-white/30 transition-all"
                >
                  <img
                    src={apiUrl(`/v1/documents/${att.id}/view`)}
                    alt={att.filename}
                    className="max-h-48 max-w-xs object-cover"
                  />
                </a>
              ) : (
                <a
                  key={att.id}
                  href={apiUrl(`/v1/documents/${att.id}/download`)}
                  download={att.filename}
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-white/10 rounded-full text-[10px] font-mono border border-white/10 opacity-60 hover:opacity-100 transition-all"
                >
                  <FileText size={10} />
                  {att.filename}
                </a>
              )
            )}
          </div>
        )}
        {isUser && (!message.attachments || message.attachments.length === 0) && message.attached_file_names && message.attached_file_names.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {message.attached_file_names.map((name, i) => (
              <div key={i} className="flex items-center gap-1.5 px-2.5 py-1 bg-white/10 rounded-full text-[10px] font-mono opacity-60 border border-white/10">
                <FileText size={10} />
                {name}
              </div>
            ))}
          </div>
        )}

        {/* Answer area: hidden while the model is still in the reasoning phase
            (has reasoning_content but no tokens yet). The ThinkingBlock above
            shows progress; the answer is revealed once the first token lands. */}
        {(message.content || (!message.reasoning_content && message.streaming && !message._cancelled)) && (
          <div className="text-sm leading-relaxed overflow-hidden">
            <MarkdownContent content={message.content || ""} />
            {!message.content && message.streaming && !message._cancelled && <StreamingIndicator />}
          </div>
        )}
        
        {message.error && (
          <div className="mt-2 text-xs text-rose-500 font-mono bg-rose-500/10 p-3 rounded-lg border border-rose-500/20 space-y-2">
            <p>{message.error}</p>
            {onRetry && (
              <button
                onClick={() => onRetry(message.id)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 transition-colors"
              >
                <RefreshCw size={11} />
                Retry
              </button>
            )}
          </div>
        )}

        <div className="flex items-center justify-between mt-4 border-t border-current/5 pt-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono opacity-30 uppercase tracking-widest">
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            {!isUser && message.model && (
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-white/5 text-white/25 border border-white/5 truncate max-w-[140px]" title={message.model}>
                {message.model}
              </span>
            )}
            {message._corrected && (
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400/70 border border-amber-500/20 uppercase tracking-widest">
                revised
              </span>
            )}
            {message._cancelled && (
              <>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-white/5 text-white/25 border border-white/5 uppercase tracking-widest">
                  cancelled
                </span>
                {onContinue && (
                  <button
                    onClick={() => onContinue(message.id)}
                    className="text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-white/10 hover:bg-white/20 text-white/60 transition-colors flex items-center gap-1"
                  >
                    Continue
                  </button>
                )}
              </>
            )}
          </div>
          
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-1 group-hover:translate-y-0">
            {!isUser && onFeedback && (
              <div className="flex items-center gap-0.5 mr-2 pr-2 border-r border-current/10">
                <button
                  onClick={() => onFeedback(message.id, 1)}
                  className={cn(
                    "p-1.5 rounded-lg transition-all hover:bg-current/10",
                    message.feedback === 1 ? "text-emerald-500" : "opacity-40"
                  )}
                  aria-label="Thumbs up"
                  aria-pressed={message.feedback === 1}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill={message.feedback === 1 ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.55l-2.76 10A2 2 0 0 1 17.05 22H7.23a2 2 0 0 1-2-1.62L4 13.62A2 2 0 0 1 5.91 12H11l1-4.12A2 2 0 0 1 14 6h.18a2 2 0 0 1 .82.18Z"/></svg>
                </button>
                <button
                  onClick={() => onFeedback(message.id, -1)}
                  className={cn(
                    "p-1.5 rounded-lg transition-all hover:bg-current/10",
                    message.feedback === -1 ? "text-rose-500" : "opacity-40"
                  )}
                  aria-label="Thumbs down"
                  aria-pressed={message.feedback === -1}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill={message.feedback === -1 ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.55l2.76-10A2 2 0 0 1 7.05 2H16.83a2 2 0 0 1 2 1.62L20 10.38A2 2 0 0 1 18.13 12H13l-1 4.12A2 2 0 0 1 10 18H9.83a2 2 0 0 1-.83-.18Z"/></svg>
                </button>
              </div>
            )}
            
            {!isUser && message.content && (
              <button
                onClick={() => {
                  useArtifactsStore.getState().openArtifact({
                    id: `msg-${message.id}`,
                    title: `Response ${new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
                    language: "markdown",
                    code: message.content,
                    contentType: "markdown",
                  });
                }}
                className="p-1.5 rounded-lg transition-all hover:bg-current/10 opacity-40 hover:opacity-100"
                aria-label="Open in Artifacts"
              >
                <ExternalLink size={14} />
              </button>
            )}

            {onCopy && (
              <button
                onClick={() => onCopy(message.content, message.id)}
                className="p-1.5 rounded-lg transition-all hover:bg-current/10 opacity-40 hover:opacity-100"
                aria-label={isCopied ? "Copied" : "Copy message"}
              >
                {isCopied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
              </button>
            )}
            
            {isUser && onEdit && (
              <button
                onClick={() => onEdit(message.id, message.content)}
                className="p-1.5 rounded-lg transition-all hover:bg-current/10 opacity-40 hover:opacity-100"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/></svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// Memoize: streaming chat re-renders the message list on every SSE token.
// Without this, every prior bubble re-runs MarkdownContent + SyntaxHighlighter
// on each token (visible jank in long threads).
export const MessageBubble = memo(MessageBubbleInner, (prev, next) => (
  prev.message.id === next.message.id &&
  prev.message.content === next.message.content &&
  prev.message.reasoning_content === next.message.reasoning_content &&
  prev.message.streaming === next.message.streaming &&
  prev.message.feedback === next.message.feedback &&
  prev.message._cancelled === next.message._cancelled &&
  prev.message.error === next.message.error &&
  prev.copiedId === next.copiedId
));
