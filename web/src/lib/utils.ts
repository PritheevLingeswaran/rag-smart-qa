/**
 * Format file size bytes to human-readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Format ISO date string to relative time or formatted date
 */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60));
    if (hours === 0) {
      const mins = Math.floor(diff / (1000 * 60));
      return mins <= 1 ? "just now" : `${mins} minutes ago`;
    }
    return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
  }
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  });
}

/**
 * Truncate string to max length with ellipsis
 */
export function truncate(str: string, max: number): string {
  if (str.length <= max) return str;
  return str.slice(0, max - 1) + "…";
}

/**
 * Generate initials from a name
 */
export function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();
}

/**
 * Join classnames conditionally
 */
export function cx(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Format document status to display text
 */
export function formatDocumentStatus(status: string): string {
  const map: Record<string, string> = {
    processing: "Processing",
    ready: "Ready",
    error: "Error",
  };
  return map[status] || status;
}
