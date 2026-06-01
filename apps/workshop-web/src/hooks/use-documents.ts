import { useQuery, useMutation, useQueryClient, UseQueryOptions } from "@tanstack/react-query";
import { apiGet, apiDelete, apiPostForm, apiAuthHeaders } from "@/lib/api-client";
import { apiUrl } from "@/lib/api-client";
import type { DocumentListResponse, DocumentUploadResponse } from "@/lib/api-types";

export const documentKeys = {
  all: ["documents"] as const,
  list: () => [...documentKeys.all, "list"] as const,
};

export function useDocuments(options?: Partial<UseQueryOptions<DocumentListResponse, Error>>) {
  return useQuery({
    queryKey: documentKeys.list(),
    queryFn: () => apiGet<DocumentListResponse>("/v1/documents"),
    // Refresh while documents are processing
    refetchInterval: (query): any => {
        const hasProcessing = query.state.data?.documents.some(
            (d: any) => d.status === "processing" || d.status === "uploading"
        );
        if (hasProcessing) return 3000;
        return options?.refetchInterval ?? false;
    },
    ...options
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    // apiPostForm attaches the Authorization bearer header (raw fetch did not,
    // which is why uploads 401'd against the auth-gated API).
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiPostForm<DocumentUploadResponse>("/v1/documents", formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.list() });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiDelete(`/v1/documents/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.list() });
    },
  });
}

export function useDownloadDocument() {
  return useMutation({
    mutationFn: async (doc: { id: string; filename: string }) => {
      const response = await fetch(apiUrl(`/v1/documents/${doc.id}/download`), {
        headers: apiAuthHeaders(),
      });
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const href = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), { href, download: doc.filename });
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(href);
    },
  });
}
