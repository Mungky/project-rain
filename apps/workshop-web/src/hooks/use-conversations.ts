import { useQuery, useMutation, useQueryClient, UseQueryOptions } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete, apiPatch } from "@/lib/api-client";
import type {
  ConversationResponse,
  ConversationDetailResponse,
} from "@/lib/api-types";

interface ConversationListResponse {
  conversations: ConversationResponse[];
  total_count: number;
  next_cursor: string | null;
}

interface ConversationCreatedResponse {
  id: string;
  created_at: string;
}

export const conversationKeys = {
  all: ["conversations"] as const,
  list: () => [...conversationKeys.all, "list"] as const,
  detail: (id: string) => [...conversationKeys.all, "detail", id] as const,
};

export function useConversations(options?: Partial<UseQueryOptions<ConversationResponse[]>>) {
  return useQuery({
    queryKey: conversationKeys.list(),
    queryFn: async () => {
      const data = await apiGet<ConversationListResponse>("/v1/conversations");
      return data.conversations;
    },
    ...options
  });
}

export function useConversation(id: string, options?: Partial<UseQueryOptions<ConversationDetailResponse>>) {
  return useQuery({
    queryKey: conversationKeys.detail(id),
    queryFn: () =>
      apiGet<ConversationDetailResponse>(`/v1/conversations/${id}`),
    enabled: !!id,
    // Prevent window-focus refetch from wiping optimistic streaming data.
    // Conversations are always refreshed via invalidateQueries after mutations.
    refetchOnWindowFocus: false,
    staleTime: 30_000,
    ...options
  });
}

import type { Persona } from "@/lib/api-types";

import { usePersonaStore } from "@/stores/persona-store";

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (opts: { persona?: Persona; behavior_mode?: string } = {}) => {
      return apiPost<ConversationCreatedResponse>("/v1/conversations", {
        persona: opts.persona ?? "drizzle",
        behavior_mode: opts.behavior_mode,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: conversationKeys.list() });
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiDelete(`/v1/conversations/${id}`),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: conversationKeys.list() });
      queryClient.removeQueries({ queryKey: conversationKeys.detail(id) });
    },
  });
}

export function useUpdateConversation(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (updates: Partial<ConversationDetailResponse>) =>
      apiPatch<ConversationDetailResponse>(`/v1/conversations/${id}`, updates),
    onSuccess: (data) => {
      queryClient.setQueryData(conversationKeys.detail(id), data);
      queryClient.invalidateQueries({ queryKey: conversationKeys.list() });
    },
  });
}