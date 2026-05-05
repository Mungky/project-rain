"use client";

import { create } from "zustand";

export interface Artifact {
  id: string;
  title: string;
  language: string;
  code: string;
  contentType?: "code" | "markdown";
}

interface ArtifactsState {
  isOpen: boolean;
  artifacts: Artifact[];
  activeId: string | null;
  panelWidth: number;
  openArtifact: (artifact: Artifact) => void;
  close: () => void;
  setActive: (id: string) => void;
  setPanelWidth: (width: number) => void;
  updateCode: (id: string, code: string) => void;
}

export const useArtifactsStore = create<ArtifactsState>((set, get) => ({
  isOpen: false,
  artifacts: [],
  activeId: null,
  panelWidth: 480,

  openArtifact: (artifact) => {
    const existing = get().artifacts.find((a) => a.id === artifact.id);
    if (!existing) {
      set((s) => ({
        isOpen: true,
        artifacts: [...s.artifacts, artifact],
        activeId: artifact.id,
      }));
    } else {
      set({ isOpen: true, activeId: artifact.id });
    }
    // Update URL hash
    window.location.hash = `artifact-${artifact.id}`;
  },

  close: () => {
    set({ isOpen: false });
    window.location.hash = "";
  },

  setActive: (id) => {
    set({ activeId: id, isOpen: true });
    window.location.hash = `artifact-${id}`;
  },

  setPanelWidth: (width) => set({ panelWidth: Math.max(360, Math.min(800, width)) }),

  updateCode: (id, code) => {
    set((s) => ({
      artifacts: s.artifacts.map((a) => (a.id === id ? { ...a, code } : a)),
    }));
  },
}));

// Check URL hash on load
if (typeof window !== "undefined") {
  const hash = window.location.hash;
  const match = hash.match(/^#artifact-(.+)$/);
  if (match && match[1]) {
    // Will be opened when the artifact data becomes available via openArtifact
    useArtifactsStore.getState().setActive(match[1]);
  }
}
