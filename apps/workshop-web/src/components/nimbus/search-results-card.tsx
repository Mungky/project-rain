"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { File, FolderOpen, Lock, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

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

const DOC_TYPE_COLORS: Record<string, string> = {
  PO:   "bg-blue-500/20 text-blue-300 border-blue-500/20",
  INV:  "bg-amber-500/20 text-amber-300 border-amber-500/20",
  DRW:  "bg-violet-500/20 text-violet-300 border-violet-500/20",
  QC:   "bg-emerald-500/20 text-emerald-300 border-emerald-500/20",
  PROP: "bg-pink-500/20 text-pink-300 border-pink-500/20",
  BA:   "bg-sky-500/20 text-sky-300 border-sky-500/20",
  MISC: "bg-white/10 text-white/40 border-white/10",
};

interface Props {
  results: SearchResult[];
  onSelect: (docId: string, filename: string) => void;
}

export function SearchResultsCard({ results, onSelect }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSelect = (doc: SearchResult) => {
    setSelected(doc.id);
    onSelect(doc.id, doc.archived_filename);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-sky-500/20 bg-sky-500/5 overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-sky-500/10 flex items-center gap-2">
        <FolderOpen size={14} className="text-sky-400" />
        <span className="text-[10px] text-sky-400/80 font-mono uppercase tracking-widest">
          {results.length} dokumen ditemukan — pilih nomor
        </span>
      </div>

      <div className="divide-y divide-white/5">
        {results.map((doc, i) => {
          const typeColor = DOC_TYPE_COLORS[doc.doc_type] ?? DOC_TYPE_COLORS.MISC;
          const isSelected = selected === doc.id;

          return (
            <motion.button
              key={doc.id}
              onClick={() => handleSelect(doc)}
              disabled={selected !== null}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-3 text-left transition-all",
                selected === null
                  ? "hover:bg-white/5 cursor-pointer"
                  : isSelected
                  ? "bg-sky-500/10"
                  : "opacity-40 cursor-not-allowed",
              )}
            >
              {/* Number badge */}
              <div className={cn(
                "w-6 h-6 rounded-full border flex items-center justify-center shrink-0 text-[10px] font-bold font-mono",
                isSelected
                  ? "bg-sky-500/30 border-sky-500/40 text-sky-300"
                  : "bg-white/5 border-white/15 text-white/30"
              )}>
                {i + 1}
              </div>

              {/* File icon */}
              <div className="p-1.5 rounded-lg bg-white/5 shrink-0">
                <File size={12} className="text-white/30" />
              </div>

              {/* Info — filename is blurred for access control effect */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <p
                    className={cn(
                      "text-xs font-mono text-white/80 truncate transition-all",
                      !isSelected && selected === null && "blur-[3px] select-none"
                    )}
                    title={isSelected ? doc.archived_filename : ""}
                  >
                    {doc.archived_filename}
                  </p>
                  {!isSelected && selected === null && (
                    <Lock size={10} className="text-white/20 shrink-0" />
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn("px-1.5 py-0.5 rounded border text-[10px] font-bold font-mono", typeColor)}>
                    {doc.doc_type}
                  </span>
                  <span className="text-[10px] text-white/30 font-mono">
                    {doc.client_code} / {doc.project_code}
                  </span>
                  <span className="text-[10px] text-white/20">
                    {new Date(doc.created_at).toLocaleDateString("id-ID")}
                  </span>
                </div>
              </div>

              {selected === null && (
                <ChevronRight size={14} className="text-white/20 shrink-0" />
              )}
            </motion.button>
          );
        })}
      </div>

      {selected === null && (
        <div className="px-4 py-2 border-t border-white/5">
          <p className="text-[10px] text-white/20 text-center">
            Ketik nomor di chat atau klik langsung · Nama file disembunyikan sampai diapprove
          </p>
        </div>
      )}
    </motion.div>
  );
}
