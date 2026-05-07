import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";

export interface HealthResponse {
  status: string;
  ollama: boolean;
  postgres: boolean;
  redis: boolean;
  minio: boolean;
  qdrant: boolean;
}

export const healthKeys = {
  all: ["health"] as const,
};

export function useHealth() {
  return useQuery({
    queryKey: healthKeys.all,
    queryFn: () => apiGet<HealthResponse>("/v1/health"),
    refetchInterval: 10_000,
    retry: 1,
    staleTime: 8_000,
  });
}