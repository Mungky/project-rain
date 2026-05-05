import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect } from "react";
import { apiGet, apiPost } from "@/lib/api-client";
import type { ModelResponse, PingModelRequest, PingModelResponse } from "@/lib/api-types";
import { useModelStore } from "@/stores/model-store";

export const modelKeys = {
  all: ["models"] as const,
};

export function useModels() {
  const setModels = useModelStore((s) => s.setModels);

  const query = useQuery({
    queryKey: modelKeys.all,
    queryFn: () => apiGet<ModelResponse[]>("/v1/models"),
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (query.data) {
      setModels(query.data);
    }
  }, [query.data, setModels]);

  return query;
}

export function usePingModel() {
  return useMutation({
    mutationFn: (body: PingModelRequest) =>
      apiPost<PingModelResponse>("/v1/models/ping", body),
  });
}
