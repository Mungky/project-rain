"use client";

import { useUIStore } from "@/stores/ui-store";
import { GlassPanel } from "@/components/identity/glass-panel";
import { motion, AnimatePresence } from "framer-motion";
import { useDocuments, useDeleteDocument, useDownloadDocument } from "@/hooks/use-documents";
import { useSkills } from "@/hooks/use-skills";
import { useUsage } from "@/hooks/use-user-preferences";
import {
  useContextLibrary,
  useCreateContextEntry,
  useUpdateContextEntry,
  useDeleteContextEntry,
} from "@/hooks/use-context-library";
import type { MessageResponse, ContextEntryResponse, UsagePeriod } from "@/lib/api-types";
import { useShallow } from "zustand/react/shallow";
import { useState } from "react";
import {
  BarChart3,
  Brain,
  Database,
  X,
  ChevronLeft,
  Wrench,
  Search,
  Plus,
  Pencil,
  Trash2,
  Check,
  ChevronDown,
  Download,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";

type InfoTab = "usage" | "skills" | "context" | "kb";

// ── Pricing helpers ──────────────────────────────────────────────────────────

const IDR_PER_USD = 16_200;

function getModelPricing(model: string | null): { in: number; out: number } {
  if (!model) return { in: 0, out: 0 };
  const m = model.toLowerCase();
  if (m.includes("opus"))          return { in: 15, out: 75 };
  if (m.includes("sonnet"))        return { in: 3, out: 15 };
  if (m.includes("haiku"))         return { in: 0.25, out: 1.25 };
  if (m.includes("gpt-4o-mini"))   return { in: 0.15, out: 0.6 };
  if (m.includes("gpt-4o"))        return { in: 5, out: 15 };
  if (m.includes("gpt-4"))         return { in: 10, out: 30 };
  if (m.includes("gpt-3.5"))       return { in: 0.5, out: 1.5 };
  if (m.includes("gemini"))        return { in: 0.075, out: 0.3 };
  return { in: 0, out: 0 }; // ollama / local = free
}

function formatIDR(idr: number): string {
  if (idr < 1) return "< Rp 1";
  return `Rp ${Math.round(idr).toLocaleString("id-ID")}`;
}

// ── Panel ────────────────────────────────────────────────────────────────────

export function InfoPanel() {
  const { infoPanelOpen, toggleInfoPanel } = useUIStore(
    useShallow((s) => ({
      infoPanelOpen: s.infoPanelOpen,
      toggleInfoPanel: s.toggleInfoPanel,
    }))
  );

  const [activeTab, setActiveTab] = useState<InfoTab>("usage");
  const [skillSearch, setSkillSearch] = useState("");
  const [usagePeriod, setUsagePeriod] = useState<UsagePeriod>("all");

  const { data: docs } = useDocuments({ refetchInterval: 5000 });
  const { data: availableSkills } = useSkills({ refetchInterval: 10000 });
  const { data: globalUsage } = useUsage(usagePeriod, { refetchInterval: 5000 });
  
  const deleteDoc = useDeleteDocument();
  const downloadDoc = useDownloadDocument();

  // Global totals
  const totalIn = globalUsage?.total_tokens_in ?? 0;
  const totalOut = globalUsage?.total_tokens_out ?? 0;
  const totalTokens = totalIn + totalOut;

  const totalCostIDR = (globalUsage?.by_model ?? []).reduce((acc, entry) => {
    const p = getModelPricing(entry.model);
    return acc + ((entry.tokens_in / 1_000_000) * p.in + (entry.tokens_out / 1_000_000) * p.out) * IDR_PER_USD;
  }, 0);

  const filteredSkills = availableSkills?.filter((s) =>
    s.name.toLowerCase().includes(skillSearch.toLowerCase()) ||
    s.description.toLowerCase().includes(skillSearch.toLowerCase())
  );

  const tabs = [
    { id: "usage",   label: "Usage",   icon: BarChart3 },
    { id: "skills",  label: "Skills",  icon: Wrench },
    { id: "context", label: "Context", icon: Brain },
    { id: "kb",      label: "Library", icon: Database },
  ];

  return (
    <motion.div
      initial={false}
      animate={{ width: infoPanelOpen ? 320 : 56 }}
      transition={{ type: "spring", damping: 25, stiffness: 200 }}
      className="h-full overflow-hidden shrink-0"
    >
      <GlassPanel className="h-full w-full flex flex-col overflow-hidden border-l border-white/20 rounded-2xl bg-white/5 backdrop-blur-2xl">
        {/* Header */}
        <div className={cn(
          "flex items-center justify-between border-b border-white/10 transition-all duration-300",
          infoPanelOpen ? "p-4" : "p-2 flex-col h-full border-b-0 pb-6"
        )}>
          {infoPanelOpen ? (
            <>
              <div className="flex gap-1 p-1 bg-white/5 rounded-xl border border-white/5 overflow-x-auto no-scrollbar max-w-[240px]">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as InfoTab)}
                    className={`p-2 rounded-lg transition-all shrink-0 ${
                      activeTab === tab.id
                        ? "bg-white text-black shadow-lg"
                        : "text-white/40 hover:text-white hover:bg-white/5"
                    }`}
                    title={tab.label}
                  >
                    <tab.icon size={16} strokeWidth={2} />
                  </button>
                ))}
              </div>
              <button
                onClick={toggleInfoPanel}
                className="p-2 rounded-lg text-white/20 hover:text-white hover:bg-white/5 transition-colors"
              >
                <X size={18} />
              </button>
            </>
          ) : (
            <>
              <button
                onClick={toggleInfoPanel}
                className="p-2 rounded-xl text-white/40 hover:text-white bg-white/5 border border-white/10 hover:bg-white/10 transition-all mb-8 shadow-lg"
                title="Expand Panel"
              >
                <ChevronLeft size={20} />
              </button>
              <div className="flex flex-col gap-4 mt-auto">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => { setActiveTab(tab.id as InfoTab); toggleInfoPanel(); }}
                    className={cn(
                      "p-2.5 rounded-xl transition-all",
                      activeTab === tab.id
                        ? "text-white bg-white/10 border border-white/10"
                        : "text-white/20 hover:text-white hover:bg-white/5"
                    )}
                    title={tab.label}
                  >
                    <tab.icon size={18} strokeWidth={2} />
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Content */}
        <div className={cn(
          "flex-1 overflow-y-auto no-scrollbar p-6 transition-opacity duration-200",
          infoPanelOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}>
          <AnimatePresence mode="wait">

            {/* ── Usage ── */}
            {activeTab === "usage" && infoPanelOpen && (
              <motion.div
                key="usage"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="space-y-6"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Global Metrics</h3>
                    <p className="text-xs text-white/40 mt-0.5">Total resource consumption.</p>
                  </div>
                  <div className="flex bg-white/5 rounded-lg p-0.5 border border-white/5">
                    {(["all", "today"] as UsagePeriod[]).map((p) => (
                      <button
                        key={p}
                        onClick={() => setUsagePeriod(p)}
                        className={cn(
                          "px-2 py-1 rounded-md text-[10px] font-bold transition-all",
                          usagePeriod === p ? "bg-white text-black shadow-lg" : "text-white/30 hover:text-white/60"
                        )}
                      >
                        {p.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-white/40">Inbound</span>
                    <span className="font-mono text-white/80">{totalIn.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/40">Outbound</span>
                    <span className="font-mono text-white/80">{totalOut.toLocaleString()}</span>
                  </div>
                  <div className="pt-3 border-t border-white/5 flex justify-between text-sm font-bold">
                    <span className="text-white/60">Total Tokens</span>
                    <span className="font-mono text-white">{totalTokens.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-white/40">Neural Threads</span>
                    <span className="font-mono text-white/80">{globalUsage?.total_conversations ?? 0}</span>
                  </div>
                  <div className="flex justify-between text-sm font-bold text-emerald-400/80">
                    <span className="opacity-60">Est. Cost</span>
                    <span className="font-mono">{formatIDR(totalCostIDR)}</span>
                  </div>
                </div>

                {(globalUsage?.by_model ?? []).length > 0 && (
                  <div className="space-y-4 pt-2 border-t border-white/5">
                    <p className="text-[9px] font-bold text-white/20 uppercase tracking-[0.2em]">By Model</p>
                    {globalUsage?.by_model.map((entry) => {
                      const tokens = entry.tokens_in + entry.tokens_out;
                      const pct = totalTokens > 0 ? (tokens / totalTokens) * 100 : 0;
                      const p = getModelPricing(entry.model);
                      const costIDR = ((entry.tokens_in / 1_000_000) * p.in + (entry.tokens_out / 1_000_000) * p.out) * IDR_PER_USD;
                      const label = entry.model.length > 26 ? entry.model.slice(0, 24) + "…" : entry.model;
                      return (
                        <div key={entry.model} className="space-y-1.5">
                          <div className="flex justify-between items-baseline gap-2">
                            <span className="text-[10px] font-mono text-white/50 truncate">{label}</span>
                            <span className="text-[10px] font-mono text-white/25 shrink-0">{pct.toFixed(0)}%</span>
                          </div>
                          <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                            <motion.div
                              className="h-full rounded-full bg-white/40"
                              initial={{ width: 0 }}
                              animate={{ width: `${pct}%` }}
                              transition={{ duration: 0.6, ease: "easeOut" }}
                            />
                          </div>
                          {costIDR >= 1 && (
                            <p className="text-[9px] text-white/20 font-mono text-right">{formatIDR(costIDR)}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </motion.div>
            )}

            {/* ── Skills ── */}
            {activeTab === "skills" && infoPanelOpen && (
              <motion.div
                key="skills"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Skill Control</h3>
                  <p className="text-xs text-white/40 mt-0.5">Active capabilities.</p>
                </div>

                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" size={14} />
                  <input
                    type="text"
                    placeholder="Search skills..."
                    value={skillSearch}
                    onChange={(e) => setSkillSearch(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-9 pr-4 text-xs text-white placeholder:text-white/20 focus:outline-none focus:border-white/20 transition-all"
                  />
                </div>

                <div className="space-y-2">
                  {!filteredSkills?.length && (
                    <p className="text-xs text-white/20 italic text-center py-4">No skills installed.</p>
                  )}
                  {filteredSkills?.map((skill) => (
                    <div
                      key={skill.id}
                      className="p-3 rounded-xl border border-white/5 bg-white/[0.02] hover:border-white/10 transition-all"
                    >
                      <p className="text-xs font-semibold text-white">{skill.name}</p>
                      <p className="text-[10px] text-white/30 truncate mt-0.5">{skill.description}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* ── Context ── */}
            {activeTab === "context" && infoPanelOpen && (
              <motion.div
                key="context"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
              >
                <ContextLibrary />
              </motion.div>
            )}

            {/* ── KB ── */}
            {activeTab === "kb" && infoPanelOpen && (
              <motion.div
                key="kb"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Neural Archive</h3>
                  <p className="text-xs text-white/40 mt-0.5">Connected knowledge sources.</p>
                </div>
                <div className="space-y-2">
                  {docs?.documents.length === 0 && (
                    <p className="text-xs text-white/20 italic">No external fragments indexed.</p>
                  )}
                  {docs?.documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center gap-3 text-xs p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/15 transition-all group"
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-white/20 shrink-0" />
                      <span className="truncate flex-1 text-white/50 group-hover:text-white/80 transition-colors">
                        {doc.filename}
                      </span>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                        <button
                          onClick={() => downloadDoc.mutate({ id: doc.id, filename: doc.filename })}
                          disabled={downloadDoc.isPending}
                          className="p-1 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-all"
                          title="Download"
                        >
                          <Download size={12} />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Delete "${doc.filename}"?`)) deleteDoc.mutate(doc.id);
                          }}
                          className="p-1 rounded-lg text-white/40 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                          title="Delete"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </GlassPanel>
    </motion.div>
  );
}

// ── Category helpers ──────────────────────────────────────────────────────────

const CATEGORY_COLORS: Record<string, string> = {
  Brand:       "bg-violet-500/20 text-violet-300 border-violet-500/20",
  Market:      "bg-blue-500/20 text-blue-300 border-blue-500/20",
  Product:     "bg-emerald-500/20 text-emerald-300 border-emerald-500/20",
  Demographic: "bg-amber-500/20 text-amber-300 border-amber-500/20",
  Technical:   "bg-cyan-500/20 text-cyan-300 border-cyan-500/20",
  Personal:    "bg-rose-500/20 text-rose-300 border-rose-500/20",
};

const CATEGORY_ICONS: Record<string, string> = {
  Brand:       "🎨",
  Market:      "📊",
  Product:     "📦",
  Demographic: "👥",
  Technical:   "⚙️",
  Personal:    "👤",
};

const DEFAULT_CATEGORIES = ["Brand", "Market", "Product", "Demographic", "Technical", "Personal"];

function getCategoryStyle(cat: string | null) {
  return CATEGORY_COLORS[cat ?? ""] ?? "bg-white/10 text-white/50 border-white/10";
}

function getCategoryIcon(cat: string | null) {
  return CATEGORY_ICONS[cat ?? ""] ?? "📌";
}

// ── Compact Entry Card ────────────────────────────────────────────────────────

interface EntryCardProps {
  entry: ContextEntryResponse;
}

function CompactEntryCard({ entry }: EntryCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(entry.title);
  const [content, setContent] = useState(entry.content);
  const [category, setCategory] = useState(entry.category ?? "");
  const [subcategory, setSubcategory] = useState(entry.subcategory ?? "");

  const updateMut = useUpdateContextEntry(entry.id);
  const deleteMut = useDeleteContextEntry();

  const handleSave = () => {
    updateMut.mutate({ title, content, category: category || null, subcategory: subcategory || null });
    setEditing(false);
  };

  const handleDelete = () => {
    if (confirm(`Delete "${entry.title}"?`)) deleteMut.mutate(entry.id);
  };

  if (editing) {
    return (
      <div className="py-2.5 px-1 space-y-2.5 border-b border-white/[0.05] last:border-0">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full bg-white/10 border border-white/10 rounded-xl px-3 py-1.5 text-xs font-semibold text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
          placeholder="Title"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={3}
          className="w-full bg-white/10 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white/80 placeholder:text-white/30 resize-none focus:outline-none focus:border-white/30"
          placeholder="Content..."
        />
        <div className="grid grid-cols-2 gap-2">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-white/10 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white/70 focus:outline-none focus:border-white/30"
          >
            <option value="">No category</option>
            {DEFAULT_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <input
            value={subcategory}
            onChange={(e) => setSubcategory(e.target.value)}
            className="bg-white/10 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white/70 placeholder:text-white/30 focus:outline-none focus:border-white/30"
            placeholder="Subcategory"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-xl bg-white text-black text-xs font-semibold hover:bg-white/90 transition-all"
          >
            <Check size={11} /> Save
          </button>
          <button
            onClick={() => setEditing(false)}
            className="flex-1 py-1.5 rounded-xl bg-white/5 text-white/50 text-xs hover:bg-white/10 transition-all"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-b border-white/[0.05] last:border-0">
      <button
        className="w-full flex items-center gap-2.5 py-2.5 px-1 hover:bg-white/[0.03] rounded-xl transition-all text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-sm shrink-0 leading-none">{getCategoryIcon(entry.category)}</span>
        <p className="flex-1 text-xs font-medium text-white/80 truncate">{entry.title}</p>
        {entry.category && (
          <span className={cn("text-[8px] font-bold uppercase px-1.5 py-0.5 rounded-full border shrink-0", getCategoryStyle(entry.category))}>
            {entry.category}
          </span>
        )}
        <ChevronDown
          size={11}
          className={cn("text-white/20 shrink-0 transition-transform duration-200", expanded && "rotate-180")}
        />
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-1 pb-3 space-y-2">
              <p className="text-[11px] text-white/45 leading-relaxed">{entry.content}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {entry.subcategory && (
                    <span className="text-[9px] text-white/20 uppercase tracking-widest">{entry.subcategory}</span>
                  )}
                  <span className="text-[9px] text-white/15 capitalize">{entry.source_type}</span>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditing(true); setExpanded(false); }}
                    className="p-1 rounded-lg text-white/30 hover:text-white hover:bg-white/10 transition-all"
                  >
                    <Pencil size={11} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(); }}
                    className="p-1 rounded-lg text-white/30 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Context Library ───────────────────────────────────────────────────────────

function ContextLibrary() {
  const [search, setSearch] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [newSubcategory, setNewSubcategory] = useState("");

  const { data: entries = [], isLoading } = useContextLibrary(undefined, { refetchInterval: 5000 });
  const createMut = useCreateContextEntry();

  // Sort by created_at descending (newest first)
  const sortedEntries = [...entries].sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const filtered = search.trim()
    ? sortedEntries.filter((e) => {
        const q = search.toLowerCase();
        return (
          e.title.toLowerCase().includes(q) ||
          e.content.toLowerCase().includes(q) ||
          (e.category?.toLowerCase().includes(q) ?? false)
        );
      })
    : sortedEntries;

  const handleCreate = () => {
    if (!newTitle.trim() || !newContent.trim()) return;
    createMut.mutate(
      {
        title: newTitle.trim(),
        content: newContent.trim(),
        category: newCategory || null,
        subcategory: newSubcategory || null,
        source_type: "manual",
      },
      {
        onSuccess: () => {
          setNewTitle(""); setNewContent(""); setNewCategory(""); setNewSubcategory("");
          setShowAddForm(false);
        },
      }
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">Neural Context</h3>
          <p className="text-xs text-white/40 mt-0.5">{entries.length} fragment{entries.length !== 1 ? "s" : ""}</p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className={cn(
            "p-2 rounded-xl transition-all border",
            showAddForm
              ? "bg-white text-black border-white"
              : "text-white/40 border-white/10 hover:text-white hover:bg-white/10"
          )}
          title="Add fragment"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" size={13} />
        <input
          type="text"
          placeholder="Search fragments..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-xl py-2 pl-8 pr-4 text-xs text-white placeholder:text-white/20 focus:outline-none focus:border-white/20 transition-all"
        />
      </div>

      {/* Add form */}
      <AnimatePresence>
        {showAddForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 rounded-2xl bg-white/[0.06] border border-white/15 space-y-3">
              <p className="text-[10px] font-bold text-white/40 uppercase tracking-widest">New Fragment</p>
              <input
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="w-full bg-white/10 border border-white/10 rounded-xl px-3 py-2 text-sm font-semibold text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
                placeholder="Title"
              />
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                rows={3}
                className="w-full bg-white/10 border border-white/10 rounded-xl px-3 py-2 text-xs text-white/80 placeholder:text-white/30 resize-none focus:outline-none focus:border-white/30"
                placeholder="Content..."
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="bg-white/10 border border-white/10 rounded-xl px-3 py-2 text-xs text-white/70 focus:outline-none focus:border-white/30"
                >
                  <option value="">No category</option>
                  {DEFAULT_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <input
                  value={newSubcategory}
                  onChange={(e) => setNewSubcategory(e.target.value)}
                  className="bg-white/10 border border-white/10 rounded-xl px-3 py-2 text-xs text-white/70 placeholder:text-white/30 focus:outline-none focus:border-white/30"
                  placeholder="Subcategory"
                />
              </div>
              <button
                onClick={handleCreate}
                disabled={!newTitle.trim() || !newContent.trim() || createMut.isPending}
                className="w-full py-2.5 rounded-xl bg-white text-black text-xs font-bold hover:bg-white/90 disabled:opacity-40 transition-all"
              >
                {createMut.isPending ? "Saving..." : "Save Fragment"}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Entry list */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-9 rounded-xl bg-white/[0.03] animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-6 text-center">
          <p className="text-xs text-white/20 italic">
            {search ? "No fragments match your search." : "No context fragments yet."}
          </p>
        </div>
      ) : (
        <div>
          {filtered.map((entry) => (
            <CompactEntryCard key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
