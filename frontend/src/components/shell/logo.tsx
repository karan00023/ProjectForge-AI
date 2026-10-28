"use client";

import { useId } from "react";
import { cx } from "@/components/ui";

export function Logo({ large, compact }: { large?: boolean; compact?: boolean }) {
  // Unique per instance: a hidden duplicate (e.g. the desktop sidebar on mobile) must not own the gradient.
  const gid = useId();
  return (
    <span className={cx("inline-flex items-center gap-2 font-semibold tracking-tight", large ? "text-xl" : "text-sm")}>
      <svg viewBox="0 0 32 32" className={large ? "size-9" : "size-7"} aria-hidden>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="var(--accent)" />
            <stop offset="0.55" stopColor="var(--accent-2)" />
            <stop offset="1" stopColor="var(--accent-3)" />
          </linearGradient>
        </defs>
        <rect x="1.5" y="1.5" width="29" height="29" rx="8" fill="none" stroke={`url(#${gid})`} strokeWidth="2.5" />
        <path d="M10 22V10h7.5a4 4 0 0 1 0 8H10" fill="none" stroke={`url(#${gid})`} strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="22.5" cy="22.5" r="2.2" fill="var(--accent-3)" />
      </svg>
      {!compact && (
        <span>
          ProjectForge <span className="text-accent-ink">AI</span>
        </span>
      )}
    </span>
  );
}
