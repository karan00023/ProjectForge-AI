"use client";

import {
  AlertOctagon,
  ArrowDown,
  ArrowUp,
  Bookmark,
  Bug,
  CheckSquare,
  ChevronsUp,
  Equal,
  Flag,
  Layers,
  ListTree,
  Sparkle,
  SquareDashed,
} from "lucide-react";
import Link from "next/link";
import type { ComponentType } from "react";
import type { HealthLevel, HealthSignal, Member, Priority, ProjectHealth, WorkItemStatus, WorkItemType } from "@/lib/api";
import { STATUS_LABEL, TYPE_LABEL, humanize } from "@/lib/format";
import { Avatar, Badge, cx, Meter } from "./ui";

const HEALTH_TONE = { green: "ok", amber: "warn", red: "bad" } as const;
const HEALTH_LABEL = { green: "On track", amber: "Needs attention", red: "At risk" } as const;

export function HealthBadge({ level, className }: { level: HealthLevel; className?: string }) {
  return (
    <Badge tone={HEALTH_TONE[level]} className={className}>
      <span
        aria-hidden
        className={cx(
          "size-1.5 rounded-full",
          level === "green" ? "bg-ok" : level === "amber" ? "bg-warn" : "bg-bad",
        )}
      />
      {HEALTH_LABEL[level]}
    </Badge>
  );
}

const STATUS_TONE: Record<WorkItemStatus, "neutral" | "accent" | "ok" | "warn" | "bad" | "info"> = {
  backlog: "neutral",
  todo: "neutral",
  in_progress: "accent",
  in_review: "info",
  blocked: "bad",
  done: "ok",
  cancelled: "neutral",
};

export function StatusBadge({ status }: { status: WorkItemStatus }) {
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>;
}

const PRIORITY_ICON: Record<Priority, { Icon: ComponentType<{ className?: string }>; cls: string }> = {
  critical: { Icon: ChevronsUp, cls: "text-bad" },
  high: { Icon: ArrowUp, cls: "text-warn" },
  medium: { Icon: Equal, cls: "text-accent-3" },
  low: { Icon: ArrowDown, cls: "text-faint" },
};

export function PriorityIcon({ priority }: { priority: Priority }) {
  const { Icon, cls } = PRIORITY_ICON[priority];
  return (
    <span title={`${humanize(priority)} priority`} className="inline-flex">
      <Icon className={cx("size-3.5", cls)} aria-hidden />
      <span className="sr-only">{humanize(priority)} priority</span>
    </span>
  );
}

const TYPE_ICON: Record<WorkItemType, { Icon: ComponentType<{ className?: string }>; cls: string }> = {
  initiative: { Icon: Sparkle, cls: "text-accent-2" },
  epic: { Icon: Layers, cls: "text-accent-ink" },
  feature: { Icon: ListTree, cls: "text-accent-3" },
  story: { Icon: Bookmark, cls: "text-ok" },
  task: { Icon: CheckSquare, cls: "text-accent-3" },
  bug: { Icon: Bug, cls: "text-bad" },
  subtask: { Icon: SquareDashed, cls: "text-muted" },
};

export function TypeIcon({ type }: { type: WorkItemType }) {
  const { Icon, cls } = TYPE_ICON[type];
  return (
    <span title={TYPE_LABEL[type]} className="inline-flex">
      <Icon className={cx("size-3.5", cls)} aria-hidden />
      <span className="sr-only">{TYPE_LABEL[type]}</span>
    </span>
  );
}

export function MemberAvatar({ members, userId, size }: { members?: Member[]; userId?: string | null; size?: number }) {
  if (!userId) return <span className="text-xs text-faint">Unassigned</span>;
  const m = members?.find((x) => x.user.id === userId);
  if (!m) return <span className="text-xs text-faint">Unknown</span>;
  return <Avatar name={m.user.name} color={m.user.avatar_color} size={size} />;
}

export function memberName(members: Member[] | undefined, userId: string | null | undefined): string {
  if (!userId) return "Unassigned";
  return members?.find((m) => m.user.id === userId)?.user.name ?? "Unknown";
}

export function evidenceHref(projectId: string, e: HealthSignal["evidence"][number]): string {
  switch (e.entity_type) {
    case "work_item":
      return `/projects/${projectId}/backlog?item=${e.id}`;
    case "milestone":
      return `/projects/${projectId}/timeline#ms-${e.id}`;
    case "raid_item":
      return `/projects/${projectId}/raid#raid-${e.id}`;
    default:
      return `/projects/${projectId}`;
  }
}

/** Shows exactly which rules fired and the records behind them — the "why" of a health status. */
export function HealthExplanation({ projectId, health }: { projectId: string; health: ProjectHealth }) {
  if (health.signals.length === 0) {
    return (
      <p className="text-sm text-muted">
        No health rule fired on {health.evaluated_on}: no overdue or slipped milestones, overdue or blocked work, high
        risks or critical issues.
      </p>
    );
  }
  return (
    <ul className="space-y-2.5">
      {health.signals.map((s) => (
        <li key={s.code + s.level} className="flex gap-2.5">
          <AlertOctagon
            aria-hidden
            className={cx("mt-0.5 size-4 shrink-0", s.level === "red" ? "text-bad" : "text-warn")}
          />
          <div className="min-w-0">
            <p className="text-sm">
              <span className="sr-only">{s.level === "red" ? "Red" : "Amber"}: </span>
              {s.message}
            </p>
            <div className="mt-1 flex flex-wrap gap-1">
              {s.evidence.slice(0, 8).map((e) => (
                <Link
                  key={e.id}
                  href={evidenceHref(projectId, e)}
                  className="rounded border border-line bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted hover:border-accent hover:text-fg"
                >
                  {e.label}
                </Link>
              ))}
              {s.evidence.length > 8 && <span className="text-[11px] text-faint">+{s.evidence.length - 8} more</span>}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ProgressSummary({ health }: { health: ProjectHealth }) {
  const p = health.progress;
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-muted">Delivered</span>
        <span className="tabular-nums">
          {p.points_done}/{p.points_total} pts · {p.items_done}/{p.items_total} items
        </span>
      </div>
      <Meter value={p.points_done} max={p.points_total} label="Story points delivered" />
      {p.unestimated_items > 0 && (
        <p className="text-[11px] text-faint">
          {p.unestimated_items} item{p.unestimated_items === 1 ? "" : "s"} not estimated — excluded from points.
        </p>
      )}
    </div>
  );
}

export function MilestoneFlag({ className }: { className?: string }) {
  return <Flag className={cx("size-3.5 text-accent-2", className)} aria-hidden />;
}
