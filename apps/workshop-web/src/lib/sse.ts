import type { ChatChunk } from "./api-types";

const API_BEARER_TOKEN = process.env.NEXT_PUBLIC_API_BEARER_TOKEN ?? "";

export interface SSEStreamOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

export async function* sseStream(
  url: string,
  opts: SSEStreamOptions = {},
): AsyncGenerator<ChatChunk, void, void> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  if (API_BEARER_TOKEN) headers.Authorization = `Bearer ${API_BEARER_TOKEN}`;

  const response = await fetch(url, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });

  if (!response.ok) {
    throw new Error(`SSE request failed: ${response.status}`);
  }
  if (!response.body) {
    throw new Error("SSE response has no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      
      if (value) {
        buffer += decoder.decode(value, { stream: true });
      }

      let separatorIndex: number;
      while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);

        if (!rawEvent.trim()) continue;

        const dataLine = rawEvent
          .split("\n")
          .find((line) => line.trim().startsWith("data: "));
        
        if (!dataLine) continue;
        const json = dataLine.slice(dataLine.indexOf("data: ") + "data: ".length).trim();

        if (!json) continue;

        try {
          const chunk = JSON.parse(json) as ChatChunk;
          yield chunk;
        } catch (err) {
          console.warn("Malformed SSE chunk:", json, err);
        }
      }

      if (done) {
        // Final flush
        const last = decoder.decode();
        if (last) {
            buffer += last;
            // No separator check here since it's the end, 
            // but usually SSE events always end with \n\n
        }
        break;
      }
    }
  } finally {
    reader.releaseLock();
  }
}