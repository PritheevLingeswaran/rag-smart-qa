"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDocumentSummary, getDocuments, type Document, type DocumentSummary } from "@/lib/api";
import styles from "./page.module.css";

export default function SummariesPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [summary, setSummary] = useState<DocumentSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copying, setCopying] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getDocuments()
      .then((data) => {
        if (!cancelled) {
          setDocuments(data);
          setSelectedId(data[0]?.id ?? null);
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

  useEffect(() => {
    if (!selectedId) {
      return;
    }

    let cancelled = false;
    getDocumentSummary(selectedId)
      .then((data) => {
        if (!cancelled) {
          setSummary(data);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setSummary(null);
          setError(err.message);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const selectedDocument = documents.find((doc) => doc.id === selectedId) ?? null;

  const handleCopy = async () => {
    if (!summary?.summary) {
      return;
    }
    await navigator.clipboard.writeText(summary.summary);
    setCopying(true);
    setTimeout(() => setCopying(false), 2000);
  };

  return (
    <div className={styles.layout}>
      <div className={styles.listPanel}>
        <div className={styles.listHeader}>
          <h1 className={`heading-lg ${styles.listTitle}`}>Summaries</h1>
          <span className={styles.listCount}>{documents.length}</span>
        </div>
        <div className={styles.docList}>
          {documents.map((doc) => (
            <button
              key={doc.id}
              className={`${styles.docItem} ${selectedId === doc.id ? styles.activeItem : ""}`}
              onClick={() => {
                setSelectedId(doc.id);
                setError(null);
              }}
            >
              <div className={styles.docItemIcon}>◇</div>
              <div className={styles.docItemInfo}>
                <span className={styles.docItemName}>{doc.filename}</span>
                <span className={styles.docItemMeta}>{doc.summary_status}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className={styles.viewer}>
        <div className={styles.viewerHeader}>
          <div className={styles.viewerMeta}>
            <h2 className={styles.viewerTitle}>{selectedDocument?.filename || "Select a document"}</h2>
            <span className={styles.viewerStats}>
              {summary?.generated_at ? `Summarized ${summary.generated_at}` : "Live backend summary"}
            </span>
          </div>
          <div className={styles.viewerActions}>
            <button className="btn btn-ghost btn-sm" onClick={handleCopy} disabled={!summary?.summary}>
              {copying ? "Copied" : "Copy"}
            </button>
          </div>
        </div>

        {summary ? (
          <>
            <div className={styles.topics}>
              <span className={styles.topicsLabel}>Key topics</span>
              <div className={styles.topicTags}>
                {[...summary.topics, ...summary.keywords].slice(0, 6).map((topic) => (
                  <span key={topic} className="badge badge-accent">{topic}</span>
                ))}
              </div>
            </div>

            <div className={`card ${styles.summaryCard}`}>
              <div className={styles.summaryLabel}>AI Summary</div>
              <p className={styles.summaryText}>
                {summary.summary || summary.error_message || "No summary available yet."}
              </p>
            </div>

            <div className={styles.followUp}>
              {selectedId ? (
                <>
                  <Link href={`/chat?doc=${selectedId}`} className="btn btn-secondary">
                    Ask questions about this document
                  </Link>
                  <Link href={`/documents/${selectedId}`} className="btn btn-ghost">
                    View document details
                  </Link>
                </>
              ) : null}
            </div>
          </>
        ) : (
          <div className={`card ${styles.summaryCard}`}>
            <div className={styles.summaryLabel}>Summary status</div>
            <p className={styles.summaryText}>
              {error || "Select a document to load its summary."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
