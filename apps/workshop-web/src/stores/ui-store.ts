import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface UIState {
  infoPanelOpen: boolean;
  settingsOpen: boolean;
  showRain: boolean;
  selectedModel: string | null;
  theme: "light" | "dark" | "system";

  toggleInfoPanel: () => void;
  toggleSettings: () => void;
  setShowRain: (show: boolean) => void;
  setSelectedModel: (model: string | null) => void;
  setTheme: (theme: UIState["theme"]) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      infoPanelOpen: true,
      settingsOpen: false,
      showRain: true,
      selectedModel: null,
      theme: "system",

      toggleInfoPanel: () => set((s) => ({ infoPanelOpen: !s.infoPanelOpen })),
      toggleSettings: () => set((s) => ({ settingsOpen: !s.settingsOpen })),
      setShowRain: (show) => set({ showRain: show }),
      setSelectedModel: (model) => set({ selectedModel: model }),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "rain-ui",
      storage: createJSONStorage(() => localStorage),
      version: 1,
      migrate: (persisted: unknown, version: number) => {
        const data = persisted as Record<string, unknown>;
        if (version === 0) {
          return { ...data, theme: "system" };
        }
        return data;
      },
    },
  ),
);