import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ModelCapability, ModelResponse } from "@/lib/api-types";

interface ModelState {
  selectedModelId: string;
  models: ModelResponse[];
  setSelectedModelId: (id: string) => void;
  setModels: (models: ModelResponse[]) => void;
  getSelectedModel: () => ModelResponse | undefined;
  hasCapability: (capability: ModelCapability) => boolean;
}

export const useModelStore = create<ModelState>()(
  persist(
    (set, get) => ({
      selectedModelId: "",
      models: [],
      setSelectedModelId: (id) => set({ selectedModelId: id }),
      setModels: (models) => set({ models }),
      getSelectedModel: () => {
        const { selectedModelId, models } = get();
        return models.find((m) => m.id === selectedModelId);
      },
      hasCapability: (capability: ModelCapability) => {
        const model = get().getSelectedModel();
        return model?.capabilities?.includes(capability) ?? false;
      },
    }),
    {
      name: "rain-model-storage-v3",
      partialize: (state) => ({ selectedModelId: state.selectedModelId }),
    }
  )
);
