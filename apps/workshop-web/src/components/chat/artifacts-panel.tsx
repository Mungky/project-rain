"use client";

import { useRef, useCallback, useState } from "react";
import { useArtifactsStore, type Artifact } from "@/stores/artifacts-store";
import { motion, AnimatePresence } from "framer-motion";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { X, Copy, Check, Download, Code, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { MarkdownContent } from "./markdown-content";

export function ArtifactsPanel() {
  const { isOpen, artifacts, activeId, panelWidth, close, setActive, setPanelWidth } =
    useArtifactsStore();
  const resizing = useRef(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState<Record<string, boolean>>({});

  const activeArtifact = artifacts.find((a) => a.id === activeId);
  const isPreview = activeId ? previewMode[activeId] ?? false : false;

  const handleCopy = async (id: string, code: string) => {
    await navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getExt = (artifact: Artifact) => {
    if (artifact.contentType === "markdown") return "md";
    if (artifact.language === "javascript" || artifact.language === "js") return "js";
    if (artifact.language === "typescript" || artifact.language === "ts") return "ts";
    if (artifact.language === "python" || artifact.language === "py") return "py";
    if (artifact.language === "html") return "html";
    if (artifact.language === "css") return "css";
    if (artifact.language === "json") return "json";
    return "txt";
  };

  const handleDownload = (artifact: Artifact) => {
    const ext = getExt(artifact);
    const mime = artifact.contentType === "markdown" ? "text/markdown" : "text/plain";
    const blob = new Blob([artifact.code], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${artifact.title.replace(/\.[^.]+$/, "")}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const togglePreview = (id: string) => {
    setPreviewMode((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const startResize = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      resizing.current = true;
      const startX = e.clientX;
      const startWidth = panelWidth;

      const onMove = (ev: MouseEvent) => {
        if (!resizing.current) return;
        setPanelWidth(startWidth + (startX - ev.clientX));
      };

      const onUp = () => {
        resizing.current = false;
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [panelWidth, setPanelWidth],
  );

  const showPreviewToggle = activeArtifact?.contentType === "markdown";

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: panelWidth, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: panelWidth, opacity: 0 }}
          transition={{ type: "spring", damping: 24, stiffness: 260 }}
          className="h-full flex flex-col shrink-0 relative border-l border-white/10 bg-black/90 backdrop-blur-2xl"
          style={{ width: panelWidth }}
        >
          {/* Resize handle */}
          <div
            onMouseDown={startResize}
            className="absolute left-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-white/10 transition-colors z-10 group"
          >
            <div className="w-[2px] h-full mx-auto bg-white/0 group-hover:bg-white/20 transition-colors" />
          </div>

          {/* Header with tabs */}
          <div className="flex items-center border-b border-white/10 pr-4">
            <div className="flex-1 flex overflow-x-auto">
              {artifacts.map((a) => (
                <button
                  key={a.id}
                  onClick={() => setActive(a.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-4 py-3 text-xs font-mono whitespace-nowrap border-r border-white/5 transition-colors",
                    activeId === a.id
                      ? "text-white bg-white/5"
                      : "text-white/30 hover:text-white/60 hover:bg-white/[0.02]",
                  )}
                >
                  <span className="text-[10px] uppercase tracking-wider opacity-50">
                    {a.contentType === "markdown" ? "md" : a.language}
                  </span>
                  {a.title}
                </button>
              ))}
            </div>
            <button
              onClick={close}
              className="p-2 ml-2 rounded-lg text-white/30 hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Close artifacts panel"
            >
              <X size={16} />
            </button>
          </div>

          {/* Toolbar */}
          {activeArtifact && (
            <div className="flex items-center justify-between px-4 py-2 bg-white/[0.02] border-b border-white/5">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono uppercase tracking-widest text-white/20">
                  {activeArtifact.contentType === "markdown" ? "markdown" : activeArtifact.language}
                </span>
                {showPreviewToggle && (
                  <button
                    onClick={() => togglePreview(activeArtifact.id)}
                    className={cn(
                      "flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono transition-colors",
                      isPreview
                        ? "bg-white/10 text-white"
                        : "text-white/30 hover:text-white/60",
                    )}
                  >
                    {isPreview ? <Code size={11} /> : <Eye size={11} />}
                    {isPreview ? "Code" : "Preview"}
                  </button>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleCopy(activeArtifact.id, activeArtifact.code)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-white/30 hover:text-white hover:bg-white/10 transition-colors text-[10px] font-mono"
                >
                  {copiedId === activeArtifact.id ? <Check size={12} /> : <Copy size={12} />}
                  Copy
                </button>
                <button
                  onClick={() => handleDownload(activeArtifact)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-white/30 hover:text-white hover:bg-white/10 transition-colors text-[10px] font-mono"
                >
                  <Download size={12} />
                  Download
                </button>
              </div>
            </div>
          )}

          {/* Content: code or preview */}
          <div className="flex-1 overflow-auto">
            {activeArtifact ? (
              isPreview && activeArtifact.contentType === "markdown" ? (
                <div className="p-5">
                  <MarkdownContent
                    content={activeArtifact.code}
                    className="text-sm leading-relaxed"
                  />
                </div>
              ) : (
                <SyntaxHighlighter
                  style={vscDarkPlus as any}
                  language={activeArtifact.language}
                  customStyle={{
                    margin: 0,
                    padding: "1.5rem",
                    background: "transparent",
                    fontSize: "0.8125rem",
                    lineHeight: "1.6",
                    fontFamily: "var(--font-mono)",
                    minHeight: "100%",
                  }}
                >
                  {activeArtifact.code}
                </SyntaxHighlighter>
              )
            ) : (
              <div className="flex items-center justify-center h-full text-white/20 text-sm font-mono">
                Select an artifact to view
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
