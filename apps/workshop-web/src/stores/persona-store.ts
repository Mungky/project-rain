import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Persona } from "@/lib/api-types";

interface PersonaState {
  selectedPersona: Persona;
  activeModels: Record<Persona, string>;
  setSelectedPersona: (persona: Persona) => void;
  setActiveModel: (persona: Persona, modelId: string) => void;
  getActiveModel: (persona: Persona) => string;
}

export const usePersonaStore = create<PersonaState>()(
  persist(
    (set, get) => ({
      selectedPersona: "drizzle",
      activeModels: {
        drizzle: "",
        nimbus: "",
        shower: "",
        storm: "",
      },
      setSelectedPersona: (persona) => set({ selectedPersona: persona }),
      setActiveModel: (persona, modelId) =>
        set((state) => ({
          activeModels: {
            ...state.activeModels,
            [persona]: modelId,
          },
        })),
      getActiveModel: (persona) => get().activeModels[persona],
    }),
    {
      name: "rain-persona-storage-v2",
    }
  )
);
