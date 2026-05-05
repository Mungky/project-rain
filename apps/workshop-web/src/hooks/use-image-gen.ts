import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/api-client";
import type { ImageGenRequest, ImageGenResponse } from "@/lib/api-types";

export function useImageGen() {
  return useMutation({
    mutationFn: (body: ImageGenRequest) =>
      apiPost<ImageGenResponse>("/v1/generate-image", body),
  });
}
