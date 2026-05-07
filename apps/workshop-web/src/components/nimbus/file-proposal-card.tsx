"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Check, X, FileText, FolderOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiGet } from "@/lib/api-client";
import type { ClientData, ProjectData, ProposalData } from "./nimbus-types";

const DOC_TYPES = ["PO", "Q", "PL", "QC", "BA", "DRW", "INV", "PROP", "BAST", "MISC"];
const FOLDER_CATS = ["DRW", "QC", "PO", "BA", "PROPOSAL", "INVOICE", "MISC"];

interface Props {
  data: ProposalData;
  clients: ClientData[];
  onApprove: (proposalId: string, data: ProposalData) => void;
  onCancel: () => void;
}

function formatBytes(b: number): string {
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileProposalCard({ data, clients, onApprove, onCancel }: Props) {
  const [form, setForm] = useState<ProposalData>({ ...data });
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [approved, setApproved] = useState(false);
  const [cancelled, setCancelled] = useState(false);

  useEffect(() => {
    if (!form.client_code || form.client_code === "CLIENT") {
      setProjects([]);
      return;
    }
    apiGet<ProjectData[]>(`/v1/nimbus/clients/${form.client_code}/projects`)
      .then(setProjects)
      .catch(() => setProjects([]));
  }, [form.client_code]);

  const handleClientChange = (code: string) => {
    setForm((f) => ({ ...f, client_code: code, project_code: "" }));
  };

  const handleProjectChange = (code: string) => {
    const proj = projects.find((p) => p.code === code);
    setForm((f) => ({
      ...f,
      project_code: code,
      folder_category: proj?.default_folder_category ?? f.folder_category,
    }));
  };

  const previewName = (() => {
    const date = new Date().toLocaleDateString("id-ID", {
      day: "2-digit", month: "2-digit", year: "2-digit",
    }).replace(/\//g, "");
    const stem = data.original_name.replace(/\.[^.]+$/, "").replace(/[^\w\-]/g, "_").slice(0, 40);
    const ext = data.original_name.match(/\.[^.]+$/)?.[0] ?? "";
    return `${form.doc_type}-${String(form.seq_preview).padStart(3, "0")}-${stem}-${date}-${form.version}${ext}`;
  })();

  const handleApprove = () => {
    setApproved(true);
    onApprove(form.proposal_id, form);
  };

  const handleCancel = () => {
    setCancelled(true);
    onCancel();
  };

  if (approved || cancelled) {
    return (
      <div className={cn(
        "px-4 py-2 rounded-xl border text-xs font-medium flex items-center gap-2",
        approved
          ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
          : "bg-white/5 border-white/10 text-white/30"
      )}>
        {approved ? <Check size={12} /> : <X size={12} />}
        {approved ? "Approved — dimasukkan ke queue" : "Dibatalkan"}
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-pink-500/20 bg-pink-500/5 overflow-hidden"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-pink-500/10 flex items-center gap-2">
        <FileText size={14} className="text-pink-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-pink-400/60 font-mono uppercase tracking-widest">File original</p>
          <p className="text-xs text-white/70 truncate">{data.original_name}</p>
        </div>
        <span className="text-[10px] text-white/30 font-mono">{formatBytes(data.file_size)}</span>
      </div>

      {/* Proposed name preview */}
      <div className="px-4 py-3 border-b border-pink-500/10">
        <p className="text-[10px] text-white/30 font-mono uppercase tracking-widest mb-1">Nama arsip</p>
        <p className="text-xs font-mono text-emerald-300 break-all">{previewName}</p>
      </div>

      {/* Editable fields */}
      <div className="px-4 py-3 grid grid-cols-2 gap-3 border-b border-pink-500/10">
        <SelectField
          label="Jenis Dokumen"
          value={form.doc_type}
          onChange={(v) => setForm({ ...form, doc_type: v })}
          options={DOC_TYPES}
        />
        <SelectField
          label="Folder"
          value={form.folder_category}
          onChange={(v) => setForm({ ...form, folder_category: v })}
          options={FOLDER_CATS}
        />

        {/* Client */}
        <div>
          <label className="text-[10px] text-white/30 font-mono uppercase tracking-widest block mb-1">Client</label>
          {clients.length > 0 ? (
            <select
              value={form.client_code}
              onChange={(e) => handleClientChange(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white outline-none focus:border-pink-500/40 transition-colors cursor-pointer"
            >
              <option value="" className="bg-slate-900">— Pilih Client —</option>
              {clients.map((c) => (
                <option key={c.code} value={c.code} className="bg-slate-900">
                  {c.name} ({c.code})
                </option>
              ))}
            </select>
          ) : (
            <input
              value={form.client_code}
              onChange={(e) => handleClientChange(e.target.value.toUpperCase())}
              placeholder="e.g. PERTAMINA"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs font-mono text-white outline-none focus:border-pink-500/40 transition-colors placeholder:text-white/15"
            />
          )}
        </div>

        {/* Project */}
        <div>
          <label className="text-[10px] text-white/30 font-mono uppercase tracking-widest block mb-1">Project</label>
          {projects.length > 0 ? (
            <select
              value={form.project_code}
              onChange={(e) => handleProjectChange(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white outline-none focus:border-pink-500/40 transition-colors cursor-pointer"
            >
              <option value="" className="bg-slate-900">— Pilih Project —</option>
              {projects.map((p) => (
                <option key={p.code} value={p.code} className="bg-slate-900">
                  {p.name}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={form.project_code}
              onChange={(e) => setForm({ ...form, project_code: e.target.value.toUpperCase() })}
              placeholder="e.g. PROJ-001"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs font-mono text-white outline-none focus:border-pink-500/40 transition-colors placeholder:text-white/15"
            />
          )}
        </div>

        <div className="col-span-2 max-w-[120px]">
          <label className="text-[10px] text-white/30 font-mono uppercase tracking-widest block mb-1">Version</label>
          <input
            value={form.version}
            onChange={(e) => setForm({ ...form, version: e.target.value.toUpperCase() })}
            placeholder="V1"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs font-mono text-white outline-none focus:border-pink-500/40 transition-colors placeholder:text-white/15"
          />
        </div>
      </div>

      {/* Drive path preview */}
      <div className="px-4 py-2.5 border-b border-pink-500/10 flex items-center gap-2">
        <FolderOpen size={12} className="text-white/20 shrink-0" />
        <p className="text-[10px] text-white/25 font-mono truncate">
          RAIN-ARCHIVE/CLIENTS/{form.client_code.toUpperCase()}/{form.project_code.toUpperCase()}/{form.folder_category}/
        </p>
      </div>

      {/* Actions */}
      <div className="px-4 py-3 flex items-center gap-2">
        <button
          onClick={handleApprove}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold hover:bg-emerald-500/30 transition-all"
        >
          <Check size={12} />
          Approve
        </button>
        <button
          onClick={handleCancel}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 text-white/30 text-xs hover:text-white/60 hover:border-white/20 transition-all"
        >
          <X size={12} />
          Cancel
        </button>
      </div>
    </motion.div>
  );
}

function SelectField({
  label, value, onChange, options,
}: {
  label: string; value: string; onChange: (v: string) => void; options: string[];
}) {
  return (
    <div>
      <label className="text-[10px] text-white/30 font-mono uppercase tracking-widest block mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white outline-none focus:border-pink-500/40 transition-colors cursor-pointer"
      >
        {options.map((o) => (
          <option key={o} value={o} className="bg-slate-900">{o}</option>
        ))}
      </select>
    </div>
  );
}
