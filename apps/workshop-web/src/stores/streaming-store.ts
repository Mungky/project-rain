import { create } from "zustand";

interface StreamingState {
  activeStreams: Record<string, AbortController>;
  lastError: { code: string; message: string; retryable: boolean } | null;
  tokensUsed: number;
  setStreaming: (conversationId: string, controller: AbortController) => void;
  clearStreaming: (conversationId: string) => void;
  isStreaming: (conversationId: string) => boolean;
  getController: (conversationId: string) => AbortController | undefined;
  setError: (error: { code: string; message: string; retryable: boolean } | null) => void;
  setTokensUsed: (count: number) => void;
}

export const useStreamingStore = create<StreamingState>((set, get) => ({
  activeStreams: {},
  lastError: null,
  tokensUsed: 0,
  setStreaming: (conversationId, controller) =>
    set((s) => ({
      activeStreams: { ...s.activeStreams, [conversationId]: controller },
      lastError: null,
    })),
  clearStreaming: (conversationId) =>
    set((s) => {
      const { [conversationId]: _, ...rest } = s.activeStreams;
      return { activeStreams: rest };
    }),
  isStreaming: (conversationId) => conversationId in get().activeStreams,
  getController: (conversationId) => get().activeStreams[conversationId],
  setError: (error) => set({ lastError: error }),
  setTokensUsed: (count) => set({ tokensUsed: count }),
}));