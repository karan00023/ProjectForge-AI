"use client";

import { Bot, User } from "lucide-react";
import Link from "next/link";
import type { AuditEvent } from "@/lib/api";
import { fmtRelative } from "@/lib/format";
import { cx } from "./ui";

function hrefFor(e: AuditEvent): string | null {
  if (!e.project_id) return null;
  switch (e.entity_type) {
    case "work_item":
      return `/projects/${e.project_id}/backlog?item=${e.entity_id}`;
    case "raid_item":
      return `/projects/${e.project_id}/raid#raid-${e.entity_id}`;
    case "decision":
      return `/projects/${e.project_id}/decisions#dec-${e.entity_id}`;
    case "milestone":
      return `/projects/${e.project_id}/timeline#ms-${e.entity_id}`;
    default:
      return `/projects/${e.project_id}`;
  }
}

export function ActivityList({
  events,
  projectKeys,
  compact,
  since,
}: {
  events: AuditEvent[];
  projectKeys?: Record<string, string>;
  compact?: boolean;
  since?: string | null;
}) {
  if (events.length === 0) return <p className="p-3 text-sm text-muted">No activity recorded yet.</p>;
  // Events are newest-first; the marker goes above the first event older than the last visit.
  const markerIndex = since ? events.findIndex((e) => new Date(e.created_at) <= new Date(since)) : -1;
  return (
    <ol className="divide-y divide-line">
      {events.map((e, i) => {
        const href = hrefFor(e);
        const showMarker = i === markerIndex && i > 0;
        const body = (
          <div className="flex items-start gap-2.5">
            <span
              className={cx(
                "mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-full",
                e.actor_type === "agent" ? "bg-accent-soft text-accent-ink" : "bg-surface-3 text-muted",
              )}
              title={e.actor_type === "agent" ? "AI agent" : "Person"}
            >
              {e.actor_type === "agent" ? <Bot className="size-3.5" aria-hidden /> : <User className="size-3.5" aria-hidden />}
            </span>
            <div className="min-w-0 flex-1">
              <p className={cx("text-sm", compact && "line-clamp-2")}>
                <span className="font-medium">{e.actor_label}</span>{" "}
                <span className="text-muted">{e.summary}</span>
              </p>
              <p className="mt-0.5 text-[11px] text-faint">
                {e.project_id && projectKeys?.[e.project_id] && <span className="font-mono">{projectKeys[e.project_id]} · </span>}
                <time dateTime={e.created_at}>{fmtRelative(e.created_at)}</time>
              </p>
            </div>
          </div>
        );
        return (
          <li key={e.id}>
            {showMarker && (
              <div className="my-1 flex items-center gap-2 px-2 text-[10px] font-semibold uppercase tracking-wider text-accent-ink">
                <span className="h-px flex-1 bg-accent/40" /> Your last visit <span className="h-px flex-1 bg-accent/40" />
              </div>
            )}
            {href ? (
              <Link href={href} className="block rounded-lg p-2.5 hover:bg-surface-2">
                {body}
              </Link>
            ) : (
              <div className="p-2.5">{body}</div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
