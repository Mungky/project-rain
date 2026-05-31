"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSendMessage } from "@/hooks/use-send-message";
import { useComposerStore } from "@/stores/composer-store";
import { usePersonaStore } from "@/stores/persona-store";
import { useModeStore } from "@/stores/mode-store";
import { useStreamingStore } from "@/stores/streaming-store";
import { useUpdateConversation } from "@/hooks/use-conversations";
import { useModes } from "@/hooks/use-modes";
import { PersonaSelector } from "./persona-selector";
import { ModeSelector } from "./mode-selector";
import { SlashCommandMenu } from "./slash-command-menu";
import { filterCommands, executeCommand, type CommandContext } from "@/lib/slash-commands";
import type { Persona } from "@/lib/api-types";
import { Plus, SendHorizonal, Square, FileText, ImageIcon, X } from "lucide-react";

interface AttachedFile {
  name: string;
  content: string;
  mime_type: string;
}

interface ComposerProps {
  conversationId: string;
  isCentered?: boolean;
  forcedModelId?: string;
  /** When set, persona is locked to this value and shown as a badge. */
  forcedPersona?: Persona;
  /** Initial persona shown without locking — used for empty conversations. */
  initialPersona?: Persona;
}

export function Composer({
  conversationId,
  isCentered = false,
  forcedModelId,
  forcedPersona,
  initialPersona,
}: ComposerProps) {
  const router = useRouter();
  const { draft, setDraft, shouldFocus, clearFocusRequest } = useComposerStore();
  const { selectedPersona, setSelectedPersona, activeModels } = usePersonaStore();
  const { selectedMode, setSelectedMode } = useModeStore();
  const { data: modesData } = useModes();
  const updateConv = useUpdateConversation(conversationId);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { mutate } = useSendMessage();
  const isStreaming = useStreamingStore((s) => conversationId in s.activeStreams);
  const abortController = useStreamingStore((s) => s.activeStreams[conversationId]);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [attachError, setAttachError] = useState<string | null>(null);

  const IMAGE_MIME_TYPES = new Set([
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/avif",
  ]);
  const ALLOWED_EXTENSIONS = new Set([
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".csv", ".html", ".css", ".yaml", ".yml",
    ".xml", ".sql", ".sh", ".env", ".toml", ".ini", ".log",
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif",
  ]);

  const BINARY_EXTENSIONS = new Set([
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"
  ]);

  const effectivePersona: Persona = forcedPersona ?? initialPersona ?? selectedPersona;
  const effectiveModel = forcedModelId || activeModels[effectivePersona];

  // Slash command state
  const { setSlashCommand } = useComposerStore();
  const [slashCommands, setSlashCommands] = useState<any[]>([]);
  const [slashIndex, setSlashIndex] = useState(0);
  const slashActive = slashCommands.length > 0;

  const handlePersonaChange = (persona: Persona) => {
    setSelectedPersona(persona);
    updateConv.mutate({ persona });
  };

  const modeOptions = modesData?.modes ?? [{ key: "default", label: "Default", subtitle: "Persona default", builtin: true }];

  const handleModeChange = (mode: string) => {
    setSelectedMode(mode);
    updateConv.mutate({ behavior_mode: mode });
  };

  useEffect(() => {
    if (shouldFocus) {
      textareaRef.current?.focus();
      clearFocusRequest();
    }
  }, [shouldFocus, clearFocusRequest]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [draft]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      setAttachError(`"${file.name}" is not supported.`);
      return;
    }

    setAttachError(null);

    // If it's an image or a complex binary doc, use base64
    if (IMAGE_MIME_TYPES.has(file.type) || BINARY_EXTENSIONS.has(ext)) {
      const dataUrl: string = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      // Strip "data:mime/type;base64," prefix
      const base64 = dataUrl.split(",")[1] ?? "";
      setAttachedFiles((prev) => [...prev, { name: file.name, content: base64, mime_type: file.type }]);
    } else {
      // Plain text files
      const text = await file.text();
      setAttachedFiles((prev) => [...prev, { name: file.name, content: text, mime_type: "text/plain" }]);
    }
  };

  const removeFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const send = () => {
    if (slashActive) return; // don't send while slash menu is open
    const content = draft.trim();
    if ((!content && attachedFiles.length === 0) || isStreaming) return;

    const toSend = [...attachedFiles];
    setDraft("");
    setAttachedFiles([]);
    setSlashCommands([]);
    setSlashCommand(null);
    mutate({
      conversationId,
      content,
      attachments: toSend.length > 0 ? toSend : undefined,
    });
  };

  const handleDraftChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setDraft(value);

    // Detect slash command: / at start of line or after whitespace
    const cursorPos = e.target.selectionStart ?? value.length;
    const textBeforeCursor = value.slice(0, cursorPos);
    const slashMatch = textBeforeCursor.match(/(?:^|\s)\/([\w-]*)$/);

    if (slashMatch) {
      const query = slashMatch[1] || "";
      const matches = filterCommands(query);
      setSlashCommands(matches);
      setSlashIndex(0);
      setSlashCommand({ active: true, query });
    } else {
      setSlashCommands([]);
      setSlashCommand(null);
    }
  };

  const handleSlashSelect = useCallback((cmd: any) => {
    // Remove the slash query from the draft
    const cursorPos = textareaRef.current?.selectionStart ?? draft.length;
    const textBefore = draft.slice(0, cursorPos);
    const textAfter = draft.slice(cursorPos);
    const slashMatch = textBefore.match(/(?:^|\s)\/[\w-]*$/);
    if (slashMatch) {
      const newDraft = textBefore.slice(0, textBefore.length - slashMatch[0].length) + textAfter;
      setDraft(newDraft);
    }
    setSlashCommands([]);
    setSlashCommand(null);
    executeCommand(cmd.name, commandContext);
  }, [draft, setDraft, setSlashCommand]);

  const commandContext: CommandContext = {
    clearDraft: () => setDraft(""),
    createNewConversation: () => {
      // SPA navigation — avoids full page reload that nukes optimistic state.
      router.push("/chat");
    },
    navigateToChat: () => {},
    openSettings: () => {
      window.dispatchEvent(new CustomEvent("open-settings"));
    },
    retryLastMessage: () => {
      // Re-send the last message — just trigger send with last content
      send();
    },
    exportConversation: (format) => {
      window.dispatchEvent(new CustomEvent("export-conversation", { detail: { format } }));
    },
    setTheme: (theme) => {
      document.documentElement.classList.toggle("dark", theme === "dark");
      localStorage.setItem("theme", theme);
    },
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Slash command menu navigation
    if (slashActive) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSlashIndex((i) => Math.min(i + 1, slashCommands.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSlashIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        handleSlashSelect(slashCommands[slashIndex]);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setSlashCommands([]);
        setSlashCommand(null);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
    if (e.key === "Escape" && isStreaming) {
      abortController?.abort();
    }
  };

  return (
    <div className={cn(
      "w-full transition-all duration-700 relative",
      // Mobile: thin side breathing room since chat-thread already inset
      // the floating composer by 2px. Desktop keeps the original max-w pill
      // with comfortable padding.
      isCentered ? "max-w-2xl mx-auto px-4 md:px-0" : "max-w-3xl mx-auto md:mb-2 px-0 md:px-4"
    )}>
      {/*
          IMPORTANT: Removed overflow-hidden from this container
          to allow dropdowns to pop out.
      */}
      <div className={cn(
        "relative flex flex-col border transition-all duration-300 shadow-2xl",
        // Less aggressive radius on small screens (was uniformly 40px — read
        // as an oval at narrow widths). On md+ keep the original pill look.
        "rounded-3xl md:rounded-[2.5rem]",
        "bg-ink-950/80 border-white/10 backdrop-blur-3xl",
        !isCentered && "md:scale-95 origin-bottom"
      )}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.py,.js,.ts,.tsx,.jsx,.json,.csv,.html,.css,.yaml,.yml,.xml,.sql,.sh,.env,.toml,.ini,.log,.jpg,.jpeg,.png,.gif,.webp,.avif,image/*"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* File type error */}
        {attachError && (
          <div className={cn(
            "flex items-center justify-between gap-2 text-[11px] text-rose-400 font-mono",
            isCentered ? "px-8 pt-4" : "px-6 pt-3"
          )}>
            <span>{attachError}</span>
            <button onClick={() => setAttachError(null)} className="hover:text-white transition-colors shrink-0">
              <X size={10} />
            </button>
          </div>
        )}

        {/* Attached file chips */}
        {attachedFiles.length > 0 && (
          <div className={cn(
            "flex flex-wrap gap-2",
            isCentered ? "px-8 pt-4" : "px-6 pt-3"
          )}>
            {attachedFiles.map((f, i) => {
              const isImage = f.mime_type.startsWith("image/");
              return (
                <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/10 rounded-full border border-white/15 text-white/60">
                  {isImage
                    ? <ImageIcon size={11} className="text-purple-400/70" />
                    : <FileText size={11} />}
                  <span className="text-[11px] font-mono max-w-[140px] truncate">{f.name}</span>
                  <button
                    onClick={() => removeFile(i)}
                    className="hover:text-white transition-colors ml-0.5"
                  >
                    <X size={10} />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <textarea
          ref={textareaRef}
          value={draft}
          onChange={handleDraftChange}
          onKeyDown={handleKeyDown}
          placeholder="Message Rain..."
          className={cn(
            "w-full bg-transparent border-none focus:ring-0 focus:outline-none text-white placeholder:text-white/20 resize-none",
            isCentered
              ? "px-6 pt-6 pb-2 md:px-8 md:pt-8 md:min-h-[100px] min-h-[80px] text-base md:text-lg font-light"
              : "px-4 pt-3 pb-1 md:px-6 md:pt-5 min-h-[48px] md:min-h-[60px] text-sm md:text-base font-normal",
            "max-h-[30vh] leading-relaxed"
          )}
          rows={1}
        />

        {/* Slash command floating menu */}
        <SlashCommandMenu
          commands={slashCommands}
          selectedIndex={slashIndex}
          onSelect={handleSlashSelect}
          onClose={() => { setSlashCommands([]); setSlashCommand(null); }}
        />

        <div className={cn(
          "flex items-center justify-between transition-all",
          isCentered
            ? "px-4 pb-4 md:px-6 md:pb-6"
            : "px-2.5 pb-2.5 md:px-4 md:pb-4"
        )}>
          <div className="flex items-center gap-2">
            {/* Attachment Button (+) */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "p-2.5 md:p-3 rounded-full transition-all border",
                attachedFiles.length > 0
                  ? "text-white bg-white/10 border-white/20"
                  : "text-white/40 hover:text-white hover:bg-white/10 border-transparent hover:border-white/10"
              )}
              title="Attach file as context"
            >
              <Plus size={20} strokeWidth={1.5} className="md:hidden" />
              <Plus size={24} strokeWidth={1.5} className="hidden md:block" />
            </button>
            
          </div>

          <div className="flex items-center gap-4">
            {/* Behavior Mode Selector */}
            <ModeSelector
              value={selectedMode}
              modes={modeOptions}
              onChange={handleModeChange}
            />

            {/* Persona Selector */}
            <PersonaSelector
              value={effectivePersona}
              onChange={forcedPersona ? undefined : handlePersonaChange}
              isLocked={!!forcedPersona}
            />

            <div className="h-8 w-[1px] bg-white/10 mx-1" />

            {isStreaming ? (
              <button
                onClick={() => abortController?.abort()}
                className="p-3 md:p-4 rounded-full bg-white text-black hover:scale-105 active:scale-95 transition-all shadow-[0_0_30px_rgba(255,255,255,0.4)]"
                title="Stop Generation"
              >
                <Square size={16} fill="currentColor" className="md:hidden" />
                <Square size={20} fill="currentColor" className="hidden md:block" />
              </button>
            ) : (
              <button
                onClick={send}
                disabled={!draft.trim() && attachedFiles.length === 0}
                className={cn(
                  "p-3 md:p-4 rounded-full transition-all",
                  (draft.trim() || attachedFiles.length > 0)
                    ? "bg-white text-black hover:scale-105 active:scale-95 shadow-[0_0_30px_rgba(255,255,255,0.4)]"
                    : "text-white/5 border border-white/5"
                )}
              >
                <SendHorizonal size={18} strokeWidth={2} className="md:hidden" />
                <SendHorizonal size={22} strokeWidth={2} className="hidden md:block" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}