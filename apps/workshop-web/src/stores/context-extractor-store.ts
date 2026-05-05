import { create } from "zustand";

type ExtractorStatus = "idle" | "extracting" | "synced" | "error";

interface ContextExtractorState {
  status: ExtractorStatus;
  startExtracting: () => void;
  extractFromText: (text: string, sourceType?: string, sourceId?: string) => Promise<void>;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const useContextExtractorStore = create<ContextExtractorState>((set) => ({
  status: "idle",

  startExtracting: () => {
    set({ status: "extracting" });
    setTimeout(() => set({ status: "synced" }), 6000);
    setTimeout(() => set({ status: "idle" }), 8500);
  },

  extractFromText: async (text, sourceType = "session", sourceId) => {
    set({ status: "extracting" });
    try {
      const res = await fetch(`${API_BASE_URL}/v1/context/extract/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source_type: sourceType, source_id: sourceId }),
      });

      if (res.ok) {
        set({ status: "synced" });
      } else {
        set({ status: "error" });
      }
    } catch {
      set({ status: "error" });
    }
    setTimeout(() => {
      set((s) => (s.status !== "extracting" ? { status: "idle" } : {}));
    }, 3000);
  },
}));
