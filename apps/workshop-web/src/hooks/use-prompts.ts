import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPatch, apiPut, apiDelete } from "@/lib/api-client";
import type { PromptResponse, CreatePromptBody, ModelCapabilityOverride, UpsertModelCapabilitiesBody } from "@/lib/api-types";

export const promptKeys = {
  all: ["prompts"] as const,
};

export function usePrompts() {
  return useQuery({
    queryKey: promptKeys.all,
    queryFn: () => apiGet<PromptResponse[]>("/v1/prompts"),
  });
}

export function useCreatePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreatePromptBody) =>
      apiPost<PromptResponse>("/v1/prompts", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: promptKeys.all }),
  });
}

export function useUpdatePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<CreatePromptBody> & { id: string }) =>
      apiPatch<PromptResponse>(`/v1/prompts/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: promptKeys.all }),
  });
}

export function useDeletePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiDelete(`/v1/prompts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: promptKeys.all }),
  });
}

export function useModelCapabilities() {
  return useQuery({
    queryKey: ["model-capabilities"] as const,
    queryFn: () => apiGet<ModelCapabilityOverride[]>("/v1/prompts/model-capabilities"),
  });
}

export function useUpsertModelCapabilities() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ modelId, ...body }: UpsertModelCapabilitiesBody & { modelId: string }) =>
      apiPut<ModelCapabilityOverride>(`/v1/prompts/model-capabilities/${encodeURIComponent(modelId)}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["model-capabilities"] });
    },
  });
}

export function useUpdateModelTags() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ modelId, tags, persona }: { modelId: string; tags: string[]; persona: string }) =>
      apiPut<ModelCapabilityOverride>(`/v1/prompts/model-capabilities/${encodeURIComponent(modelId)}`, { tags, persona }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["model-capabilities"] }),
  });
}

export function useDeleteModelCapability() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (modelId: string) =>
      apiDelete(`/v1/prompts/model-capabilities/${encodeURIComponent(modelId)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["model-capabilities"] }),
  });
}
