import { useMutation } from "@tanstack/react-query";
import { apiPut } from "@/lib/api-client";
import type { FeedbackRating } from "@/lib/api-types";

export function useFeedback() {
  return useMutation({
    mutationFn: ({
      messageId,
      feedback,
    }: {
      messageId: string;
      feedback: FeedbackRating;
    }) => apiPut<{ ok: boolean }>(`/v1/messages/${messageId}/feedback`, { feedback }),
  });
}