"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import ThemeToggle from "@/components/ui/ThemeToggle";
import styles from "./MarketingNav.module.css";

export default function MarketingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={`${styles.header} ${scrolled ? styles.scrolled : ""}`}>
      <nav className={styles.nav}>
        <Link href="/" className={styles.logo}>
          <span className={styles.logoMark}>⬡</span>
          <span className={styles.logoText}>RAG Smart QA</span>
        </Link>

        <ul className={styles.links}>
          <li><Link href="/#features" className={styles.link}>Features</Link></li>
          <li><Link href="/#how-it-works" className={styles.link}>How it works</Link></li>
          <li><Link href="/#pricing" className={styles.link}>Pricing</Link></li>
        </ul>

        <div className={styles.actions}>
          <ThemeToggle />
          <Link href="/signin" className="btn btn-ghost btn-sm">Sign in</Link>
          <Link href="/signin" className="btn btn-primary btn-sm">
            Get started
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </Link>
        </div>

        <button
          className={styles.mobileToggle}
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          <span className={`${styles.burger} ${mobileOpen ? styles.open : ""}`} />
        </button>
      </nav>

      {mobileOpen && (
        <div className={styles.mobileMenu}>
          <Link href="/#features" className={styles.mobileLink} onClick={() => setMobileOpen(false)}>Features</Link>
          <Link href="/#how-it-works" className={styles.mobileLink} onClick={() => setMobileOpen(false)}>How it works</Link>
          <Link href="/#pricing" className={styles.mobileLink} onClick={() => setMobileOpen(false)}>Pricing</Link>
          <div className={styles.mobileDivider} />
          <Link href="/signin" className="btn btn-secondary" onClick={() => setMobileOpen(false)}>Sign in</Link>
          <Link href="/signin" className="btn btn-primary" onClick={() => setMobileOpen(false)}>Get started</Link>
        </div>
      )}
    </header>
  );
}
