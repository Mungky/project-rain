"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Check, X, ChevronDown, ChevronUp, FileText } from "lucide-react";
import { apiGet } from "@/lib/api-client";
import type { ClientData, ProjectData, ProposalData } from "./nimbus-types";

const DOC_TYPES = ["PO", "Q", "PL", "QC", "BA", "DRW", "INV", "PROP", "BAST", "MISC"];
const FOLDER_CATS = ["DRW", "QC", "PO", "BA", "PROPOSAL", "INVOICE", "MISC"];

interface Props {
  proposals: ProposalData[];
  clients: ClientData[];
  onApproveAll: (proposals: ProposalData[]) => void;
  onCancel: () => void;
}

export function BatchProposalCard({ proposals, clients, onApproveAll, onCancel }: Props) {
  const [items, setItems] = useState<ProposalData[]>(proposals);
  const [cancelled, setCancelled] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [approved, setApproved] = useState(false);

  const activeItems = items.filter((p) => !cancelled.has(p.proposal_id));

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const updateItem = (id: string, patch: Partial<ProposalData>) => {
    setItems((prev) => prev.map((p) => p.proposal_id === id ? { ...p, ...patch } : p));
  };

  const handleApproveAll = () => {
    setApproved(true);
    onApproveAll(activeItems);
  };

  if (approved) {
    return (
      <div className="px-4 py-2 rounded-xl border bg-emerald-500/10 border-emerald-500/20 text-emerald-400 text-xs font-medium flex items-center gap-2">
        <Check size={12} />
        {activeItems.length} file dimasukkan ke queue
      </div>
    );
  }

  if (activeItems.length === 0) {
    return (
      <div className="px-4 py-2 rounded-xl border bg-white/5 border-white/10 text-white/30 text-xs flex items-center gap-2">
        <X size={12} />
        Semua file dibatalkan
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-pink-500/20 bg-pink-500/5 overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-pink-500/10">
        <p className="text-xs font-semibold text-white">{activeItems.length} file siap diarsipkan</p>
        <p className="text-[10px] text-white/30 mt-0.5">Klik ▾ untuk edit, ✕ untuk batalkan per file</p>
      </div>

      <div className="divide-y divide-pink-500/10">
        {items.map((item) => {
          const isCancelled = cancelled.has(item.proposal_id);
          const isExpanded = expanded.has(item.proposal_id);

          if (isCancelled) {
            return (
              <div key={item.proposal_id} className="px-4 py-2.5 flex items-center gap-2 opacity-40">
                <X size={11} className="text-white/30 shrink-0" />
                <p className="text-xs text-white/30 line-through truncate flex-1">{item.original_name}</p>
              </div>
            );
          }

          return (
            <div key={item.proposal_id}>
              <div className="px-4 py-2.5 flex items-center gap-2">
                <FileText size={12} className="text-pink-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-white/80 truncate">{item.original_name}</p>
                  <p className="text-[10px] font-mono text-emerald-300/70 truncate">{item.proposed_name}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => toggleExpand(item.proposal_id)}
                    className="p-1 rounded text-white/30 hover:text-white/60 transition-colors"
                    title="Edit"
                  >
                    {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>
                  <button
                    onClick={() => setCancelled((prev) => new Set([...prev, item.proposal_id]))}
                    className="p-1 rounded text-white/30 hover:text-rose-400 transition-colors"
                    title="Batalkan"
                  >
                    <X size={12} />
                  </button>
                </div>
              </div>

              {isExpanded && (
                <ItemEditor
                  item={item}
                  clients={clients}
                  onChange={(patch) => updateItem(item.proposal_id, patch)}
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="px-4 py-3 flex items-center gap-2 border-t border-pink-500/10">
        <button
          onClick={handleApproveAll}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold hover:bg-emerald-500/30 transition-all"
        >
          <Check size={12} />
          Approve All ({activeItems.length})
        </button>
        <button
          onClick={onCancel}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 text-white/30 text-xs hover:text-white/60 hover:border-white/20 transition-all"
        >
          <X size={12} />
          Batal Semua
        </button>
      </div>
    </motion.div>
  );
}

function ItemEditor({
  item, clients, onChange,
}: {
  item: ProposalData;
  clients: ClientData[];
  onChange: (patch: Partial<ProposalData>) => void;
}) {
  const [projects, setProjects] = useState<ProjectData[]>([]);

  useEffect(() => {
    if (!item.client_code || item.client_code === "CLIENT") {
      setProjects([]);
      return;
    }
    apiGet<ProjectData[]>(`/v1/nimbus/clients/${item.client_code}/projects`)
      .then(setProjects)
      .catch(() => setProjects([]));
  }, [item.client_code]);

  const handleClientChange = (code: string) => {
    onChange({ client_code: code, project_code: "" });
  };

  const handleProjectChange = (code: string) => {
    const proj = projects.find((p) => p.code === code);
    onChange({
      project_code: code,
      folder_category: proj?.default_folder_category ?? item.folder_category,
    });
  };

  const cls = "w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white outline-none focus:border-pink-500/40";

  return (
    <div className="px-4 pb-3 grid grid-cols-2 gap-2 bg-black/10">
      <div>
        <label className="text-[10px] text-white/20 font-mono uppercase tracking-widest block mb-1">Doc Type</label>
        <select value={item.doc_type} onChange={(e) => onChange({ doc_type: e.target.value })} className={cls}>
          {DOC_TYPES.map((o) => <option key={o} value={o} className="bg-slate-900">{o}</option>)}
        </select>
      </div>
      <div>
        <label className="text-[10px] text-white/20 font-mono uppercase tracking-widest block mb-1">Folder</label>
        <select value={item.folder_category} onChange={(e) => onChange({ folder_category: e.target.value })} className={cls}>
          {FOLDER_CATS.map((o) => <option key={o} value={o} className="bg-slate-900">{o}</option>)}
        </select>
      </div>
      <div>
        <label className="text-[10px] text-white/20 font-mono uppercase tracking-widest block mb-1">Client</label>
        {clients.length > 0 ? (
          <select value={item.client_code} onChange={(e) => handleClientChange(e.target.value)} className={cls}>
            <option value="" className="bg-slate-900">— Pilih —</option>
            {clients.map((c) => (
              <option key={c.code} value={c.code} className="bg-slate-900">{c.name}</option>
            ))}
          </select>
        ) : (
          <input
            value={item.client_code}
            onChange={(e) => handleClientChange(e.target.value.toUpperCase())}
            className={cls}
          />
        )}
      </div>
      <div>
        <label className="text-[10px] text-white/20 font-mono uppercase tracking-widest block mb-1">Project</label>
        {projects.length > 0 ? (
          <select value={item.project_code} onChange={(e) => handleProjectChange(e.target.value)} className={cls}>
            <option value="" className="bg-slate-900">— Pilih —</option>
            {projects.map((p) => (
              <option key={p.code} value={p.code} className="bg-slate-900">{p.name}</option>
            ))}
          </select>
        ) : (
          <input
            value={item.project_code}
            onChange={(e) => onChange({ project_code: e.target.value.toUpperCase() })}
            className={cls}
          />
        )}
      </div>
    </div>
  );
}
