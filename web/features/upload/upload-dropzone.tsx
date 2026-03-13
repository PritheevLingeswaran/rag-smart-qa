"use client";

import { useState } from "react";
import { UploadCloud } from "lucide-react";

import { API_BASE_URL } from "@/lib/config";

type UploadState = {
  name: string;
  progress: number;
  status: "uploading" | "success" | "error";
  detail?: string;
};

export function UploadDropzone({ onUploaded }: { onUploaded?: () => void }) {
  const [items, setItems] = useState<UploadState[]>([]);

  async function handleFiles(fileList: FileList | null) {
    if (!fileList?.length) return;
    for (const file of Array.from(fileList)) {
      await uploadFile(file);
    }
    onUploaded?.();
  }

  function uploadFile(file: File) {
    return new Promise<void>((resolve) => {
      setItems((current) => [...current, { name: file.name, progress: 0, status: "uploading" }]);
      const formData = new FormData();
      formData.append("files", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}/api/upload`);
      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) return;
        const percent = Math.round((event.loaded / event.total) * 100);
        setItems((current) =>
          current.map((item) => (item.name === file.name ? { ...item, progress: percent } : item))
        );
      };
      xhr.onload = () => {
        const success = xhr.status >= 200 && xhr.status < 300;
        setItems((current) =>
          current.map((item) =>
            item.name === file.name
              ? {
                  ...item,
                  progress: 100,
                  status: success ? "success" : "error",
                  detail: success ? "Indexed in background" : xhr.responseText
                }
              : item
          )
        );
        resolve();
      };
      xhr.onerror = () => {
        setItems((current) =>
          current.map((item) =>
            item.name === file.name ? { ...item, status: "error", detail: "Network error" } : item
          )
        );
        resolve();
      };
      xhr.send(formData);
    });
  }

  return (
    <div className="space-y-4">
      <label className="panel flex cursor-pointer flex-col items-center justify-center gap-4 border-dashed p-8 text-center transition hover:border-accent/40 hover:bg-white">
        <span className="rounded-2xl bg-accent/10 p-3 text-accent">
          <UploadCloud className="h-6 w-6" />
        </span>
        <div>
          <p className="text-lg font-medium text-slate-900">Drop files to ingest and index</p>
          <p className="text-sm text-slate-500">
            PDF, TXT, Markdown, and HTML up to 25MB. Uploads trigger ingestion and summary caching.
          </p>
        </div>
        <input
          type="file"
          multiple
          className="hidden"
          onChange={(event) => void handleFiles(event.target.files)}
        />
      </label>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.name} className="panel-muted p-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-800">{item.name}</span>
              <span className="text-slate-500">{item.status}</span>
            </div>
            <div className="mt-3 h-2 rounded-full bg-slate-200">
              <div
                className="h-2 rounded-full bg-accent transition-all"
                style={{ width: `${item.progress}%` }}
              />
            </div>
            {item.detail ? <p className="mt-2 text-xs text-slate-500">{item.detail}</p> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
