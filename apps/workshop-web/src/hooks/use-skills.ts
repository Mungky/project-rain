import { useQuery, useMutation, useQueryClient, UseQueryOptions } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "@/lib/api-client";
import type { SkillResponse } from "@/lib/api-types";

export const skillKeys = {
  all: ["skills"] as const,
};

export function useSkills(options?: Partial<UseQueryOptions<SkillResponse[]>>) {
  return useQuery({
    queryKey: skillKeys.all,
    queryFn: () => apiGet<SkillResponse[]>("/v1/skills"),
    ...options
  });
}

export function useInstallSkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (gitUrl: string) => 
      apiPost<SkillResponse>("/v1/skills", { git_url: gitUrl }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skillKeys.all });
    },
  });
}

export function useUninstallSkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => apiDelete(`/v1/skills/${name}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skillKeys.all });
    },
  });
}