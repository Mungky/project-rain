import { useCallback, useEffect, useRef, useState } from "react";

export function useCopyClipboard(resetDelay = 2000) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const copy = useCallback(
    async (text: string, id: string) => {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      if (timerRef.current !== undefined) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopiedId(null), resetDelay);
    },
    [resetDelay],
  );

  useEffect(() => {
    const timer = timerRef.current;
    return () => {
      if (timer !== undefined) clearTimeout(timer);
    };
  }, []);

  return { copiedId, copy };
}