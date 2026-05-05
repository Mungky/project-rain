"use client";

import { useQuery, useMutation, useQueryClient, UseQueryOptions } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api-client";
import type {
  ContextEntryResponse,
  CreateContextEntryBody,
  UpdateContextEntryBody,
} from "@/lib/api-types";

const contextKeys = {
  all: ["context"] as const,
  list: (category?: string) => ["context", "list", category ?? "all"] as const,
};

export function useContextLibrary(category?: string, options?: Partial<UseQueryOptions<ContextEntryResponse[]>>) {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  const path = `/v1/context${params.size ? `?${params}` : ""}`;
  return useQuery<ContextEntryResponse[]>({
    queryKey: contextKeys.list(category),
    queryFn: () => apiGet<ContextEntryResponse[]>(path),
    ...options
  });
}

export function useCreateContextEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateContextEntryBody) =>
      apiPost<ContextEntryResponse>("/v1/context", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: contextKeys.all }),
  });
}

export function useUpdateContextEntry(entryId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateContextEntryBody) =>
      apiPut<ContextEntryResponse>(`/v1/context/${entryId}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: contextKeys.all }),
  });
}

export function useDeleteContextEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) => apiDelete(`/v1/context/${entryId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: contextKeys.all }),
  });
}

export function useExtractFromSession(conversationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entries: CreateContextEntryBody[]) =>
      apiPost<ContextEntryResponse[]>(
        `/v1/context/extract/session/${conversationId}`,
        { entries }
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: contextKeys.all }),
  });
}
