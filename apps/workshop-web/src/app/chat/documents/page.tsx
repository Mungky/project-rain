"use client";

import { useRef } from "react";
import { GlassPanel } from "@/components/identity/glass-panel";
import { useDocuments, useUploadDocument, useDeleteDocument } from "@/hooks/use-documents";

export default function DocumentsPage() {
  const { data, isLoading } = useDocuments();
  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await uploadMutation.mutateAsync(file);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this document? This will remove its data from the knowledge base.")) {
      await deleteMutation.mutateAsync(id);
    }
  };

  return (
    <div className="flex-1 flex flex-col p-4 md:p-8 space-y-6 overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-900 dark:text-ink-100 tracking-tight">
            Knowledge Base
          </h1>
          <p className="text-sm text-ink-500">
            Manage documents that Rain uses to answer your questions.
          </p>
        </div>

        <input
          type="file"
          ref={fileInputRef}
          onChange={handleUpload}
          className="hidden"
          accept=".txt,.md"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
          className="px-4 py-2 rounded-lg bg-storm-500 hover:bg-storm-600 text-white font-medium transition-colors disabled:opacity-50"
        >
          {uploadMutation.isPending ? "Processing..." : "Upload Document"}
        </button>
      </div>

      <GlassPanel className="flex-1 overflow-hidden flex flex-col">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
             <div className="h-8 w-8 rounded-full border-2 border-storm-500 border-t-transparent animate-spin" />
          </div>
        ) : !data?.documents || data.documents.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-12 space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-ink-100/50 dark:bg-ink-800/50 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8 text-ink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-medium text-ink-900 dark:text-ink-100">No documents found</h3>
              <p className="text-sm text-ink-500">Upload text or markdown files to get started with RAG.</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-ink-50/80 dark:bg-ink-900/80 backdrop-blur-md z-10">
                <tr>
                  <th className="px-6 py-3 text-xs font-semibold text-ink-400 uppercase tracking-wider">Filename</th>
                  <th className="px-6 py-3 text-xs font-semibold text-ink-400 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-xs font-semibold text-ink-400 uppercase tracking-wider">Added</th>
                  <th className="px-6 py-3 text-xs font-semibold text-ink-400 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100/50 dark:divide-ink-800/50">
                {data.documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-ink-50/40 dark:hover:bg-ink-800/40 transition-colors">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-ink-900 dark:text-ink-100">{doc.filename}</div>
                      <div className="text-xs text-ink-500">{doc.mime}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        doc.status === 'ready' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400' :
                        doc.status === 'error' ? 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400' :
                        'bg-storm-100 text-storm-800 dark:bg-storm-900/30 dark:text-storm-400 animate-pulse'
                      }`}>
                        {doc.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-ink-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="p-2 text-ink-400 hover:text-rose-500 transition-colors"
                        aria-label="Delete document"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassPanel>
    </div>
  );
}
