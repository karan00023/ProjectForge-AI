import type { Priority, WorkItemStatus, WorkItemType } from "./api";

export const STATUS_ORDER: WorkItemStatus[] = [
  "backlog",
  "todo",
  "in_progress",
  "in_review",
  "blocked",
  "done",
  "cancelled",
];

export const STATUS_LABEL: Record<WorkItemStatus, string> = {
  backlog: "Backlog",
  todo: "To do",
  in_progress: "In progress",
  in_review: "Review",
  blocked: "Blocked",
  done: "Done",
  cancelled: "Cancelled",
};

export const TYPE_LABEL: Record<WorkItemType, string> = {
  initiative: "Initiative",
  epic: "Epic",
  feature: "Feature",
  story: "Story",
  task: "Task",
  bug: "Bug",
  subtask: "Subtask",
};

/** Allowed child types per parent, mirroring the backend hierarchy rule. */
export const TYPE_LEVEL: Record<WorkItemType, number> = {
  initiative: 0,
  epic: 1,
  feature: 2,
  story: 3,
  task: 4,
  bug: 4,
  subtask: 5,
};

export const PRIORITY_ORDER: Priority[] = ["critical", "high", "medium", "low"];

export function humanize(value: string): string {
  const s = value.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const dateFmt = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
const dateYearFmt = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" });

/** Planning dates are calendar dates (no time zone); parse them as local dates. */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y!, (m ?? 1) - 1, d ?? 1);
}

export function fmtDate(iso: string | null | undefined, withYear = false): string {
  if (!iso) return "—";
  const d = parseDate(iso);
  return (withYear || d.getFullYear() !== new Date().getFullYear() ? dateYearFmt : dateFmt).format(d);
}

export function daysBetween(fromIso: string, toIso: string): number {
  return Math.round((parseDate(toIso).getTime() - parseDate(fromIso).getTime()) / 86_400_000);
}

const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

export function fmtRelative(isoDateTime: string): string {
  const diff = (new Date(isoDateTime).getTime() - Date.now()) / 1000;
  const abs = Math.abs(diff);
  if (abs < 60) return "just now";
  if (abs < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  if (abs < 86400 * 30) return rtf.format(Math.round(diff / 86400), "day");
  return fmtDate(isoDateTime.slice(0, 10), true);
}


export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
