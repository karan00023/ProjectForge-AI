"use client";

import { AlertTriangle, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { MemberAvatar, PriorityIcon, TypeIcon } from "@/components/domain";
import { useProjectCtx } from "@/components/project/context";
import { NewItemDialog } from "@/components/project/new-item";
import { useSession } from "@/components/shell/session";
import { Badge, Button, cx, Field, FormError, Select, Spinner } from "@/components/ui";
import type { WorkItem, WorkItemStatus } from "@/lib/api";
import { fmtDate, STATUS_LABEL, todayIso } from "@/lib/format";
import { useUpdateItem } from "@/lib/queries";

const COLUMNS: WorkItemStatus[] = ["todo", "in_progress", "in_review", "blocked", "done"];
const CONTAINERS = new Set(["initiative", "epic", "feature"]);
const COLUMN_ACCENT: Record<string, string> = {
  backlog: "border-t-line-strong",
  todo: "border-t-accent",
  in_progress: "border-t-accent-2",
  in_review: "border-t-accent-3",
  blocked: "border-t-bad",
  done: "border-t-ok",
};

function Card({ item, onOpen }: { item: WorkItem; onOpen: () => void }) {
  const { members } = useProjectCtx();
  const { canWrite } = useSession();
  const overdue = item.due_date && item.status !== "done" && item.due_date < todayIso();
  return (
    <li
      draggable={canWrite}
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", item.id);
        e.dataTransfer.effectAllowed = "move";
      }}
      className="group"
    >
      <button
        type="button"
        onClick={onOpen}
        className="w-full rounded-lg border border-line bg-surface-2 p-2.5 text-left transition hover:border-accent hover:shadow-[0_0_16px_-8px_var(--accent)]"
      >
        <div className="flex items-center gap-1.5">
          <TypeIcon type={item.type} />
          <span className="font-mono text-[11px] text-faint">{item.key}</span>
          <span className="ml-auto flex items-center gap-1.5">
            <PriorityIcon priority={item.priority} />
            {item.story_points !== null && <Badge>{item.story_points}</Badge>}
          </span>
        </div>
        <p className="mt-1.5 line-clamp-3 text-sm leading-snug">{item.title}</p>
        <div className="mt-2 flex items-center gap-1.5">
          {item.labels.slice(0, 2).map((l) => (
            <Badge key={l} tone="accent">
              {l}
            </Badge>
          ))}
          {item.due_date && (
            <span className={cx("text-[11px] tabular-nums", overdue ? "font-semibold text-bad" : "text-faint")}>
              {overdue ? "Overdue · " : "Due "}
              {fmtDate(item.due_date)}
            </span>
          )}
          <span className="ml-auto">
            <MemberAvatar members={members} userId={item.assignee_id} size={20} />
          </span>
        </div>
      </button>
    </li>
  );
}

export default function BoardPage() {
  const { project, items, sprints, members, openItem } = useProjectCtx();
  const { canWrite } = useSession();
  const update = useUpdateItem(project.id);
  const activeSprint = sprints?.find((s) => s.status === "active");
  const [sprintFilter, setSprintFilter] = useState<string | null>(null);
  const [assignee, setAssignee] = useState("");
  const [showBacklog, setShowBacklog] = useState(false);
  const [dragOver, setDragOver] = useState<WorkItemStatus | null>(null);
  const [creating, setCreating] = useState<WorkItemStatus | null>(null);

  const sprintId = sprintFilter ?? activeSprint?.id ?? "all";
  const columns = useMemo(() => (showBacklog ? (["backlog", ...COLUMNS] as WorkItemStatus[]) : COLUMNS), [showBacklog]);

  const byStatus = useMemo(() => {
    const map = new Map<WorkItemStatus, WorkItem[]>();
    for (const c of columns) map.set(c, []);
    for (const w of items ?? []) {
      if (CONTAINERS.has(w.type)) continue;
      if (sprintId !== "all" && (sprintId === "none" ? w.sprint_id !== null : w.sprint_id !== sprintId)) continue;
      if (assignee && w.assignee_id !== assignee) continue;
      map.get(w.status)?.push(w);
    }
    return map;
  }, [items, sprintId, assignee, columns]);

  if (!items || !sprints) return <Spinner label="Loading board" />;

  function drop(status: WorkItemStatus, e: React.DragEvent) {
    e.preventDefault();
    setDragOver(null);
    const id = e.dataTransfer.getData("text/plain");
    const item = items?.find((w) => w.id === id);
    if (item && item.status !== status) update.mutate({ id, status });
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-56">
          <Field label="Sprint">
            <Select value={sprintId} onChange={(e) => setSprintFilter(e.target.value)}>
              <option value="all">All work</option>
              <option value="none">Not in a sprint</option>
              {sprints.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {s.status === "active" ? " (active)" : s.status === "closed" ? " (closed)" : ""}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <div className="w-48">
          <Field label="Assignee">
            <Select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
              <option value="">Everyone</option>
              {members.map((m) => (
                <option key={m.user.id} value={m.user.id}>
                  {m.user.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <label className="flex h-9 items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={showBacklog} onChange={(e) => setShowBacklog(e.target.checked)} className="accent-[var(--accent)]" />
          Show backlog column
        </label>
        <p className="ml-auto text-[11px] text-faint">
          {canWrite ? "Drag cards between columns, or open a card to change any field." : "Read-only: your role cannot change work items."}
        </p>
      </div>
      <FormError error={update.error} />

      <div className="scrollbar-thin -mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-3 sm:mx-0 sm:px-0">
        {columns.map((status) => {
          const list = byStatus.get(status) ?? [];
          const limit = project.wip_limits[status];
          const over = limit !== undefined && list.length > limit;
          const points = list.reduce((n, w) => n + (w.story_points ?? 0), 0);
          return (
            <section
              key={status}
              aria-label={`${STATUS_LABEL[status]} column`}
              onDragOver={(e) => {
                if (!canWrite) return;
                e.preventDefault();
                setDragOver(status);
              }}
              onDragLeave={() => setDragOver((s) => (s === status ? null : s))}
              onDrop={(e) => canWrite && drop(status, e)}
              className={cx(
                "panel flex w-[78vw] max-w-[300px] shrink-0 snap-start flex-col border-t-2 sm:w-[280px]",
                COLUMN_ACCENT[status],
                dragOver === status && "ring-2 ring-accent",
                over && "border-warn",
              )}
            >
              <header className="flex items-center gap-2 px-3 py-2.5">
                <h2 className="text-xs font-semibold uppercase tracking-wider">{STATUS_LABEL[status]}</h2>
                <Badge tone={over ? "warn" : "neutral"}>
                  {list.length}
                  {limit !== undefined && ` / ${limit}`}
                </Badge>
                <span className="text-[11px] text-faint">{points} pts</span>
                {canWrite && (
                  <Button variant="ghost" size="sm" className="ml-auto" aria-label={`Add item to ${STATUS_LABEL[status]}`} onClick={() => setCreating(status)}>
                    <Plus className="size-3.5" />
                  </Button>
                )}
              </header>
              {over && (
                <p className="mx-3 mb-2 flex items-center gap-1.5 rounded-md bg-warn-soft px-2 py-1 text-[11px] text-warn">
                  <AlertTriangle className="size-3.5" aria-hidden /> Over WIP limit — finish before starting more.
                </p>
              )}
              <ul className="scrollbar-thin flex max-h-[65vh] flex-1 flex-col gap-2 overflow-y-auto px-3 pb-3">
                {list.length === 0 && <li className="rounded-lg border border-dashed border-line py-6 text-center text-[11px] text-faint">Empty</li>}
                {list.map((w) => (
                  <Card key={w.id} item={w} onOpen={() => openItem(w.id)} />
                ))}
              </ul>
            </section>
          );
        })}
      </div>
      {creating && (
        <NewItemDialog
          open
          onClose={() => setCreating(null)}
          defaults={{ status: creating, type: "task", sprint_id: sprintId !== "all" && sprintId !== "none" ? sprintId : undefined }}
        />
      )}
    </div>
  );
}
