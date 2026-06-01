import { useQuery, useMutation, useQueryClient, UseQueryOptions } from "@tanstack/react-query";
import { apiGet, apiPatch } from "@/lib/api-client";
import type { UserPreferencesResponse, UsageResponse, UsagePeriod, CustomMode } from "@/lib/api-types";

export interface UpdatePreferencesPayload {
  providers?: Record<string, { enabled?: boolean; key?: string; base_url?: string }>;
  custom_system_prompt?: string | null;
  hidden_models?: string[];
  custom_modes?: CustomMode[];
  default_behavior_mode?: string;
}

export const preferenceKeys = {
  all: ["user-preferences"] as const,
};

export const usageKeys = {
  period: (period: UsagePeriod) => ["usage", period] as const,
};

export function useUserPreferences() {
  return useQuery({
    queryKey: preferenceKeys.all,
    queryFn: () => apiGet<UserPreferencesResponse>("/v1/user/preferences"),
  });
}

export function useUpdateUserPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (updates: UpdatePreferencesPayload) =>
      apiPatch<UserPreferencesResponse>("/v1/user/preferences", updates),
    onSuccess: (data) => {
      queryClient.setQueryData(preferenceKeys.all, data);
    },
  });
}

export function useUsage(period: UsagePeriod = "all", options?: Partial<UseQueryOptions<UsageResponse, Error>>) {
  return useQuery({
    queryKey: usageKeys.period(period),
    queryFn: () => apiGet<UsageResponse>(`/v1/user/usage?period=${period}`),
    ...options
  });
}