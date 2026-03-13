"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "@/components/page-header";
import { DocumentsTable } from "@/features/documents/documents-table";
import { UploadDropzone } from "@/features/upload/upload-dropzone";
import { api } from "@/lib/api";

export default function KnowledgeBasePage() {
  const queryClient = useQueryClient();
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: api.documents });

  const deleteMutation = useMutation({
    mutationFn: api.deleteDocument,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["documents"] })
  });
  const reindexMutation = useMutation({
    mutationFn: api.reindexDocument,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["documents"] })
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Knowledge Base"
        title="Manage indexed documents"
        description="Search, delete, reindex, and inspect every source file that powers retrieval."
      />
      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <UploadDropzone onUploaded={() => void queryClient.invalidateQueries({ queryKey: ["documents"] })} />
        <DocumentsTable
          documents={documentsQuery.data?.documents ?? []}
          onDelete={(id) => deleteMutation.mutate(id)}
          onReindex={(id) => reindexMutation.mutate(id)}
        />
      </div>
    </div>
  );
}
