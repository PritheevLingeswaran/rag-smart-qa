"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDashboard, type DashboardResponse } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import styles from "./page.module.css";

const quickActions = [
  {
    href: "/chat",
    icon: "◎",
    title: "Ask a question",
    description: "Query across all your documents with natural language.",
    cta: "Start chatting ->",
  },
  {
    href: "/upload",
    icon: "⬡",
    title: "Upload documents",
    description: "Add PDFs, Word files, or text documents to your library.",
    cta: "Upload now ->",
  },
  {
    href: "/summaries",
    icon: "◈",
    title: "View summaries",
    description: "Review generated summaries and key insights from your files.",
    cta: "See summaries ->",
  },
];

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getDashboard()
      .then((data) => {
        if (!cancelled) {
          setDashboard(data);
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

  const recentDocuments = dashboard?.recent_documents ?? [];
  const recentSessions = dashboard?.recent_sessions ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={`heading-xl ${styles.title}`}>Dashboard</h1>
          <p className={styles.subtitle}>
            Connected to your FastAPI workspace and showing live project data.
          </p>
        </div>
        <Link href="/upload" className="btn btn-primary">
          Upload document
        </Link>
      </div>

      <div className={styles.statsGrid}>
        {[
          {
            label: "Documents",
            value: dashboard?.stats.total_documents ?? "—",
            sub: "in your library",
            icon: "◇",
          },
          {
            label: "Chat sessions",
            value: dashboard?.stats.total_sessions ?? "—",
            sub: "saved conversations",
            icon: "◎",
          },
          {
            label: "Chunks",
            value: dashboard?.stats.total_chunks ?? "—",
            sub: "indexed for retrieval",
            icon: "⬧",
          },
          {
            label: "Processing",
            value: dashboard?.stats.indexing_status.processing ?? 0,
            sub: "documents in flight",
            icon: "◈",
          },
        ].map((stat) => (
          <div key={stat.label} className={`card ${styles.statCard}`}>
            <div className={styles.statIcon}>{stat.icon}</div>
            <div className={styles.statValue}>{stat.value}</div>
            <div className={styles.statLabel}>{stat.label}</div>
            <div className={styles.statSub}>{stat.sub}</div>
          </div>
        ))}
      </div>

      <div className={styles.section}>
        <h2 className={`heading-lg ${styles.sectionTitle}`}>Quick actions</h2>
        <div className={styles.actionsGrid}>
          {quickActions.map((action) => (
            <Link key={action.href} href={action.href} className={`card card-hover ${styles.actionCard}`}>
              <div className={styles.actionIcon}>{action.icon}</div>
              <h3 className={styles.actionTitle}>{action.title}</h3>
              <p className={styles.actionDesc}>{action.description}</p>
              <span className={styles.actionCta}>{action.cta}</span>
            </Link>
          ))}
        </div>
      </div>

      <div className={styles.twoCol}>
        <div className={styles.section}>
          <h2 className={`heading-lg ${styles.sectionTitle}`}>Recent documents</h2>
          <div className={`card ${styles.activityCard}`}>
            {recentDocuments.length > 0 ? (
              recentDocuments.map((doc) => (
                <div key={doc.id} className={styles.activityItem}>
                  <div className={`${styles.activityDot} ${styles.upload}`} />
                  <div className={styles.activityContent}>
                    <p className={styles.activityText}>{doc.filename}</p>
                    <span className={styles.activityDoc}>{doc.indexing_status}</span>
                  </div>
                  <span className={styles.activityTime}>{formatDate(doc.upload_time)}</span>
                </div>
              ))
            ) : (
              <div className={styles.activityItem}>
                <div className={`${styles.activityDot} ${styles.upload}`} />
                <div className={styles.activityContent}>
                  <p className={styles.activityText}>No uploaded documents yet.</p>
                  <span className={styles.activityDoc}>Upload a file to get started.</span>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className={styles.section}>
          <h2 className={`heading-lg ${styles.sectionTitle}`}>Recent chat sessions</h2>
          <div className={`card ${styles.gettingStarted}`}>
            {recentSessions.length > 0 ? (
              recentSessions.map((session) => (
                <Link key={session.id} href="/chat" className={styles.checkItem}>
                  <div className={`${styles.checkbox} ${styles.checked}`}>•</div>
                  <span className={styles.done}>{session.title}</span>
                  <span style={{ marginLeft: "auto", opacity: 0.5 }}>
                    {formatDate(session.updated_at)}
                  </span>
                </Link>
              ))
            ) : (
              <>
                <Link href="/upload" className={styles.checkItem}>
                  <div className={styles.checkbox} />
                  <span>Upload your first document</span>
                </Link>
                <Link href="/chat" className={styles.checkItem}>
                  <div className={styles.checkbox} />
                  <span>Ask your first question</span>
                </Link>
                <Link href="/summaries" className={styles.checkItem}>
                  <div className={styles.checkbox} />
                  <span>Review a generated summary</span>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      {error ? <p className={styles.subtitle}>Unable to load dashboard: {error}</p> : null}
    </div>
  );
}
