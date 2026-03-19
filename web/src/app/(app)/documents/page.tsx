"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getDocuments, type Document } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/utils";
import styles from "./page.module.css";

const STATUS_COLORS: Record<string, string> = {
  ready: "success",
  processing: "accent",
  queued: "accent",
  failed: "error",
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"grid" | "list">("list");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getDocuments()
      .then((data) => {
        if (!cancelled) {
          setDocuments(data);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(
    () =>
      documents.filter((doc) =>
        doc.filename.toLowerCase().includes(search.toLowerCase())
      ),
    [documents, search]
  );

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={`heading-xl ${styles.title}`}>Documents</h1>
          <p className={styles.subtitle}>{documents.length} documents in your library</p>
        </div>
        <Link href="/upload" className="btn btn-primary">
          Upload
        </Link>
      </div>

      <div className={styles.toolbar}>
        <div className={styles.searchWrap}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={styles.searchIcon}>
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="search"
            className={styles.searchInput}
            placeholder="Search documents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className={styles.viewToggle}>
          <button
            className={`${styles.viewBtn} ${view === "list" ? styles.activeView : ""}`}
            onClick={() => setView("list")}
            aria-label="List view"
          >
            List
          </button>
          <button
            className={`${styles.viewBtn} ${view === "grid" ? styles.activeView : ""}`}
            onClick={() => setView("grid")}
            aria-label="Grid view"
          >
            Grid
          </button>
        </div>
      </div>

      {error ? <p className={styles.subtitle}>Unable to load documents: {error}</p> : null}

      {filtered.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>◇</div>
          <h3>No documents found</h3>
          <p>{search ? `No results for "${search}"` : "Upload your first document to get started."}</p>
          {!search ? <Link href="/upload" className="btn btn-primary">Upload document</Link> : null}
        </div>
      ) : view === "list" ? (
        <div className={`card ${styles.listTable}`}>
          <div className={styles.tableHead}>
            <span>Name</span>
            <span>Size</span>
            <span>Pages</span>
            <span>Status</span>
            <span>Added</span>
            <span />
          </div>
          {filtered.map((doc) => (
            <div key={doc.id} className={styles.tableRow}>
              <div className={styles.docName}>
                <div className={styles.fileIcon}>◇</div>
                <Link href={`/documents/${doc.id}`} className={styles.docLink}>{doc.filename}</Link>
              </div>
              <span className={styles.cellMuted}>{formatBytes(doc.size_bytes)}</span>
              <span className={styles.cellMuted}>{doc.pages || "—"}</span>
              <span>
                <span className={`badge badge-${STATUS_COLORS[doc.indexing_status] || "muted"}`}>
                  {doc.indexing_status}
                </span>
              </span>
              <span className={styles.cellMuted}>{formatDate(doc.upload_time)}</span>
              <div className={styles.rowActions}>
                <Link href={`/chat?doc=${doc.id}`} className="btn btn-ghost btn-sm" title="Ask questions">
                  Chat
                </Link>
                <Link href={`/summaries?doc=${doc.id}`} className="btn btn-ghost btn-sm" title="View summary">
                  Summary
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={styles.docGrid}>
          {filtered.map((doc) => (
            <Link key={doc.id} href={`/documents/${doc.id}`} className={`card card-hover ${styles.docCard}`}>
              <div className={styles.docCardIcon}>◇</div>
              <div className={styles.docCardName}>{doc.filename}</div>
              <div className={styles.docCardMeta}>
                {formatBytes(doc.size_bytes)} · {doc.pages ? `${doc.pages} pages` : "Processing"}
              </div>
              <div className={styles.docCardFooter}>
                <span className={`badge badge-${STATUS_COLORS[doc.indexing_status] || "muted"}`}>
                  {doc.indexing_status}
                </span>
                <span className={styles.cellMuted}>{formatDate(doc.upload_time)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
