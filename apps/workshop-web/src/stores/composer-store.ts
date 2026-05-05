import { create } from "zustand";
import type { SlashCommand } from "@/lib/slash-commands";

interface ComposerState {
  draft: string;
  editingMessageId: string | null;
  shouldFocus: boolean;
  slashCommand: { active: boolean; query: string } | null;
  setDraft: (text: string) => void;
  clearDraft: () => void;
  setEditingMessageId: (id: string | null) => void;
  requestFocus: () => void;
  clearFocusRequest: () => void;
  setSlashCommand: (cmd: { active: boolean; query: string } | null) => void;
}

export const useComposerStore = create<ComposerState>()((set) => ({
  draft: "",
  editingMessageId: null,
  shouldFocus: false,
  slashCommand: null,
  setDraft: (text) => set({ draft: text }),
  clearDraft: () => set({ draft: "" }),
  setEditingMessageId: (id) => set({ editingMessageId: id }),
  requestFocus: () => set({ shouldFocus: true }),
  clearFocusRequest: () => set({ shouldFocus: false }),
  setSlashCommand: (cmd) => set({ slashCommand: cmd }),
}));