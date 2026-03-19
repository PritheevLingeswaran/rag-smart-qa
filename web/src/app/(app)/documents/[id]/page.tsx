"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getDocument, type DocumentDetail } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/utils";
import styles from "./page.module.css";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id) {
      return;
    }

    let cancelled = false;
    getDocument(params.id)
      .then((data) => {
        if (!cancelled) {
          setDocument(data);
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
  }, [params?.id]);

  if (error) {
    return <div className={styles.page}>Unable to load document: {error}</div>;
  }

  if (!document) {
    return <div className={styles.page}>Loading document...</div>;
  }

  return (
    <div className={styles.page}>
      <nav className={styles.breadcrumb}>
        <Link href="/documents" className={styles.breadLink}>Documents</Link>
        <span className={styles.breadSep}>/</span>
        <span className={styles.breadCurrent}>{document.filename}</span>
      </nav>

      <div className={styles.header}>
        <div className={styles.docIcon}>◇</div>
        <div className={styles.headerInfo}>
          <h1 className={`heading-xl ${styles.docTitle}`}>{document.filename}</h1>
          <div className={styles.docMeta}>
            <span className="badge badge-success">{document.indexing_status}</span>
            <span className={styles.metaItem}>{document.pages || 0} pages</span>
            <span className={styles.metaItem}>Added {formatDate(document.upload_time)}</span>
            <span className={styles.metaItem}>{formatBytes(document.size_bytes)}</span>
          </div>
        </div>
        <div className={styles.headerActions}>
          <Link href={`/chat?doc=${document.id}`} className="btn btn-primary">
            Ask questions
          </Link>
          <Link href={`/summaries?doc=${document.id}`} className="btn btn-secondary">
            Summary
          </Link>
        </div>
      </div>

      <div className={styles.statsGrid}>
        {[
          { label: "Pages", value: document.pages, icon: "◇" },
          { label: "File size", value: formatBytes(document.size_bytes), icon: "◈" },
          { label: "Chunks", value: document.chunks_created, icon: "◎" },
          { label: "Summary", value: document.summary?.status || document.summary_status, icon: "⬧" },
        ].map((stat) => (
          <div key={stat.label} className={`card ${styles.statCard}`}>
            <div className={styles.statIcon}>{stat.icon}</div>
            <div className={styles.statValue}>{stat.value}</div>
            <div className={styles.statLabel}>{stat.label}</div>
          </div>
        ))}
      </div>

      <div className={styles.twoCol}>
        <div>
          <h2 className={`heading-lg ${styles.sectionTitle}`}>Document preview</h2>
          <div className={`card ${styles.queryList}`}>
            {document.preview.length > 0 ? (
              document.preview.slice(0, 3).map((page) => (
                <div key={page.page} className={styles.queryItem}>
                  <strong>Page {page.page}</strong>
                  <span>{page.text.slice(0, 220)}...</span>
                </div>
              ))
            ) : (
              <div className={styles.queryItem}>No preview available.</div>
            )}
          </div>
        </div>

        <div>
          <h2 className={`heading-lg ${styles.sectionTitle}`}>Document info</h2>
          <div className={`card ${styles.infoCard}`}>
            {[
              { label: "File name", value: document.filename },
              { label: "File type", value: document.file_type.toUpperCase() },
              { label: "File size", value: formatBytes(document.size_bytes) },
              { label: "Pages", value: String(document.pages || 0) },
              { label: "Chunks", value: String(document.chunks_created || 0) },
              { label: "Uploaded", value: formatDate(document.upload_time) },
            ].map((row) => (
              <div key={row.label} className={styles.infoRow}>
                <span className={styles.infoLabel}>{row.label}</span>
                <span className={styles.infoValue}>{row.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {document.summary?.summary ? (
        <div style={{ marginTop: "2rem" }}>
          <h2 className={`heading-lg ${styles.sectionTitle}`}>Summary</h2>
          <div className={`card ${styles.infoCard}`}>{document.summary.summary}</div>
        </div>
      ) : null}
    </div>
  );
}
