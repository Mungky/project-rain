import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import type { ModesResponse } from "@/lib/api-types";

export const modeKeys = {
  all: ["behavior-modes"] as const,
};

/** Fetch available behavior modes — built-in presets plus the user's custom modes. */
export function useModes() {
  return useQuery({
    queryKey: modeKeys.all,
    queryFn: () => apiGet<ModesResponse>("/v1/user/modes"),
    staleTime: 60_000,
  });
}
