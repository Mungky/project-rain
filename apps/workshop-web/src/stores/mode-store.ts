import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ModeState {
  /** Currently selected behavior-mode key (built-in or custom). "default" = no override. */
  selectedMode: string;
  setSelectedMode: (mode: string) => void;
}

export const useModeStore = create<ModeState>()(
  persist(
    (set) => ({
      selectedMode: "default",
      setSelectedMode: (mode) => set({ selectedMode: mode }),
    }),
    {
      name: "rain-mode-storage-v1",
    }
  )
);
