import { useMutation, useQueryClient } from "@tanstack/react-query";
import { sseStream } from "@/lib/sse";
import { apiUrl } from "@/lib/api-client";
import { conversationKeys } from "@/hooks/use-conversations";
import { useContextStore } from "@/stores/context-store";
import { useContextExtractorStore } from "@/stores/context-extractor-store";
import { useStreamingStore } from "@/stores/streaming-store";

interface SendMessageInput {
  conversationId: string;
  content: string;
  attachments?: { name: string; content: string; mime_type?: string }[];
}

import type { ToolEvent, ReactStep } from "@/lib/api-types";

interface OptimisticMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  reasoning_content?: string;
  streaming?: boolean;
  error?: string;
  tool_events?: ToolEvent[];
  react_steps?: ReactStep[];
  attached_file_names?: string[];
  created_at: string;
  model: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  feedback?: number | null;
  _optimistic?: boolean;
  _corrected?: boolean;
  _cancelled?: boolean;
}

/**
 * Update the assistant message in the cache. If a React Query refetch
 * removed the optimistic assistant message from the cache (e.g. window
 * focus refetch with staleTime=0), re-add it so streaming continues.
 */
function patchAssistant(
  old: { messages: OptimisticMessage[] } | undefined,
  assistantId: string,
  now: string,
  patch: Partial<OptimisticMessage>,
): { messages: OptimisticMessage[] } {
  const messages = old?.messages ?? [];
  const idx = messages.findIndex((m) => m.id === assistantId);
  if (idx === -1) {
    return {
      messages: [
        ...messages,
        {
          id: assistantId,
          role: "assistant" as const,
          content: "",
          streaming: true,
          created_at: now,
          model: null,
          tokens_in: null,
          tokens_out: null,
          _optimistic: true,
          ...patch,
        },
      ],
    };
  }
  return { messages: messages.map((m, i) => (i === idx ? { ...m, ...patch } : m)) };
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  const clearContext = useContextStore((s) => s.clearContext);
  const appendContext = useContextStore((s) => s.appendContext);
  const startExtracting = useContextExtractorStore((s) => s.startExtracting);

  return useMutation({
    mutationFn: async ({
      conversationId,
      content,
      attachments,
    }: SendMessageInput) => {
      clearContext();
      const abortController = new AbortController();
      useStreamingStore.getState().setStreaming(conversationId, abortController);

      const userMessageId = `tmp-user-${crypto.randomUUID()}`;
      const assistantMessageId = `tmp-asst-${crypto.randomUUID()}`;
      const now = new Date().toISOString();

      const optimisticUser: OptimisticMessage = {
        id: userMessageId,
        role: "user",
        content,
        attached_file_names: attachments?.map((a) => a.name),
        created_at: now,
        model: null,
        tokens_in: null,
        tokens_out: null,
        _optimistic: true,
      };

      const optimisticAssistant: OptimisticMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        streaming: true,
        created_at: now,
        model: null,
        tokens_in: null,
        tokens_out: null,
        _optimistic: true,
      };

      queryClient.setQueryData(
        conversationKeys.detail(conversationId),
        (old: { messages: OptimisticMessage[] } | undefined) => ({
          ...old,
          messages: [
            ...(old?.messages ?? []),
            optimisticUser,
            optimisticAssistant,
          ],
        }),
      );

      let buffered = "";
      let reasoningBuffer = "";
      const toolEventsList: ToolEvent[] = [];
      const reactStepsList: ReactStep[] = [];
      const qk = conversationKeys.detail(conversationId);

      const patch = (p: Partial<OptimisticMessage>) =>
        queryClient.setQueryData(qk, (old: { messages: OptimisticMessage[] } | undefined) =>
          patchAssistant(old, assistantMessageId, now, p),
        );

      const stream = sseStream(
        apiUrl(`/v1/conversations/${conversationId}/messages`),
        {
          method: "POST",
          body: { content, attachments: attachments ?? [] },
          signal: abortController.signal,
        },
      );

      try {
        for await (const chunk of stream) {
          if (chunk.type === "token") {
            buffered += chunk.data as string;
            patch({ content: buffered });
          } else if (chunk.type === "reasoning") {
            reasoningBuffer += chunk.data as string;
            patch({ reasoning_content: reasoningBuffer });
          } else if (chunk.type === "tool_call") {
            const toolCall = chunk.data as { name: string; args: Record<string, unknown> };
            toolEventsList.push({ name: toolCall.name, args: toolCall.args, status: "calling" });
            patch({ tool_events: [...toolEventsList] });
          } else if (chunk.type === "tool_result") {
            const toolResult = chunk.data as { name: string; result: unknown };
            for (const t of toolEventsList) {
              if (t.name === toolResult.name && t.status === "calling") {
                t.result = toolResult.result;
                t.status = "done";
                break;
              }
            }
            patch({ tool_events: [...toolEventsList] });
          } else if (chunk.type === "react_step") {
            const step = chunk.data as ReactStep;
            reactStepsList.push(step);
            patch({ react_steps: [...reactStepsList] });
          } else if (chunk.type === "correction") {
            const corrected = chunk.data as string;
            buffered = corrected;
            patch({ content: corrected, _corrected: true });
          } else if (chunk.type === "neural_context") {
            const snippets = Array.isArray(chunk.data)
              ? chunk.data.map((c: unknown) => {
                  const entry = c as { source?: string; text?: string };
                  return `[${entry.source ?? "archive"}] ${(entry.text ?? "").slice(0, 200)}`;
                }).join("\n")
              : "";
            appendContext(snippets);
          } else if (chunk.type === "done") {
            const doneData = chunk.data as { tokens_in?: number; tokens_out?: number; model?: string } | undefined;
            const totalTokens = (doneData?.tokens_in ?? 0) + (doneData?.tokens_out ?? 0);
            if (totalTokens > 0) {
              useStreamingStore.getState().setTokensUsed(totalTokens);
            }
            patch({ streaming: false });
            useStreamingStore.getState().clearStreaming(conversationId);
            setTimeout(() => {
              queryClient.invalidateQueries({ queryKey: qk });
              queryClient.invalidateQueries({
                queryKey: conversationKeys.list(),
              });
            }, 500);
            startExtracting();
            setTimeout(() => {
              queryClient.invalidateQueries({ queryKey: ["context"] });
            }, 6000);

            // Auto-generate a proper title after the first AI response.
            // Per-tab guard via sessionStorage so we only fire once per
            // conversation per browser session.
            try {
              const flagKey = `rain:auto-titled:${conversationId}`;
              if (typeof sessionStorage !== "undefined" && !sessionStorage.getItem(flagKey)) {
                sessionStorage.setItem(flagKey, "1");
                fetch(apiUrl(`/v1/conversations/${conversationId}/auto-title`), { method: "POST" })
                  .then(() => {
                    queryClient.invalidateQueries({ queryKey: qk });
                    queryClient.invalidateQueries({ queryKey: conversationKeys.list() });
                  })
                  .catch((err) => console.warn("[auto-title] failed:", err));
              }
            } catch {
              // sessionStorage unavailable — skip
            }
            return chunk.data;
          } else if (chunk.type === "error") {
            const errorData = chunk.data as { code: string; message: string };
            console.error("SSE stream error:", errorData);
            patch({ content: buffered, streaming: false, error: errorData.message });
            useStreamingStore.getState().clearStreaming(conversationId);
            throw new Error(errorData.message);
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          patch({ content: buffered, streaming: false, _cancelled: true });
          useStreamingStore.getState().clearStreaming(conversationId);
          return;
        }
        patch({ content: buffered, streaming: false, error: String(err) });
        useStreamingStore.getState().clearStreaming(conversationId);
        throw err;
      }
    },
    onSettled: (_data, _error, variables) => {
      useStreamingStore.getState().clearStreaming(variables.conversationId);
    },
  });
}