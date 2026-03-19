import styles from "./layout.module.css";
import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.layout}>
      <div className={styles.bg} aria-hidden="true">
        <div className={styles.glow1} />
        <div className={styles.glow2} />
        <div className={styles.grid} />
      </div>
      <div className={styles.topBar}>
        <Link href="/" className={styles.logo}>
          <span className={styles.logoMark}>⬡</span>
          <span className={styles.logoText}>RAG Smart QA</span>
        </Link>
      </div>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
