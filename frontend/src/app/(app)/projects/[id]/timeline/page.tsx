"use client";

import { Link2, Plus } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { memberName } from "@/components/domain";
import { useProjectCtx } from "@/components/project/context";
import { useSession } from "@/components/shell/session";
import { Badge, Button, cx, Dialog, Field, FormError, Input, Select, Spinner, Textarea } from "@/components/ui";
import type { Milestone, WorkItem } from "@/lib/api";
import { daysBetween, fmtDate, parseDate, todayIso } from "@/lib/format";
import { useCreateMilestone, useLinks, useRebaseline, useUpdateMilestone } from "@/lib/queries";

const ZOOM = { week: 18, month: 6, quarter: 2.5 } as const;
const LABEL_W = 260;

const BAR_COLOR: Record<string, string> = {
  done: "bg-ok/70",
  in_progress: "bg-gradient-to-r from-accent to-accent-2",
  in_review: "bg-accent-3/80",
  blocked: "bg-bad/80",
  todo: "bg-line-strong",
  backlog: "bg-line",
  cancelled: "bg-line",
};

function addDays(iso: string, n: number): string {
  const d = parseDate(iso);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function MilestoneDialog({ milestone, onClose }: { milestone: Milestone | "new"; onClose: () => void }) {
  const { project, members } = useProjectCtx();
  const create = useCreateMilestone(project.id);
  const update = useUpdateMilestone(project.id);
  const rebaseline = useRebaseline(project.id);
  const existing = milestone === "new" ? null : milestone;
  const [name, setName] = useState(existing?.name ?? "");
  const [description, setDescription] = useState(existing?.description ?? "");
  const [planned, setPlanned] = useState(existing?.planned_date ?? "");
  const [owner, setOwner] = useState(existing?.owner_id ?? "");
  const [reason, setReason] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    const body = { name, description: description || null, planned_date: planned, owner_id: owner || null };
    if (existing) await update.mutateAsync({ id: existing.id, ...body });
    else await create.mutateAsync(body);
    onClose();
  }

  return (
    <Dialog open onClose={onClose} title={existing ? `Milestone: ${existing.name}` : "New milestone"}>
      <form onSubmit={(e) => void submit(e).catch(() => undefined)} className="space-y-3">
        <Field label="Name">
          <Input required value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label="Description">
          <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            label={existing ? "Forecast date" : "Planned date"}
            hint={existing ? `Baseline ${fmtDate(existing.baseline_date, true)} — changing the forecast keeps the baseline.` : "Also becomes the baseline."}
          >
            <Input type="date" required value={planned} onChange={(e) => setPlanned(e.target.value)} />
          </Field>
          <Field label="Owner">
            <Select value={owner} onChange={(e) => setOwner(e.target.value)}>
              <option value="">None</option>
              {members.map((m) => (
                <option key={m.user.id} value={m.user.id}>
                  {m.user.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <FormError error={create.error ?? update.error ?? rebaseline.error} />
        <div className="flex flex-wrap justify-end gap-2">
          {existing && existing.status === "open" && (
            <Button
              type="button"
              variant="secondary"
              loading={update.isPending}
              onClick={() => update.mutate({ id: existing.id, status: "completed" }, { onSuccess: onClose })}
            >
              Mark completed today
            </Button>
          )}
          <Button type="submit" variant="primary" loading={create.isPending || update.isPending}>
            {existing ? "Save" : "Create milestone"}
          </Button>
        </div>
      </form>
      {existing && existing.baseline_date !== existing.planned_date && existing.status === "open" && (
        <form
          className="mt-5 space-y-2 border-t border-line pt-4"
          onSubmit={(e) => {
            e.preventDefault();
            rebaseline.mutate({ id: existing.id, reason }, { onSuccess: onClose });
          }}
        >
          <p className="text-sm font-medium">Re-baseline to {fmtDate(existing.planned_date, true)}</p>
          <p className="text-xs text-muted">
            Accepts the current forecast as the new commitment. The previous baseline and your reason are kept in the audit log.
          </p>
          <Textarea required minLength={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (e.g. approved change request CR-12)" aria-label="Re-baseline reason" />
          <Button type="submit" variant="danger" loading={rebaseline.isPending}>
            Re-baseline
          </Button>
        </form>
      )}
    </Dialog>
  );
}

export default function TimelinePage() {
  const { project, items, milestones, members, openItem } = useProjectCtx();
  const { canWrite } = useSession();
  const links = useLinks(project.id);
  const [zoom, setZoom] = useState<keyof typeof ZOOM>("month");
  const [editing, setEditing] = useState<Milestone | "new" | null>(null);
  const today = todayIso();
  const pxPerDay = ZOOM[zoom];
  const scrollRef = useRef<HTMLDivElement>(null);

  // Scroll a milestone into view when linked to via #ms-<id>.
  useEffect(() => {
    const hash = window.location.hash;
    if (hash.startsWith("#ms-") && milestones) document.getElementById(hash.slice(1))?.scrollIntoView({ block: "center" });
  }, [milestones]);

  const { start, end, groups } = useMemo(() => {
    const dated = (items ?? []).filter((w) => (w.start_date || w.due_date) && w.status !== "cancelled");
    const dates = [
      project.start_date,
      project.target_date,
      today,
      ...dated.flatMap((w) => [w.start_date, w.due_date]),
      ...(milestones ?? []).flatMap((m) => [m.baseline_date, m.planned_date, m.actual_date]),
    ].filter((d): d is string => !!d);
    const sorted = [...dates].sort();
    const s = addDays(sorted[0] ?? today, -7);
    const e = addDays(sorted[sorted.length - 1] ?? today, 14);
    const byId = new Map((items ?? []).map((w) => [w.id, w]));
    const topOf = (w: WorkItem): WorkItem => {
      let cur = w;
      while (cur.parent_id && byId.get(cur.parent_id)) cur = byId.get(cur.parent_id)!;
      return cur;
    };
    const isContainer = (w: WorkItem) => ["initiative", "epic", "feature"].includes(w.type);
    const g = new Map<string, { epic: WorkItem | null; rows: WorkItem[] }>();
    for (const w of dated) {
      const top = topOf(w);
      if (top.id === w.id && isContainer(w)) continue; // containers are group headers, not rows
      const key = top.id !== w.id && isContainer(top) ? top.id : "none";
      if (!g.has(key)) g.set(key, { epic: key === "none" ? null : top, rows: [] });
      g.get(key)!.rows.push(w);
    }
    for (const v of g.values()) v.rows.sort((a, b) => (a.start_date ?? a.due_date ?? "").localeCompare(b.start_date ?? b.due_date ?? ""));
    return { start: s, end: e, groups: [...g.values()] };
  }, [items, milestones, project.start_date, project.target_date, today]);

  // Open the chart around "today" rather than at the project start (unless a milestone is targeted).
  const todayOffset = daysBetween(start, today) * pxPerDay;
  const loaded = !!items && !!milestones;
  useEffect(() => {
    const el = scrollRef.current;
    if (el && loaded && !window.location.hash.startsWith("#ms-")) el.scrollLeft = Math.max(0, todayOffset - el.clientWidth / 3);
  }, [todayOffset, loaded]);

  if (!items || !milestones) return <Spinner label="Loading timeline" />;

  const totalDays = daysBetween(start, end);
  const width = totalDays * pxPerDay;
  const x = (iso: string) => daysBetween(start, iso) * pxPerDay;
  const blockersOf = (id: string) => (links.data ?? []).filter((l) => l.type === "blocks" && l.target_id === id).length;

  const months: { label: string; left: number }[] = [];
  const cursor = parseDate(start);
  cursor.setDate(1);
  while (cursor <= parseDate(end)) {
    const iso = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}-01`;
    if (iso >= start) months.push({ label: cursor.toLocaleDateString(undefined, { month: "short", year: "2-digit" }), left: x(iso) });
    cursor.setMonth(cursor.getMonth() + 1);
  }

  const todayLeft = x(today);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <div role="group" aria-label="Zoom" className="inline-flex rounded-lg border border-line p-0.5">
          {(Object.keys(ZOOM) as (keyof typeof ZOOM)[]).map((z) => (
            <button
              key={z}
              type="button"
              aria-pressed={zoom === z}
              onClick={() => setZoom(z)}
              className={cx("rounded-md px-2.5 py-1 text-xs capitalize", zoom === z ? "bg-accent-soft text-fg" : "text-muted")}
            >
              {z}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted">
          <span className="flex items-center gap-1">
            <span className="inline-block size-2.5 rotate-45 bg-accent-2" /> Forecast
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block size-2.5 rotate-45 border border-faint" /> Baseline
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block size-2.5 rotate-45 bg-ok" /> Completed
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-3 w-px bg-accent-3" /> Today
          </span>
        </div>
        {canWrite && (
          <Button className="ml-auto" variant="primary" onClick={() => setEditing("new")}>
            <Plus className="size-4" aria-hidden /> Milestone
          </Button>
        )}
      </div>

      <div ref={scrollRef} className="panel scrollbar-thin overflow-x-auto">
        <div style={{ width: LABEL_W + width }} className="relative text-sm">
          {/* Month header */}
          <div className="sticky top-0 z-10 flex h-8 border-b border-line bg-surface">
            <div style={{ width: LABEL_W }} className="sticky left-0 z-10 shrink-0 border-r border-line bg-surface px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">
              Plan
            </div>
            <div className="relative flex-1">
              {months.map((m) => (
                <span key={m.left} className="absolute top-1.5 border-l border-line pl-1 text-[11px] text-faint" style={{ left: m.left }}>
                  {m.label}
                </span>
              ))}
            </div>
          </div>

          {/* Today line */}
          <div aria-hidden className="pointer-events-none absolute bottom-0 top-8 z-0 w-px bg-accent-3/70" style={{ left: LABEL_W + todayLeft }} />

          {/* Milestones */}
          <div className="border-b border-line bg-surface-2/40 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-faint">Milestones</div>
          {milestones.length === 0 && <p className="px-3 py-2 text-xs text-muted">No milestones.</p>}
          {milestones.map((m) => {
            const forecast = m.actual_date ?? m.planned_date;
            const a = Math.min(x(m.baseline_date), x(forecast));
            const b = Math.max(x(m.baseline_date), x(forecast));
            return (
              <div key={m.id} id={`ms-${m.id}`} className="flex h-10 items-center border-b border-line/60 target:bg-accent-soft">
                <button
                  type="button"
                  onClick={() => canWrite && setEditing(m)}
                  style={{ width: LABEL_W }}
                  className="sticky left-0 z-10 flex h-full shrink-0 items-center gap-2 border-r border-line bg-surface px-3 text-left hover:text-accent-ink disabled:cursor-default"
                  disabled={!canWrite}
                  title={`${m.name} — owner ${memberName(members, m.owner_id)}`}
                >
                  <span className="min-w-0 flex-1 truncate">{m.name}</span>
                  {m.overdue ? (
                    <Badge tone="bad">Overdue</Badge>
                  ) : m.variance_working_days > 0 ? (
                    <Badge tone={m.variance_working_days > 10 ? "bad" : m.variance_working_days > 5 ? "warn" : "neutral"}>+{m.variance_working_days}wd</Badge>
                  ) : null}
                </button>
                <div className="relative h-full flex-1">
                  {b > a && <div className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-warn/60" style={{ left: a, width: b - a }} />}
                  <span
                    title={`Baseline ${fmtDate(m.baseline_date, true)}`}
                    className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rotate-45 border border-faint bg-surface"
                    style={{ left: x(m.baseline_date) }}
                  />
                  <span
                    title={`${m.status === "completed" ? "Completed" : "Forecast"} ${fmtDate(forecast, true)}`}
                    className={cx(
                      "absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rotate-45 shadow-[0_0_10px_var(--accent-2)]",
                      m.status === "completed" ? "bg-ok" : m.overdue ? "bg-bad" : "bg-accent-2",
                    )}
                    style={{ left: x(forecast) }}
                  />
                  <span className="absolute top-1/2 ml-3 -translate-y-1/2 whitespace-nowrap text-[11px] text-muted" style={{ left: x(forecast) }}>
                    {fmtDate(forecast)}
                  </span>
                </div>
              </div>
            );
          })}

          {/* Work grouped by top-level epic */}
          {groups.map((g) => (
            <div key={g.epic?.id ?? "none"}>
              <div className="flex h-8 items-center border-b border-line bg-surface-2/40">
                <div style={{ width: LABEL_W }} className="sticky left-0 z-10 flex h-full shrink-0 items-center border-r border-line bg-surface-2 px-3">
                  {g.epic ? (
                    <button type="button" onClick={() => openItem(g.epic!.id)} className="truncate text-xs font-semibold hover:text-accent-ink">
                      <span className="mr-1 font-mono text-faint">{g.epic.key}</span>
                      {g.epic.title}
                    </button>
                  ) : (
                    <span className="text-xs font-semibold text-muted">Not under an epic</span>
                  )}
                </div>
                <div className="relative h-full flex-1">
                  {g.rows.length > 0 && (() => {
                    const ds = g.rows.flatMap((w) => [w.start_date ?? w.due_date!, w.due_date ?? w.start_date!]).sort();
                    return <div className="absolute top-1/2 h-1 -translate-y-1/2 rounded bg-accent/30" style={{ left: x(ds[0]!), width: Math.max(4, x(ds[ds.length - 1]!) - x(ds[0]!) + pxPerDay) }} />;
                  })()}
                </div>
              </div>
              {g.rows.map((w) => {
                const s = w.start_date ?? w.due_date!;
                const e = w.due_date ?? w.start_date!;
                const overdue = w.due_date && w.due_date < today && w.status !== "done";
                const blockers = blockersOf(w.id);
                return (
                  <div key={w.id} className="flex h-9 items-center border-b border-line/40">
                    <button
                      type="button"
                      onClick={() => openItem(w.id)}
                      style={{ width: LABEL_W }}
                      className="sticky left-0 z-10 flex h-full shrink-0 items-center gap-1.5 border-r border-line bg-surface px-3 pl-5 text-left text-xs hover:text-accent-ink"
                    >
                      <span className="font-mono text-[11px] text-faint">{w.key}</span>
                      <span className="min-w-0 flex-1 truncate">{w.title}</span>
                      {blockers > 0 && (
                        <span title={`${blockers} blocking dependenc${blockers === 1 ? "y" : "ies"}`} className="flex items-center gap-0.5 text-[10px] text-warn">
                          <Link2 className="size-3" aria-hidden />
                          {blockers}
                        </span>
                      )}
                    </button>
                    <div className="relative h-full flex-1">
                      <button
                        type="button"
                        onClick={() => openItem(w.id)}
                        aria-label={`${w.key} ${fmtDate(s)} to ${fmtDate(e)}`}
                        className={cx(
                          "absolute top-1/2 h-4 -translate-y-1/2 rounded-sm",
                          BAR_COLOR[w.status],
                          overdue && "ring-1 ring-bad",
                        )}
                        style={{ left: x(s), width: Math.max(pxPerDay, x(e) - x(s) + pxPerDay) }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <p className="text-[11px] text-faint">
        Only items with a start or due date appear. Critical-path and slip-impact analysis arrive in Phase 4 (see roadmap).
      </p>
      <div className="sr-only">
        {/* Text alternative of the chart for assistive technology. */}
        <h2>Milestones</h2>
        <ul>
          {milestones.map((m) => (
            <li key={m.id}>
              {m.name}: baseline {m.baseline_date}, forecast {m.planned_date}
              {m.actual_date ? `, completed ${m.actual_date}` : ""}.
            </li>
          ))}
        </ul>
      </div>
      {editing && <MilestoneDialog milestone={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}
