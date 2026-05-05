import { create } from "zustand";

interface ContextState {
  contextSnippets: string[];
  setContext: (snippets: string[]) => void;
  appendContext: (snippet: string) => void;
  clearContext: () => void;
}

export const useContextStore = create<ContextState>()((set) => ({
  contextSnippets: [],
  setContext: (snippets) => set({ contextSnippets: snippets }),
  appendContext: (snippet) => 
    set((state) => ({ contextSnippets: [...state.contextSnippets, snippet] })),
  clearContext: () => set({ contextSnippets: [] }),
}));