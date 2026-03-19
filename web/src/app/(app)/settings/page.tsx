"use client";

import { useEffect, useState } from "react";
import { getSettings, type UserSettings } from "@/lib/api";
import styles from "./page.module.css";

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getSettings()
      .then((data) => {
        if (!cancelled) {
          setSettings(data);
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

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={`heading-xl ${styles.title}`}>Settings</h1>
        <p className={styles.subtitle}>
          Live backend configuration exposed by the FastAPI settings endpoint.
        </p>
      </div>

      <div className={styles.layout}>
        <nav className={styles.tabNav}>
          {["General", "Models", "Auth", "Runtime"].map((label) => (
            <button key={label} className={`${styles.tabBtn} ${styles.activeTab}`}>
              {label}
            </button>
          ))}
        </nav>

        <div className={styles.panel}>
          {error ? (
            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Unable to load settings</h3>
              <div className={styles.sectionBody}>{error}</div>
            </div>
          ) : null}

          <Section title="Application">
            <InfoRow label="App name" value={settings?.app_name || "Loading..."} />
            <InfoRow label="Environment" value={settings?.environment || "Loading..."} />
            <InfoRow label="Summaries enabled" value={String(settings?.summaries_enabled ?? "Loading...")} />
          </Section>

          <Section title="Models">
            <InfoRow
              label="Generation model"
              value={settings?.default_generation_model || "Loading..."}
            />
            <InfoRow
              label="Embedding model"
              value={settings?.default_embedding_model || "Loading..."}
            />
            <InfoRow
              label="Default retrieval mode"
              value={settings?.default_retrieval_mode || "Loading..."}
            />
          </Section>

          <Section title="Authentication and runtime">
            <InfoRow label="Auth enabled" value={String(settings?.auth_enabled ?? "Loading...")} />
            <InfoRow label="Auth provider" value={settings?.auth_provider || "Loading..."} />
            <InfoRow
              label="Vector store"
              value={settings?.vector_store_provider || "Loading..."}
            />
            <InfoRow
              label="Frontend backend URL"
              value={process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"}
            />
          </Section>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className={styles.section}>
      <h3 className={styles.sectionTitle}>{title}</h3>
      <div className={styles.sectionBody}>{children}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.envRow}>
      <span className={styles.envKey}>{label}</span>
      <span className={styles.envVal}>{value}</span>
    </div>
  );
}
