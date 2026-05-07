"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "@/stores/auth-store";
import { apiGet, apiPost, apiPostForm } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { FileProposalCard } from "./file-proposal-card";
import { SearchResultsCard } from "./search-results-card";
import {
  CloudUpload, Send, Paperclip, Loader2, FolderSearch,
  CheckCircle2, XCircle, Clock, FolderOpen, X
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

type MessageRole = "user" | "nimbus";
type MessageType =
  | "text"
  | "file-attach"
  | "proposal"
  | "search-results"
  | "queue-status"
  | "upload-success"
  | "upload-failed"
  | "access-request-sent"
  | "access-denied";

interface ChatMessage {
  id: string;
  role: MessageRole;
  type: MessageType;
  content: string;
  data?: Record<string, unknown>;
  timestamp: Date;
}

interface ProposalData {
  proposal_id: string;
  proposed_name: string;
  original_name: string;
  file_size: number;
  doc_type: string;
  client_code: string;
  project_code: string;
  folder_category: string;
  version: string;
  seq_preview: number;
}

interface SearchResult {
  id: string;
  archived_filename: string;
  doc_type: string;
  client_code: string;
  project_code: string;
  folder_category: string;
  status: string;
  version: string;
  created_at: string;
}

interface QueueItem {
  doc_id: string;
  archived_filename: string;
  status: string;
  client_code: string;
  project_code: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const DOC_TYPES = ["PO", "Q", "PL", "QC", "BA", "DRW", "INV", "PROP", "BAST", "MISC"];
const FOLDER_CATEGORIES = ["DRW", "QC", "PO", "BA", "PROPOSAL", "INVOICE", "MISC"];
const DOC_TYPE_FOLDER: Record<string, string> = {
  PO: "PO", INV: "INVOICE", PROP: "PROPOSAL", QC: "QC",
  DRW: "DRW", BA: "BA", BAST: "BA", Q: "MISC", PL: "MISC", MISC: "MISC",
};

function guessDocType(filename: string): { doc_type: string; folder_category: string } {
  const upper = filename.toUpperCase();
  const found = DOC_TYPES.find((t) => {
    const re = new RegExp(`(^|[-_\\s])${t}([-_\\s\\d]|$)`);
    return re.test(upper);
  });
  const doc_type = found ?? "MISC";
  return { doc_type, folder_category: DOC_TYPE_FOLDER[doc_type] ?? "MISC" };
}

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

const SEARCH_INTENTS = [
  "cari", "cariin", "find", "caritin", "tolong cari", "ada file", "file apa",
  "dokumen", "bisa kasih", "minta", "pull", "ambil",
];

function isSearchQuery(text: string): boolean {
  const lower = text.toLowerCase();
  return SEARCH_INTENTS.some((kw) => lower.includes(kw));
}

function mkMsg(
  role: MessageRole,
  type: MessageType,
  content: string,
  data?: Record<string, unknown>
): ChatMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    role, type, content, data,
    timestamp: new Date(),
  };
}

// ── Component ─────────────────────────────────────────────────────────────────

export function NimbusChat() {
  const user = useAuthStore((s) => s.user);
  const [messages, setMessages] = useState<ChatMessage[]>([
    mkMsg("nimbus", "text",
      `Halo, **${user?.username ?? "boss"}**. Saya Nimbus, document archive agent kamu.\n\nKamu bisa:\n- **Upload file** — drop atau attach file di bawah\n- **Cari dokumen** — ketik "cariin file klien X" atau "cari PO project Y"`,
    ),
  ]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [pendingSearchResults, setPendingSearchResults] = useState<SearchResult[] | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const push = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Queue polling
  const startPolling = useCallback(() => {
    if (pollingRef.current) return;
    pollingRef.current = setInterval(async () => {
      try {
        const res = await apiGet<{ items: QueueItem[] }>("/v1/nimbus/queue");
        setQueueItems(res.items);
        if (res.items.length === 0 && pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
      } catch {
        // ignore
      }
    }, 3000);
  }, []);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  // ── File drop ──────────────────────────────────────────────────────────────

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) setPendingFiles((prev) => [...prev, ...files]);
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      setPendingFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
      e.target.value = "";
    }
  }, []);

  // ── Propose file ──────────────────────────────────────────────────────────

  const proposeFile = useCallback(async (file: File) => {
    push(mkMsg("user", "file-attach", file.name, { size: file.size }));
    setIsThinking(true);

    const { doc_type, folder_category } = guessDocType(file.name);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("doc_type", doc_type);
    fd.append("client_code", "CLIENT");
    fd.append("project_code", "PROJECT");
    fd.append("folder_category", folder_category);
    fd.append("version", "V1");

    try {
      const proposal = await apiPostForm<ProposalData>("/v1/nimbus/propose", fd);
      setIsThinking(false);
      push(mkMsg("nimbus", "proposal",
        `Simpan sebagai nama berikut ya. Cek dulu, edit kalau perlu, baru approve.`,
        proposal as unknown as Record<string, unknown>
      ));
    } catch (err: unknown) {
      setIsThinking(false);
      const msg = err instanceof Error ? err.message : "Upload gagal";
      push(mkMsg("nimbus", "text", `Hmm, ada masalah: ${msg}`));
    }
  }, [push]);

  // Auto-propose first pending file when file added
  useEffect(() => {
    if (pendingFiles.length > 0 && !isThinking) {
      const [first, ...rest] = pendingFiles;
      setPendingFiles(rest);
      proposeFile(first);
    }
  }, [pendingFiles, isThinking, proposeFile]);

  // ── Confirm proposal ──────────────────────────────────────────────────────

  const confirmProposal = useCallback(async (proposalId: string, data: ProposalData) => {
    setIsThinking(true);
    try {
      const res = await apiPost<{
        doc_id: string; archived_filename: string; queue_position: number; drive_path: string; message: string;
      }>(`/v1/nimbus/confirm/${proposalId}`, {
        doc_type: data.doc_type,
        client_code: data.client_code,
        project_code: data.project_code,
        folder_category: data.folder_category,
        version: data.version,
      });
      setIsThinking(false);
      push(mkMsg("nimbus", "queue-status",
        `Siap boss. **${res.archived_filename}** masuk queue di posisi ${res.queue_position}. Saya kabarin kalau sudah kelar.`,
        { doc_id: res.doc_id, archived_filename: res.archived_filename, drive_path: res.drive_path }
      ));
      setQueueItems((prev) => [
        ...prev,
        { doc_id: res.doc_id, archived_filename: res.archived_filename, status: "queued", client_code: data.client_code, project_code: data.project_code },
      ]);
      startPolling();

      // Poll for this specific doc completion
      const docId = res.doc_id;
      const checkDone = setInterval(async () => {
        try {
          const q = await apiGet<{ items: QueueItem[] }>("/v1/nimbus/queue");
          const stillInQueue = q.items.some((i) => i.doc_id === docId);
          if (!stillInQueue) {
            clearInterval(checkDone);
            push(mkMsg("nimbus", "upload-success",
              `File **${res.archived_filename}** sudah berhasil diarsipkan!\n\nPath: \`${res.drive_path}\`\n\nSudah saya notif ke email kamu juga.`,
              { archived_filename: res.archived_filename, drive_path: res.drive_path }
            ));
          }
        } catch {
          clearInterval(checkDone);
        }
      }, 3000);

    } catch (err: unknown) {
      setIsThinking(false);
      const msg = err instanceof Error ? err.message : "Gagal konfirmasi";
      push(mkMsg("nimbus", "text", `Ups, gagal proses: ${msg}`));
    }
  }, [push, startPolling]);

  // ── Search ─────────────────────────────────────────────────────────────────

  const runSearch = useCallback(async (query: string) => {
    setIsThinking(true);
    try {
      const res = await apiGet<{ results: SearchResult[]; total: number }>(
        `/v1/nimbus/search?q=${encodeURIComponent(query)}`
      );
      setIsThinking(false);
      if (res.total === 0) {
        push(mkMsg("nimbus", "text",
          `Hmm, saya cari di database tapi nggak nemu dokumen yang cocok dengan "${query}". Coba keyword lain?`
        ));
        return;
      }
      setPendingSearchResults(res.results);
      push(mkMsg("nimbus", "search-results",
        `Ketemu **${res.total}** dokumen yang mungkin cocok. Yang mana yang kamu mau?`,
        { results: res.results as unknown as Record<string, unknown>[], query }
      ));
    } catch {
      setIsThinking(false);
      push(mkMsg("nimbus", "text", "Gagal search, coba lagi."));
    }
  }, [push]);

  // ── Request access ─────────────────────────────────────────────────────────

  const requestAccess = useCallback(async (docId: string, filename: string) => {
    setIsThinking(true);
    setPendingSearchResults(null);
    try {
      await apiPost(`/v1/nimbus/documents/${docId}/request-access`, {});
      setIsThinking(false);
      push(mkMsg("nimbus", "access-request-sent",
        `Request sudah saya kirim ke email kamu. Begitu di-approve, link download-nya langsung saya kasih di sini.\n\n*Pending approval untuk: **${filename}***`,
        { doc_id: docId, filename }
      ));
    } catch {
      setIsThinking(false);
      push(mkMsg("nimbus", "text", "Gagal kirim request. Coba lagi?"));
    }
  }, [push]);

  // ── Send text message ──────────────────────────────────────────────────────

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    push(mkMsg("user", "text", text));

    // Detect number selection for search results
    if (pendingSearchResults) {
      const numMatch = text.match(/\b(\d+)\b/);
      if (numMatch) {
        const idx = parseInt(numMatch[1], 10) - 1;
        if (idx >= 0 && idx < pendingSearchResults.length) {
          const doc = pendingSearchResults[idx];
          await requestAccess(doc.id, doc.archived_filename);
          return;
        }
      }
      // Non-number reply when search results pending
      if (isSearchQuery(text)) {
        await runSearch(text);
      } else {
        push(mkMsg("nimbus", "text",
          `Pilih nomor dari list di atas (1–${pendingSearchResults.length}), atau ketik pencarian lain kalau mau cari yang lain.`
        ));
      }
      return;
    }

    // Detect search intent
    if (isSearchQuery(text)) {
      await runSearch(text);
      return;
    }

    // Approve keyword
    const lc = text.toLowerCase();
    if (lc === "approve" || lc === "oke" || lc === "ok" || lc === "yes" || lc === "ya") {
      push(mkMsg("nimbus", "text", "Ada yang mau di-approve? Kalau file, klik tombol Approve di proposal card di atas."));
      return;
    }

    // Default Nimbus reply
    push(mkMsg("nimbus", "text",
      `Oke. Kalau mau upload file, drop di sini atau klik lampiran. Kalau mau cari dokumen, ketik "cariin [nama/client/project]".`
    ));
  }, [input, pendingSearchResults, push, requestAccess, runSearch]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div
      className="flex flex-col h-full"
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-pink-500/10 border border-pink-500/20">
            <FolderOpen size={16} className="text-pink-400" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white tracking-tight">Nimbus DCC</h1>
            <p className="text-[10px] text-white/30 font-mono uppercase tracking-widest">Document Control</p>
          </div>
        </div>

        {/* Queue badge */}
        <AnimatePresence>
          {queueItems.length > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20"
            >
              <Loader2 size={12} className="text-amber-400 animate-spin" />
              <span className="text-[10px] font-mono text-amber-400">
                {queueItems.length} dalam queue
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-4 py-6 space-y-4">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onProposalApprove={confirmProposal}
              onProposalCancel={() =>
                push(mkMsg("nimbus", "text", "Oke, proposal dibatalkan. Ada yang lain?"))
              }
              onSelectResult={requestAccess}
            />
          ))}
        </AnimatePresence>

        {/* Thinking indicator */}
        <AnimatePresence>
          {isThinking && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="flex items-end gap-3"
            >
              <div className="w-7 h-7 rounded-full bg-pink-500/20 border border-pink-500/30 flex items-center justify-center shrink-0">
                <span className="text-[10px] font-bold text-pink-400">N</span>
              </div>
              <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-white/5 border border-white/10">
                <div className="flex gap-1.5 items-center h-4">
                  {[0, 0.2, 0.4].map((delay) => (
                    <span
                      key={delay}
                      className="w-1.5 h-1.5 rounded-full bg-pink-400/60 animate-bounce"
                      style={{ animationDelay: `${delay}s` }}
                    />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* Drag overlay */}
      <AnimatePresence>
        {dragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 flex items-center justify-center bg-pink-500/10 border-2 border-dashed border-pink-400/50 rounded-2xl m-4 pointer-events-none"
          >
            <div className="text-center">
              <CloudUpload size={40} className="text-pink-400 mx-auto mb-3" />
              <p className="text-sm font-semibold text-pink-300">Drop file di sini</p>
              <p className="text-xs text-pink-400/60 mt-1">PDF, DOCX, XLSX, PPTX, DWG, STEP</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input bar */}
      <div className="shrink-0 px-4 pb-4 pt-2 border-t border-white/10">
        {/* Pending file chips */}
        <AnimatePresence>
          {pendingFiles.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="flex flex-wrap gap-2 mb-2 overflow-hidden"
            >
              {pendingFiles.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-pink-500/10 border border-pink-500/20 text-xs text-pink-300"
                >
                  <Paperclip size={10} />
                  <span className="max-w-[120px] truncate">{f.name}</span>
                  <button
                    onClick={() => setPendingFiles((prev) => prev.filter((_, j) => j !== i))}
                    className="hover:text-pink-100 transition-colors"
                  >
                    <X size={10} />
                  </button>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-end gap-2 bg-white/5 border border-white/10 rounded-2xl px-4 py-3 focus-within:border-pink-500/30 transition-colors">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-1.5 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/10 transition-all shrink-0 mb-0.5"
            title="Attach file"
          >
            <Paperclip size={16} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.dwg,.step,.stp"
            className="hidden"
            onChange={handleFileChange}
          />
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ketik pesan atau drop file…"
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-white placeholder:text-white/20 outline-none min-h-[24px] max-h-32 leading-relaxed"
            style={{ height: "auto" }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = `${el.scrollHeight}px`;
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() && pendingFiles.length === 0}
            className={cn(
              "p-2 rounded-xl transition-all shrink-0 mb-0.5",
              input.trim() || pendingFiles.length > 0
                ? "bg-pink-500/20 border border-pink-500/30 text-pink-400 hover:bg-pink-500/30"
                : "text-white/10 cursor-not-allowed"
            )}
          >
            <Send size={15} />
          </button>
        </div>
        <p className="text-center text-[10px] text-white/15 mt-2 font-mono">
          Enter kirim · Shift+Enter baris baru · Drop file untuk upload
        </p>
      </div>
    </div>
  );
}

// ── Message bubble ─────────────────────────────────────────────────────────────

interface BubbleProps {
  message: ChatMessage;
  onProposalApprove: (proposalId: string, data: ProposalData) => void;
  onProposalCancel: () => void;
  onSelectResult: (docId: string, filename: string) => void;
}

function MessageBubble({ message, onProposalApprove, onProposalCancel, onSelectResult }: BubbleProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={cn("flex items-end gap-3", isUser && "flex-row-reverse")}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-pink-500/20 border border-pink-500/30 flex items-center justify-center shrink-0">
          <span className="text-[10px] font-bold text-pink-400">N</span>
        </div>
      )}

      <div className={cn("flex flex-col gap-1 max-w-[80%]", isUser && "items-end")}>
        {/* Bubble */}
        {message.type === "text" && (
          <TextBubble content={message.content} isUser={isUser} />
        )}

        {message.type === "file-attach" && (
          <FileAttachBubble filename={message.content} size={message.data?.size as number} />
        )}

        {message.type === "proposal" && message.data && (
          <div className={cn("w-full", isUser && "self-end")}>
            <TextBubble content={message.content} isUser={false} />
            <div className="mt-2">
              <FileProposalCard
                data={message.data as unknown as ProposalData}
                onApprove={onProposalApprove}
                onCancel={onProposalCancel}
              />
            </div>
          </div>
        )}

        {message.type === "search-results" && message.data && (
          <div className="w-full">
            <TextBubble content={message.content} isUser={false} />
            <div className="mt-2">
              <SearchResultsCard
                results={(message.data.results as unknown as SearchResult[]) ?? []}
                onSelect={onSelectResult}
              />
            </div>
          </div>
        )}

        {(message.type === "queue-status" || message.type === "upload-success" || message.type === "upload-failed") && (
          <StatusBubble message={message} />
        )}

        {message.type === "access-request-sent" && (
          <AccessRequestBubble content={message.content} />
        )}

        <span className="text-[10px] text-white/20 px-1">
          {message.timestamp.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </motion.div>
  );
}

function TextBubble({ content, isUser }: { content: string; isUser: boolean }) {
  // Simple markdown: **bold**, *italic*, `code`, \n
  const rendered = content
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, '<code class="bg-white/10 px-1 rounded text-[11px] font-mono">$1</code>')
    .replace(/\n/g, "<br />");

  return (
    <div
      className={cn(
        "px-4 py-3 rounded-2xl text-sm leading-relaxed",
        isUser
          ? "bg-pink-500/20 border border-pink-500/20 text-white rounded-br-sm"
          : "bg-white/5 border border-white/10 text-white/90 rounded-bl-sm"
      )}
      dangerouslySetInnerHTML={{ __html: rendered }}
    />
  );
}

function FileAttachBubble({ filename, size }: { filename: string; size?: number }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2.5 rounded-2xl rounded-br-sm bg-pink-500/10 border border-pink-500/20">
      <div className="p-1.5 rounded-lg bg-pink-500/20">
        <Paperclip size={12} className="text-pink-400" />
      </div>
      <div>
        <p className="text-xs font-medium text-white">{filename}</p>
        {size !== undefined && (
          <p className="text-[10px] text-white/30">{formatBytes(size)}</p>
        )}
      </div>
    </div>
  );
}

function StatusBubble({ message }: { message: ChatMessage }) {
  const isSuccess = message.type === "upload-success";
  const isQueue = message.type === "queue-status";
  const Icon = isSuccess ? CheckCircle2 : isQueue ? Clock : XCircle;
  const color = isSuccess ? "emerald" : isQueue ? "amber" : "rose";

  const rendered = message.content
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, '<code class="bg-white/10 px-1 rounded text-[11px] font-mono">$1</code>')
    .replace(/\n/g, "<br />");

  return (
    <div className={cn(
      "px-4 py-3 rounded-2xl rounded-bl-sm border text-sm leading-relaxed",
      `bg-${color}-500/10 border-${color}-500/20 text-${color}-200`,
    )}>
      <div className="flex items-start gap-2">
        <Icon size={14} className={`text-${color}-400 shrink-0 mt-0.5`} />
        <span dangerouslySetInnerHTML={{ __html: rendered }} />
      </div>
    </div>
  );
}

function AccessRequestBubble({ content }: { content: string }) {
  const rendered = content
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br />");

  return (
    <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-sky-500/10 border border-sky-500/20 text-sky-200 text-sm leading-relaxed">
      <div className="flex items-start gap-2">
        <Clock size={14} className="text-sky-400 shrink-0 mt-0.5" />
        <span dangerouslySetInnerHTML={{ __html: rendered }} />
      </div>
    </div>
  );
}
