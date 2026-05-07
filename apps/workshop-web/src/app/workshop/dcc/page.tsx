"use client";

import { GlassPanel } from "@/components/identity/glass-panel";
import { motion } from "framer-motion";
import { FolderOpen, Upload, Clock, CheckCircle2, XCircle, AlertCircle, File } from "lucide-react";
import { useEffect, useState } from "react";
import { useUIStore } from "@/stores/ui-store";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface NimbusDocument {
  id: string;
  original_filename: string;
  archived_filename: string;
  doc_type: string;
  client_code: string;
  project_code: string;
  folder_category: string;
  drive_path: string;
  drive_file_id: string | null;
  status: "pending" | "archived" | "failed";
  uploaded_by: string;
  version: string;
  created_at: string;
}

const STATUS_CONFIG = {
  pending:  { icon: Clock,        color: "text-amber-400",  bg: "bg-amber-500/10 border-amber-500/20",  label: "Pending" },
  archived: { icon: CheckCircle2, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20", label: "Archived" },
  failed:   { icon: XCircle,      color: "text-rose-400",   bg: "bg-rose-500/10 border-rose-500/20",    label: "Failed" },
};

const FOLDER_LABELS: Record<string, string> = {
  DRW: "Drawing", QC: "QC", PO: "Purchase Order", BA: "Berita Acara",
  PROPOSAL: "Proposal", INVOICE: "Invoice", MISC: "Misc",
};

export default function DCCPage() {
  const setShowRain = useUIStore((s) => s.setShowRain);
  const [docs, setDocs] = useState<NimbusDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "pending" | "archived" | "failed">("all");

  useEffect(() => { setShowRain(true); }, [setShowRain]);

  useEffect(() => {
    apiGet<{ documents: NimbusDocument[] }>("/v1/nimbus/documents")
      .then((r) => setDocs(r.documents))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === "all" ? docs : docs.filter((d) => d.status === filter);

  const counts = {
    all: docs.length,
    pending: docs.filter((d) => d.status === "pending").length,
    archived: docs.filter((d) => d.status === "archived").length,
    failed: docs.filter((d) => d.status === "failed").length,
  };

  return (
    <div className="flex-1 flex flex-col p-8 overflow-y-auto relative z-10 custom-scrollbar">
      {/* Header */}
      <motion.header initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <div className="flex items-center gap-3 text-white/30 mb-3">
          <FolderOpen size={16} />
          <span className="text-xs font-mono uppercase tracking-[0.2em]">Workshop · DCC</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tighter text-white">
          Document Control <span className="text-white/50">Center</span>
        </h1>
        <p className="text-sm text-white/30 mt-2">
          Semua dokumen yang diarsipkan Nimbus ke Google Drive.
        </p>
      </motion.header>

      {/* Stats */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-4 gap-4 mb-8"
      >
        {(["all", "pending", "archived", "failed"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={cn(
              "p-4 rounded-2xl border text-left transition-all",
              filter === s ? "bg-white text-black border-white" : "bg-white/5 border-white/10 hover:border-white/20"
            )}
          >
            <p className={cn("text-2xl font-bold font-mono", filter === s ? "text-black" : "text-white")}>
              {counts[s]}
            </p>
            <p className={cn("text-[10px] uppercase tracking-[0.2em] font-bold mt-1", filter === s ? "text-black/60" : "text-white/30")}>
              {s === "all" ? "Total" : s}
            </p>
          </button>
        ))}
      </motion.div>

      {/* Document List */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
        <GlassPanel className="border-white/10 bg-white/5 backdrop-blur-3xl overflow-hidden">
          {loading ? (
            <div className="p-8 space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-14 rounded-xl bg-white/5 animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="p-16 flex flex-col items-center gap-4 text-center">
              <div className="p-4 rounded-2xl bg-white/5">
                <Upload size={32} className="text-white/20" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white/40">Belum ada dokumen</p>
                <p className="text-xs text-white/20 mt-1">
                  Dokumen yang diupload user lewat Nimbus akan muncul di sini.
                </p>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {/* Table header */}
              <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr] gap-4 px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] text-white/20">
                <span>File</span>
                <span>Tipe</span>
                <span>Client / Project</span>
                <span>Folder</span>
                <span>Status</span>
                <span>Diupload</span>
              </div>

              {filtered.map((doc, i) => {
                const st = STATUS_CONFIG[doc.status];
                const StatusIcon = st.icon;
                return (
                  <motion.div
                    key={doc.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr] gap-4 px-6 py-4 items-center hover:bg-white/[0.02] transition-all"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="p-1.5 rounded-lg bg-white/5 shrink-0">
                        <File size={14} className="text-white/40" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-white truncate">{doc.archived_filename}</p>
                        <p className="text-[10px] text-white/30 truncate">{doc.original_filename}</p>
                      </div>
                    </div>
                    <span className="text-xs font-mono text-white/50 uppercase">{doc.doc_type}</span>
                    <div>
                      <p className="text-xs font-mono text-white/70">{doc.client_code}</p>
                      <p className="text-[10px] text-white/30">{doc.project_code}</p>
                    </div>
                    <span className="text-xs text-white/40">{FOLDER_LABELS[doc.folder_category] ?? doc.folder_category}</span>
                    <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded-full border text-[10px] font-bold w-fit", st.bg)}>
                      <StatusIcon size={10} className={st.color} />
                      <span className={st.color}>{st.label}</span>
                    </div>
                    <div>
                      <p className="text-xs text-white/40">{doc.uploaded_by}</p>
                      <p className="text-[10px] text-white/20 font-mono">
                        {new Date(doc.created_at).toLocaleDateString("id-ID")}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </GlassPanel>
      </motion.div>
    </div>
  );
}
