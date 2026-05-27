"use client";

import { useUIStore } from "@/stores/ui-store";
import { GlassPanel } from "@/components/identity/glass-panel";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, useRef } from "react";
import {
  useUserPreferences,
  useUpdateUserPreferences
} from "@/hooks/use-user-preferences";
import { useModels, modelKeys, usePingModel } from "@/hooks/use-models";
import {
  useSkills,
  useInstallSkill,
  useUninstallSkill
} from "@/hooks/use-skills";
import {
  useDocuments,
  useUploadDocument,
  useDeleteDocument
} from "@/hooks/use-documents";
import {
  useModelCapabilities,
  useUpsertModelCapabilities,
  useDeleteModelCapability,
  useUpdateModelTags,
} from "@/hooks/use-prompts";
import { useQueryClient } from "@tanstack/react-query";
import type { Persona, ModelTag } from "@/lib/api-types";
import { MODEL_TAG_LABELS, getTagsForPersona } from "@/lib/api-types";
import {
  Plus,
  Trash2,
  Globe,
  Cpu,
  Database,
  Upload,
  FileText,
  Loader2,
  Check,
  Eye,
  EyeOff,
  Brain,
  Layers,
  Wifi,
  WifiOff,
  Cloud,
  Droplets,
  Zap,
  Tag,
} from "lucide-react";

type TabId = "api" | "models" | "skills" | "kb" | "baseline";

type RegisterPersona = Persona;

function detectProvider(modelId: string): string {
  const id = modelId.toLowerCase();
  if (id.startsWith("gemini")) return "google";
  if (id.startsWith("claude")) return "anthropic";
  if (id.startsWith("gpt-") || id.startsWith("dall-e-") || id.startsWith("o3") || id.startsWith("o4")) return "openai";
  return "ollama";
}

const PERSONA_SECTIONS: { id: RegisterPersona; label: string; icon: React.ElementType; color: string; subtitle: string }[] = [
  { id: "drizzle", label: "Drizzle",  icon: Cloud,     color: "text-sky-400",    subtitle: "Chat & Tools" },
  { id: "shower",  label: "Shower",   icon: Droplets,  color: "text-emerald-400", subtitle: "Quick Reply" },
  { id: "storm",   label: "Storm",    icon: Zap,       color: "text-amber-400",  subtitle: "Deep Execute" },
];

export function SettingsModal() {
  const { settingsOpen, toggleSettings } = useUIStore();
  const [activeTab, setActiveTab] = useState<TabId>("api");
  const [gitUrl, setGitUrl] = useState("");

  // API Hooks
  const { data: prefs } = useUserPreferences();
  const updatePrefs = useUpdateUserPreferences();
  const { data: models } = useModels();
  const queryClient = useQueryClient();

  // Skill Hooks
  const { data: skills, isLoading: skillsLoading } = useSkills();
  const installSkill = useInstallSkill();
  const uninstallSkill = useUninstallSkill();

  // KB Hooks
  const { data: docs, isLoading: docsLoading } = useDocuments();
  const uploadDoc = useUploadDocument();
  const deleteDoc = useDeleteDocument();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Model capability hooks
  const { data: capOverrides } = useModelCapabilities();
  const upsertCaps = useUpsertModelCapabilities();
  const deleteCap = useDeleteModelCapability();
  const updateTags = useUpdateModelTags();
  const pingModel = usePingModel();

  // Baseline state
  const [baselinePrompt, setBaselinePrompt] = useState(prefs?.custom_system_prompt || "");

  useEffect(() => {
    if (prefs?.custom_system_prompt !== undefined) {
      setBaselinePrompt(prefs.custom_system_prompt || "");
    }
  }, [prefs?.custom_system_prompt]);

  const handleSaveBaseline = () => {
    if (baselinePrompt !== prefs?.custom_system_prompt) {
      updatePrefs.mutate({ custom_system_prompt: baselinePrompt });
    }
  };

  type ProviderName = "anthropic" | "openai" | "google" | "ollama";

  const OLLAMA_CLOUD_URL = "https://ollama.com";

  const [providerForm, setProviderForm] = useState<Record<ProviderName, { key: string; base_url: string }>>({
    anthropic: { key: "", base_url: "" },
    openai:    { key: "", base_url: "" },
    google:    { key: "", base_url: "" },
    ollama:    { key: "", base_url: OLLAMA_CLOUD_URL },
  });
  const [showKeys, setShowKeys] = useState<Record<ProviderName, boolean>>({
    anthropic: false, openai: false, google: false, ollama: false,
  });
  const [savedProvider, setSavedProvider] = useState<ProviderName | null>(null);

  useEffect(() => {
    if (prefs?.providers) {
      setProviderForm({
        anthropic: { key: prefs.providers.anthropic.key ?? "", base_url: "" },
        openai:    { key: prefs.providers.openai.key ?? "",    base_url: "" },
        google:    { key: prefs.providers.google.key ?? "",    base_url: "" },
        ollama:    { key: prefs.providers.ollama.key ?? "",    base_url: OLLAMA_CLOUD_URL },
      });
    }
  }, [prefs]);

  const handleSaveProvider = (name: ProviderName) => {
    const cfg = providerForm[name];
    const enabled = cfg.key.trim().length > 0;
    const payload: { enabled: boolean; key: string; base_url?: string } = {
      enabled,
      key: cfg.key,
    };
    // Always pin Ollama to Cloud endpoint
    if (name === "ollama") payload.base_url = OLLAMA_CLOUD_URL;
    updatePrefs.mutate(
      { providers: { [name]: payload } },
      {
        onSuccess: () => {
          setSavedProvider(name);
          setTimeout(() => setSavedProvider(null), 2000);
          queryClient.invalidateQueries({ queryKey: modelKeys.all });
        }
      }
    );
  };

  const handleInstallSkill = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!gitUrl.trim()) return;
    installSkill.mutate(gitUrl, {
      onSuccess: () => setGitUrl("")
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadDoc.mutate(file);
    }
  };

  // ── Models tab state ────────────────────────────────────────────────────────
  const [addModelId, setAddModelId] = useState("");
  const [addDisplayName, setAddDisplayName] = useState("");
  const [addPersona, setAddPersona] = useState<RegisterPersona>("drizzle");
  const [pingResult, setPingResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const handlePing = () => {
    if (!addModelId.trim()) return;
    setPingResult(null);
    pingModel.mutate(
      { model_id: addModelId.trim(), provider: detectProvider(addModelId.trim()), persona: addPersona as Persona },
      {
        onSuccess: (res) => setPingResult({ ok: res.reachable, msg: res.error ?? "Reachable" }),
        onError: (err) => setPingResult({ ok: false, msg: String(err) }),
      }
    );
  };

  const handleAddModel = () => {
    if (!addModelId.trim()) return;
    upsertCaps.mutate(
      {
        modelId: addModelId.trim(),
        display_name: addDisplayName.trim() || undefined,
        persona: addPersona as Persona,
      },
      {
        onSuccess: () => {
          setAddModelId("");
          setAddDisplayName("");
          setPingResult(null);
          queryClient.invalidateQueries({ queryKey: modelKeys.all });
        },
      }
    );
  };

  // Per-model editing state (inline)
  const [editingModel, setEditingModel] = useState<string | null>(null);
  const [editDisplayName, setEditDisplayName] = useState("");
  const [editTags, setEditTags] = useState<ModelTag[]>([]);

  const startEdit = (modelId: string) => {
    const override = capOverrides?.find((o) => o.model_id === modelId);
    setEditDisplayName(override?.display_name ?? "");
    setEditTags((override?.tags ?? []) as ModelTag[]);
    setEditingModel(modelId);
  };

  const toggleEditTag = (tag: ModelTag) => {
    setEditTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const saveEdit = (modelId: string) => {
    const override = capOverrides?.find((o) => o.model_id === modelId);
    upsertCaps.mutate(
      {
        modelId,
        display_name: editDisplayName.trim() || undefined,
        tags: editTags,
        persona: (override?.persona ?? "drizzle") as Persona,
      },
      {
        onSuccess: () => {
          setEditingModel(null);
          queryClient.invalidateQueries({ queryKey: modelKeys.all });
        },
      }
    );
  };

  if (!settingsOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={toggleSettings}
        className="absolute inset-0 bg-black/80 backdrop-blur-md"
      />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative w-full max-w-3xl h-[680px] z-10"
      >
        <GlassPanel className="h-full flex flex-col shadow-2xl border-white/10 bg-black backdrop-blur-2xl overflow-hidden">
          <div className="p-6 border-b border-white/10 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">System Settings</h2>
              <p className="text-sm text-white/40">Configure neural parameters and local clusters.</p>
            </div>
            <button
              onClick={toggleSettings}
              className="p-2 hover:bg-white/5 rounded-full transition-colors text-white/40 hover:text-white"
            >
              <Plus className="rotate-45" size={20} />
            </button>
          </div>

          <div className="flex flex-1 overflow-hidden">
            {/* Sidebar Tabs */}
            <div className="w-56 border-r border-white/5 p-3 space-y-1">
              {[
                { id: "api",      label: "API Credentials", icon: Globe },
                { id: "models",   label: "Models",          icon: Layers },
                { id: "skills",   label: "Skill Store",     icon: Cpu },
                { id: "kb",       label: "Archive",         icon: Database },
                { id: "baseline", label: "Baseline",        icon: Brain },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as TabId)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-all ${
                    activeTab === tab.id
                      ? "bg-white text-black font-bold shadow-lg"
                      : "text-white/40 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <tab.icon size={16} strokeWidth={activeTab === tab.id ? 2.5 : 2} />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-8 bg-white/[0.01]">
              <AnimatePresence mode="wait">

                {/* ── API Credentials ─────────────────────────────────────── */}
                {activeTab === "api" && (
                  <motion.div
                    key="api"
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="space-y-4"
                  >
                    <div className="space-y-1 mb-6">
                      <h3 className="text-lg font-semibold text-white">Provider Credentials</h3>
                      <p className="text-xs text-white/30 uppercase tracking-widest">Save API key to activate provider</p>
                    </div>

                    {(["anthropic", "openai", "google", "ollama"] as ProviderName[]).map((name) => {
                      const cfg = providerForm[name];
                      const isSaved = savedProvider === name;
                      const labels: Record<ProviderName, { title: string; subtitle: string; placeholder: string }> = {
                        anthropic: { title: "Anthropic",    subtitle: "Claude Opus 4.7, Sonnet 4.6, Haiku 4.5", placeholder: "sk-ant-..." },
                        openai:    { title: "OpenAI",       subtitle: "GPT-5.4, GPT-5.4-mini, GPT-Image-2",     placeholder: "sk-..." },
                        google:    { title: "Google",       subtitle: "Gemini 3.1 Pro, Flash, Image preview",   placeholder: "AIza..." },
                        ollama:    { title: "Ollama Cloud", subtitle: "ollama.com — Kimi, GLM, Gemma, Qwen",    placeholder: "Paste Ollama Cloud API key" },
                      };
                      const meta = labels[name];

                      return (
                        <div key={name} className="rounded-2xl border border-white/10 bg-white/[0.03]">
                          <div className="px-5 pt-4 pb-3">
                            <p className="text-sm font-bold text-white">{meta.title}</p>
                            <p className="text-[10px] text-white/30 mt-0.5">{meta.subtitle}</p>
                          </div>
                          <div className="px-5 pb-4 space-y-3">
                            <div className="relative">
                              <input
                                type={showKeys[name] ? "text" : "password"}
                                value={cfg.key}
                                onChange={(e) =>
                                  setProviderForm(prev => ({
                                    ...prev,
                                    [name]: { ...prev[name], key: e.target.value },
                                  }))
                                }
                                placeholder={meta.placeholder}
                                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 pr-10 text-xs text-white font-mono focus:ring-1 focus:ring-white/30 outline-none transition-all placeholder:text-white/10"
                              />
                              <button
                                type="button"
                                onClick={() => setShowKeys(prev => ({ ...prev, [name]: !prev[name] }))}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/20 hover:text-white/60 transition-colors"
                              >
                                {showKeys[name] ? <EyeOff size={14} /> : <Eye size={14} />}
                              </button>
                            </div>
                            <button
                              onClick={() => handleSaveProvider(name)}
                              disabled={updatePrefs.isPending}
                              className={`w-full py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                                isSaved
                                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                  : "bg-white/10 text-white/60 hover:bg-white/20 hover:text-white border border-white/5"
                              }`}
                            >
                              {isSaved ? (
                                <><Check size={12} /> Saved</>
                              ) : updatePrefs.isPending ? (
                                <Loader2 size={12} className="animate-spin" />
                              ) : (
                                "Save"
                              )}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </motion.div>
                )}

                {/* ── Models Management ───────────────────────────────────── */}
                {activeTab === "models" && (
                  <motion.div
                    key="models"
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="space-y-6"
                  >
                    <div className="space-y-1">
                      <h3 className="text-lg font-semibold text-white">Models Management</h3>
                      <p className="text-xs text-white/30 uppercase tracking-widest">Register models and assign task tags</p>
                      <p className="text-[11px] text-white/20 mt-2 leading-relaxed">
                        Rain automatically picks the best model for each message based on its task tags. Click the tag icon on any model to assign tags.
                        Multiple models can share a tag — Rain rotates between them.
                      </p>
                    </div>

                    {/* Register New Model */}
                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 space-y-4">
                      <p className="text-xs font-bold text-white/60 uppercase tracking-widest">Register New Model</p>

                      {/* Model ID + Ping */}
                      <div className="flex gap-2">
                        <input
                          value={addModelId}
                          onChange={(e) => { setAddModelId(e.target.value); setPingResult(null); }}
                          placeholder="Model ID (e.g. gemini-2.0-flash-exp, gpt-4o)"
                          className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white font-mono focus:ring-1 focus:ring-white/30 outline-none placeholder:text-white/10"
                        />
                        <button
                          onClick={handlePing}
                          disabled={pingModel.isPending || !addModelId.trim()}
                          className="px-4 py-2.5 rounded-xl text-xs font-bold border border-white/10 text-white/60 hover:border-white/30 hover:text-white transition-all flex items-center gap-1.5 disabled:opacity-30"
                        >
                          {pingModel.isPending ? (
                            <Loader2 size={12} className="animate-spin" />
                          ) : pingResult?.ok ? (
                            <Wifi size={12} className="text-emerald-400" />
                          ) : pingResult ? (
                            <WifiOff size={12} className="text-rose-400" />
                          ) : (
                            <Wifi size={12} />
                          )}
                          Ping
                        </button>
                      </div>

                      {pingResult && (
                        <p className={`text-[10px] font-mono ${pingResult.ok ? "text-emerald-400" : "text-rose-400"}`}>
                          {pingResult.ok ? "✓ " : "✗ "}{pingResult.msg}
                        </p>
                      )}

                      {/* Display name */}
                      <input
                        value={addDisplayName}
                        onChange={(e) => setAddDisplayName(e.target.value)}
                        placeholder="Display name (optional)"
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:ring-1 focus:ring-white/30 outline-none placeholder:text-white/10"
                      />

                      {/* Persona picker */}
                      <div className="space-y-1.5">
                        <p className="text-[10px] text-white/30 uppercase tracking-widest">Persona</p>
                        <div className="flex gap-2">
                          {PERSONA_SECTIONS.map(({ id, label, icon: Icon, color }) => (
                            <button
                              key={id}
                              type="button"
                              onClick={() => setAddPersona(id)}
                              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                                addPersona === id
                                  ? "bg-white text-black border-white"
                                  : "border-white/10 text-white/30 hover:border-white/30 hover:text-white/60"
                              }`}
                            >
                              <Icon size={12} className={addPersona === id ? "text-black" : color} />
                              {label}
                            </button>
                          ))}
                        </div>
                      </div>

                      <button
                        onClick={handleAddModel}
                        disabled={upsertCaps.isPending || !addModelId.trim()}
                        className="w-full py-2.5 rounded-xl text-xs font-bold bg-white/10 text-white/60 hover:bg-white/20 hover:text-white border border-white/5 transition-all flex items-center justify-center gap-2 disabled:opacity-30"
                      >
                        {upsertCaps.isPending ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
                        Register Model
                      </button>
                    </div>

                    {/* Persona-grouped model sections */}
                    {PERSONA_SECTIONS.map(({ id: sectionPersona, label: sectionLabel, icon: SectionIcon, color: sectionColor, subtitle: sectionSubtitle }) => {
                      const sectionModels = (capOverrides ?? []).filter((o) => o.persona === sectionPersona);

                      return (
                        <div key={sectionPersona} className="space-y-2">
                          <div className="flex items-center gap-2 px-1">
                            <SectionIcon size={14} className={sectionColor} />
                            <p className="text-xs font-bold text-white/60 uppercase tracking-widest">{sectionLabel}</p>
                            <span className="text-[10px] text-white/20">— {sectionSubtitle}</span>
                          </div>

                          {sectionModels.length === 0 ? (
                            <div className="rounded-xl border border-dashed border-white/5 p-4 text-center">
                              <p className="text-[10px] text-white/20 uppercase tracking-widest">No models registered</p>
                            </div>
                          ) : (
                            sectionModels.map((override) => {
                              const model = models?.find((m) => m.id === override.model_id);
                              const isEditing = editingModel === override.model_id;
                              const tags = (override.tags ?? []) as ModelTag[];

                              return (
                                <div
                                  key={override.model_id}
                                  className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-2 transition-all"
                                >
                                  <div className="flex items-center justify-between gap-3">
                                    <div className="min-w-0 flex-1">
                                      <p className="text-sm font-bold text-white/90 truncate">
                                        {override.display_name || override.model_id}
                                      </p>
                                      {override.display_name && (
                                        <p className="text-[10px] font-mono text-white/30 truncate">{override.model_id}</p>
                                      )}
                                      <p className="text-[9px] text-white/20 uppercase tracking-widest mt-0.5">
                                        {model?.provider ?? detectProvider(override.model_id)}
                                      </p>
                                    </div>
                                    <button
                                      onClick={() => isEditing ? setEditingModel(null) : startEdit(override.model_id)}
                                      className="p-1.5 text-white/20 hover:text-white/70 transition-colors shrink-0"
                                    >
                                      <Tag size={13} />
                                    </button>
                                  </div>

                                  {/* Tag chips (read mode) */}
                                  {!isEditing && (
                                    <div className="flex flex-wrap gap-1">
                                      {tags.length > 0 ? tags.map((tag) => (
                                        <span key={tag} className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-white/10 text-white/50 uppercase tracking-widest">
                                          {MODEL_TAG_LABELS[tag] ?? tag}
                                        </span>
                                      )) : (
                                        <span className="text-[9px] text-white/15 uppercase tracking-widest">no tags — click tag icon to assign</span>
                                      )}
                                    </div>
                                  )}

                                  {/* Edit mode */}
                                  {isEditing && (
                                    <div className="space-y-3 pt-2 border-t border-white/5">
                                      <input
                                        value={editDisplayName}
                                        onChange={(e) => setEditDisplayName(e.target.value)}
                                        placeholder="Display name (optional)"
                                        className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-white/30 outline-none placeholder:text-white/10"
                                      />
                                      {/* Tag picker */}
                                      <div className="space-y-1.5">
                                        <p className="text-[9px] text-white/30 uppercase tracking-widest">Task tags — model is used when message matches this type</p>
                                        <div className="flex flex-wrap gap-1.5">
                                          {getTagsForPersona(sectionPersona).map((tag) => {
                                            const active = editTags.includes(tag);
                                            return (
                                              <button
                                                key={tag}
                                                type="button"
                                                onClick={() => toggleEditTag(tag)}
                                                className={`text-[9px] font-bold px-2 py-1 rounded-full transition-all border ${
                                                  active
                                                    ? "bg-white text-black border-white"
                                                    : "border-white/10 text-white/30 hover:border-white/30 hover:text-white/60"
                                                }`}
                                              >
                                                {MODEL_TAG_LABELS[tag]}
                                              </button>
                                            );
                                          })}
                                        </div>
                                      </div>
                                      <div className="flex gap-2">
                                        <button
                                          onClick={() => saveEdit(override.model_id)}
                                          disabled={upsertCaps.isPending}
                                          className="flex-1 py-1.5 rounded-lg text-xs font-bold bg-white/10 text-white/60 hover:bg-white/20 hover:text-white border border-white/5 transition-all flex items-center justify-center gap-1"
                                        >
                                          {upsertCaps.isPending ? <Loader2 size={10} className="animate-spin" /> : <Check size={10} />}
                                          Save
                                        </button>
                                        <button
                                          onClick={() => deleteCap.mutate(override.model_id, {
                                            onSuccess: () => {
                                              setEditingModel(null);
                                              queryClient.invalidateQueries({ queryKey: modelKeys.all });
                                            }
                                          })}
                                          disabled={deleteCap.isPending}
                                          className="p-1.5 rounded-lg border border-white/5 text-white/20 hover:text-rose-400 hover:border-rose-400/30 transition-all"
                                        >
                                          <Trash2 size={13} />
                                        </button>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              );
                            })
                          )}
                        </div>
                      );
                    })}
                  </motion.div>
                )}

                {/* ── Skill Store ─────────────────────────────────────────── */}
                {activeTab === "skills" && (
                  <motion.div
                    key="skills"
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="space-y-8"
                  >
                    <div className="space-y-2">
                      <h3 className="text-lg font-semibold text-white">Skill Marketplace</h3>
                      <p className="text-xs text-white/30 uppercase tracking-widest">Install Neural Extensions</p>
                    </div>

                    <form onSubmit={handleInstallSkill} className="flex gap-2">
                      <input
                        type="text"
                        value={gitUrl}
                        onChange={(e) => setGitUrl(e.target.value)}
                        placeholder="https://github.com/..."
                        className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xs text-white outline-none focus:border-white/30"
                      />
                      <Button
                        disabled={installSkill.isPending}
                        type="submit"
                        className="px-6 h-auto py-2 text-xs"
                      >
                        {installSkill.isPending ? <Loader2 size={14} className="animate-spin" /> : "Install"}
                      </Button>
                    </form>

                    <div className="space-y-3">
                      {skillsLoading ? (
                        <div className="py-12 flex justify-center"><Loader2 className="animate-spin text-white/10" /></div>
                      ) : skills?.length === 0 ? (
                        <div className="text-center py-12 border border-dashed border-white/5 rounded-2xl">
                          <p className="text-xs text-white/20 uppercase tracking-widest">No skills active</p>
                        </div>
                      ) : (
                        skills?.map((skill) => (
                          <div key={skill.id} className="flex items-center justify-between p-4 border border-white/5 rounded-2xl bg-white/[0.02] group hover:border-white/10 transition-all">
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-bold text-white/90">{skill.name}</p>
                              <p className="text-[10px] text-white/30 truncate mt-1">{skill.description}</p>
                            </div>
                            <button
                              onClick={() => uninstallSkill.mutate(skill.name)}
                              className="p-2 text-white/10 hover:text-rose-500 transition-colors shrink-0 ml-4"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </motion.div>
                )}

                {/* ── Neural Archive ──────────────────────────────────────── */}
                {activeTab === "kb" && (
                  <motion.div
                    key="kb"
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="space-y-8"
                  >
                    <div className="space-y-2">
                      <h3 className="text-lg font-semibold text-white">Neural Archive</h3>
                      <p className="text-xs text-white/30 uppercase tracking-widest">Local Knowledge Fragments</p>
                    </div>

                    <div
                      onClick={() => fileInputRef.current?.click()}
                      className="group cursor-pointer p-8 border-2 border-dashed border-white/5 rounded-2xl text-center space-y-4 bg-white/[0.01] hover:bg-white/[0.02] hover:border-white/10 transition-all"
                    >
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                      <div className="w-12 h-12 bg-white/5 rounded-full flex items-center justify-center mx-auto text-white/20 group-hover:scale-110 transition-transform">
                        {uploadDoc.isPending ? <Loader2 size={24} className="animate-spin" /> : <Upload size={24} />}
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-white/80">Inject Knowledge</p>
                        <p className="text-[10px] text-white/20 uppercase tracking-widest">PDF, MD, TXT (MAX 10MB)</p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      {docsLoading ? (
                        <div className="py-12 flex justify-center"><Loader2 className="animate-spin text-white/10" /></div>
                      ) : docs?.documents.length === 0 ? (
                        <div className="text-center py-8">
                          <p className="text-[10px] text-white/10 uppercase tracking-widest">Archive is empty</p>
                        </div>
                      ) : (
                        docs?.documents.map((doc) => (
                          <div key={doc.id} className="flex items-center gap-4 p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-all group">
                            <div className="p-2 rounded-lg bg-white/5 text-white/20 group-hover:text-white/40 transition-colors">
                              <FileText size={14} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium text-white/70 truncate">{doc.filename}</p>
                              <p className="text-[10px] font-mono text-white/20 uppercase tracking-tighter">{doc.status}</p>
                            </div>
                            <button
                              onClick={() => deleteDoc.mutate(doc.id)}
                              className="opacity-0 group-hover:opacity-100 p-1.5 text-white/20 hover:text-rose-500 transition-all"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </motion.div>
                )}

                {/* ── Baseline ─────────────────────────────────────── */}
                {activeTab === "baseline" && (
                  <motion.div
                    key="baseline"
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="space-y-6"
                  >
                    <div className="space-y-1 mb-6">
                      <h3 className="text-lg font-semibold text-white">Baseline</h3>
                      <p className="text-xs text-white/30 uppercase tracking-widest">Global system prompt injected in every conversation</p>
                    </div>
                    <textarea
                      value={baselinePrompt}
                      onChange={(e) => setBaselinePrompt(e.target.value)}
                      onBlur={handleSaveBaseline}
                      placeholder="Enter global baseline instructions..."
                      className="w-full h-72 bg-white/5 border border-white/10 rounded-2xl p-4 text-xs text-white/80 placeholder:text-white/20 resize-none focus:outline-none focus:border-white/20 transition-all font-mono leading-relaxed"
                    />
                    <p className="text-[10px] text-white/20 uppercase tracking-widest text-center italic">Changes auto-sync on blur</p>
                  </motion.div>
                )}

              </AnimatePresence>
            </div>
          </div>
        </GlassPanel>
      </motion.div>
    </div>
  );
}

