import Link from "next/link";
import styles from "./MarketingFooter.module.css";

export default function MarketingFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.glow} />
      <div className="container">
        <div className={styles.top}>
          <div className={styles.brand}>
            <Link href="/" className={styles.logo}>
              <span className={styles.logoMark}>⬡</span>
              <span className={styles.logoText}>RAG Smart QA</span>
            </Link>
            <p className={styles.tagline}>
              Intelligent document understanding<br />for teams who move fast.
            </p>
          </div>

          <div className={styles.columns}>
            <div className={styles.col}>
              <h4 className={styles.colTitle}>Product</h4>
              <Link href="/#features" className={styles.colLink}>Features</Link>
              <Link href="/#how-it-works" className={styles.colLink}>How it works</Link>
              <Link href="/#pricing" className={styles.colLink}>Pricing</Link>
              <Link href="/changelog" className={styles.colLink}>Changelog</Link>
            </div>
            <div className={styles.col}>
              <h4 className={styles.colTitle}>Company</h4>
              <Link href="/about" className={styles.colLink}>About</Link>
              <Link href="/blog" className={styles.colLink}>Blog</Link>
              <Link href="/careers" className={styles.colLink}>Careers</Link>
              <Link href="/contact" className={styles.colLink}>Contact</Link>
            </div>
            <div className={styles.col}>
              <h4 className={styles.colTitle}>Legal</h4>
              <Link href="/privacy" className={styles.colLink}>Privacy</Link>
              <Link href="/terms" className={styles.colLink}>Terms</Link>
              <Link href="/security" className={styles.colLink}>Security</Link>
            </div>
          </div>
        </div>

        <div className={styles.bottom}>
          <p className={styles.copy}>
            © {new Date().getFullYear()} RAG Smart QA. All rights reserved.
          </p>
          <div className={styles.socials}>
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className={styles.social} aria-label="GitHub">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
              </svg>
            </a>
            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className={styles.social} aria-label="Twitter/X">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
