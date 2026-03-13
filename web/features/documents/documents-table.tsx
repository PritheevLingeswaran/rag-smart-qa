"use client";

import Link from "next/link";

import type { DocumentItem } from "@/types/api";

export function DocumentsTable({
  documents,
  onDelete,
  onReindex
}: {
  documents: DocumentItem[];
  onDelete?: (id: string) => void;
  onReindex?: (id: string) => void;
}) {
  if (!documents.length) {
    return (
      <div className="panel flex min-h-72 items-center justify-center p-8 text-center text-slate-500">
        Upload documents to start building a searchable knowledge base.
      </div>
    );
  }

  return (
    <div className="panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-5 py-4 font-medium">Document</th>
              <th className="px-5 py-4 font-medium">Type</th>
              <th className="px-5 py-4 font-medium">Pages</th>
              <th className="px-5 py-4 font-medium">Chunks</th>
              <th className="px-5 py-4 font-medium">Status</th>
              <th className="px-5 py-4 font-medium">Uploaded</th>
              <th className="px-5 py-4 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.id} className="border-t border-slate-200/70">
                <td className="px-5 py-4">
                  <Link href={`/documents/${document.id}`} className="font-medium text-slate-900">
                    {document.filename}
                  </Link>
                </td>
                <td className="px-5 py-4 uppercase text-slate-500">{document.file_type}</td>
                <td className="px-5 py-4">{document.pages}</td>
                <td className="px-5 py-4">{document.chunks_created}</td>
                <td className="px-5 py-4">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                    {document.indexing_status}
                  </span>
                </td>
                <td className="px-5 py-4 text-slate-500">
                  {new Date(document.upload_time).toLocaleString()}
                </td>
                <td className="px-5 py-4">
                  <div className="flex gap-2">
                    <button
                      className="rounded-xl border border-slate-200 px-3 py-2 hover:bg-slate-50"
                      onClick={() => onReindex?.(document.id)}
                    >
                      Reindex
                    </button>
                    <button
                      className="rounded-xl border border-rose-200 px-3 py-2 text-rose-700 hover:bg-rose-50"
                      onClick={() => onDelete?.(document.id)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
