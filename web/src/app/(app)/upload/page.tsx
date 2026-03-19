"use client";

import { useState, useRef, useCallback } from "react";
import Link from "next/link";
import { uploadDocument } from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import styles from "./page.module.css";

interface FileEntry {
  id: string;
  file: File;
  status: "pending" | "uploading" | "done" | "error";
  progress: number;
  error?: string;
}

const ACCEPTED = [".pdf", ".txt", ".md", ".html", ".htm"];
const MAX_SIZE = 25 * 1024 * 1024;

export default function UploadPage() {
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = (incoming: File[]) => {
    const entries: FileEntry[] = incoming.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: file.size <= MAX_SIZE ? "pending" : "error",
      progress: 0,
      error: file.size <= MAX_SIZE ? undefined : "File exceeds 25 MB limit.",
    }));
    setFiles((prev) => [...prev, ...entries]);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(Array.from(e.dataTransfer.files));
  }, []);

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((file) => file.id !== id));
  };

  const uploadOne = async (entry: FileEntry) => {
    setFiles((prev) =>
      prev.map((file) =>
        file.id === entry.id ? { ...file, status: "uploading", progress: 35 } : file
      )
    );

    try {
      await uploadDocument(entry.file);
      setFiles((prev) =>
        prev.map((file) =>
          file.id === entry.id ? { ...file, status: "done", progress: 100 } : file
        )
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed.";
      setFiles((prev) =>
        prev.map((file) =>
          file.id === entry.id
            ? { ...file, status: "error", progress: 0, error: message }
            : file
        )
      );
    }
  };

  const uploadAll = async () => {
    const pending = files.filter((file) => file.status === "pending");
    for (const entry of pending) {
      await uploadOne(entry);
    }
  };

  const pendingCount = files.filter((file) => file.status === "pending").length;
  const doneCount = files.filter((file) => file.status === "done").length;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={`heading-xl ${styles.title}`}>Upload Documents</h1>
          <p className={styles.subtitle}>
            Send files into the FastAPI backend and rebuild the retrieval indexes.
          </p>
        </div>
        {doneCount > 0 ? (
          <Link href="/documents" className="btn btn-secondary">
            View library →
          </Link>
        ) : null}
      </div>

      <div
        className={`${styles.dropZone} ${dragging ? styles.dragging : ""}`}
        onDrop={handleDrop}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED.join(",")}
          className={styles.fileInput}
          onChange={(e) => addFiles(Array.from(e.target.files || []))}
        />
        <div className={styles.dropIcon}>⬡</div>
        <div className={styles.dropText}>
          <span className={styles.dropPrimary}>
            {dragging ? "Release to add files" : "Drop files here, or click to browse"}
          </span>
          <span className={styles.dropSecondary}>
            Supports {ACCEPTED.join(", ")} · Max {formatBytes(MAX_SIZE)} per file
          </span>
        </div>
      </div>

      {files.length > 0 ? (
        <div className={styles.queue}>
          <div className={styles.queueHeader}>
            <span className={styles.queueTitle}>
              {files.length} file{files.length !== 1 ? "s" : ""} selected
              {doneCount > 0 ? ` · ${doneCount} uploaded` : ""}
            </span>
            <div className={styles.queueActions}>
              {pendingCount > 0 ? (
                <button className="btn btn-primary btn-sm" onClick={uploadAll}>
                  Upload {pendingCount} file{pendingCount !== 1 ? "s" : ""}
                </button>
              ) : null}
              <button className="btn btn-ghost btn-sm" onClick={() => setFiles([])}>
                Clear all
              </button>
            </div>
          </div>

          <div className={`card ${styles.fileList}`}>
            {files.map((entry) => (
              <div key={entry.id} className={styles.fileRow}>
                <div className={`${styles.fileIconWrap} ${styles[entry.status]}`}>◇</div>
                <div className={styles.fileInfo}>
                  <div className={styles.fileName}>{entry.file.name}</div>
                  <div className={styles.fileMeta}>
                    {formatBytes(entry.file.size)}
                    {entry.status === "uploading" ? (
                      <span className={styles.uploadingText}> · Uploading…</span>
                    ) : null}
                    {entry.status === "done" ? (
                      <span className={styles.doneText}> · Queued for indexing</span>
                    ) : null}
                    {entry.error ? <span className={styles.errorText}> · {entry.error}</span> : null}
                  </div>
                  {entry.status === "uploading" ? (
                    <div className={styles.progressBar}>
                      <div className={styles.progressFill} style={{ width: `${entry.progress}%` }} />
                    </div>
                  ) : null}
                </div>
                {entry.status !== "uploading" ? (
                  <button
                    className={styles.removeBtn}
                    onClick={() => removeFile(entry.id)}
                    aria-label="Remove file"
                  >
                    ×
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
