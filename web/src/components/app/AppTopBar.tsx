"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { signOut } from "next-auth/react";
import ThemeToggle from "@/components/ui/ThemeToggle";
import { getInitials } from "@/lib/utils";
import styles from "./AppTopBar.module.css";

interface AppTopBarProps {
  user?: {
    name?: string | null;
    email?: string | null;
    image?: string | null;
  };
}

export default function AppTopBar({ user }: AppTopBarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const initials = user?.name ? getInitials(user.name) : "?";

  return (
    <header className={styles.topBar}>
      <div className={styles.left}>
        {/* Breadcrumb placeholder - individual pages can override */}
      </div>

      <div className={styles.right}>
        <ThemeToggle />

        <div className={styles.userMenu} ref={dropdownRef}>
          <button
            className={styles.avatarBtn}
            onClick={() => setDropdownOpen(!dropdownOpen)}
            aria-label="User menu"
            aria-expanded={dropdownOpen}
          >
            {user?.image ? (
              <Image
                src={user.image}
                alt={user.name || "User"}
                width={32}
                height={32}
                className={styles.avatarImg}
              />
            ) : (
              <div className={styles.avatarInitials}>{initials}</div>
            )}
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`${styles.chevron} ${dropdownOpen ? styles.open : ""}`}
              aria-hidden
            >
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>

          {dropdownOpen && (
            <div className={styles.dropdown} role="menu">
              {/* User info */}
              <div className={styles.dropdownHeader}>
                {user?.image ? (
                  <Image
                    src={user.image}
                    alt={user.name || "User"}
                    width={36}
                    height={36}
                    className={styles.dropdownAvatarImg}
                  />
                ) : (
                  <div className={styles.dropdownAvatarInitials}>{initials}</div>
                )}
                <div className={styles.dropdownUserInfo}>
                  <span className={styles.dropdownName}>{user?.name || "User"}</span>
                  <span className={styles.dropdownEmail}>{user?.email || ""}</span>
                </div>
              </div>

              <div className={styles.dropdownDivider} />

              <Link href="/dashboard" className={styles.dropdownItem} role="menuitem" onClick={() => setDropdownOpen(false)}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                  <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
                </svg>
                Dashboard
              </Link>
              <Link href="/settings" className={styles.dropdownItem} role="menuitem" onClick={() => setDropdownOpen(false)}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
                Settings
              </Link>

              <div className={styles.dropdownDivider} />

              <button
                className={`${styles.dropdownItem} ${styles.signOut}`}
                role="menuitem"
                onClick={() => signOut({ callbackUrl: "/" })}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
