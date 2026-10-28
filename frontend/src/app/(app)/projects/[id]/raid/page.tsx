"use client";

import { Plus } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { MemberAvatar, memberName } from "@/components/domain";
import { useProjectCtx } from "@/components/project/context";
import { useSession } from "@/components/shell/session";
import { Badge, Button, cx, Dialog, EmptyState, ErrorState, Field, FormError, Input, Panel, Select, Spinner, Textarea } from "@/components/ui";
import type { Raid, RaidCreate } from "@/lib/api";
import { fmtDate, humanize, PRIORITY_ORDER, todayIso } from "@/lib/format";
import { useCreateRaid, useRaid, useUpdateRaid } from "@/lib/queries";

const TYPES = ["risk", "assumption", "issue", "dependency"] as const;
const STATUSES = ["open", "in_progress", "monitoring", "resolved", "closed", "accepted"] as const;
const OPEN = new Set(["open", "in_progress", "monitoring"]);

function scoreTone(score: number | null) {
  if (score === null) return "neutral" as const;
  return score >= 15 ? ("bad" as const) : score >= 10 ? ("warn" as const) : ("ok" as const);
}

function RaidDialog({ item, defaultType, onClose }: { item: Raid | null; defaultType: Raid["type"]; onClose: () => void }) {
  const { project, members, items, milestones } = useProjectCtx();
  const create = useCreateRaid(project.id);
  const update = useUpdateRaid(project.id);
  const [form, setForm] = useState<RaidCreate>(
    item
      ? {
          type: item.type,
          title: item.title,
          description: item.description,
          status: item.status,
          priority: item.priority,
          probability: item.probability,
          impact: item.impact,
          mitigation: item.mitigation,
          contingency: item.contingency,
          escalation_trigger: item.escalation_trigger,
          evidence: item.evidence,
          owner_id: item.owner_id,
          due_date: item.due_date,
          milestone_id: item.milestone_id,
          work_item_ids: item.work_item_ids,
        }
      : { type: defaultType, title: "", impact: 3, probability: defaultType === "risk" ? 3 : null, priority: "medium", status: "open" },
  );
  const set = <K extends keyof RaidCreate>(k: K, v: RaidCreate[K]) => setForm((f) => ({ ...f, [k]: v }));
  const isRisk = form.type === "risk";

  async function submit(e: FormEvent) {
    e.preventDefault();
    const body = { ...form, probability: isRisk ? form.probability : null };
    if (item) {
      // `type` is fixed after creation.
      const { type: _type, ...patch } = body;
      void _type;
      await update.mutateAsync({ id: item.id, ...patch });
    } else {
      await create.mutateAsync(body);
    }
    onClose();
  }

  return (
    <Dialog open onClose={onClose} title={item ? `${item.key} · ${humanize(item.type)}` : `Log ${form.type}`} wide>
      <form onSubmit={(e) => void submit(e).catch(() => undefined)} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-[10rem_1fr]">
          <Field label="Type">
            <Select disabled={!!item} value={form.type} onChange={(e) => set("type", e.target.value as Raid["type"])}>
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {humanize(t)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Title">
            <Input required value={form.title} onChange={(e) => set("title", e.target.value)} />
          </Field>
        </div>
        <Field label="Description">
          <Textarea rows={2} value={form.description ?? ""} onChange={(e) => set("description", e.target.value || null)} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-4">
          {isRisk && (
            <Field label="Probability (1–5)">
              <Select value={form.probability ?? 3} onChange={(e) => set("probability", Number(e.target.value))}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </Select>
            </Field>
          )}
          <Field label="Impact (1–5)">
            <Select value={form.impact ?? 3} onChange={(e) => set("impact", Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </Select>
          </Field>
          <Field label="Priority">
            <Select value={form.priority} onChange={(e) => set("priority", e.target.value as Raid["priority"])}>
              {PRIORITY_ORDER.map((p) => (
                <option key={p} value={p}>
                  {humanize(p)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Status">
            <Select value={form.status} onChange={(e) => set("status", e.target.value as Raid["status"])}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {humanize(s)}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        {isRisk && (
          <p className="text-xs text-muted">
            Score = probability × impact = <strong>{(form.probability ?? 0) * (form.impact ?? 0)}</strong> (≥ 15 turns project health red).
          </p>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Mitigation">
            <Textarea rows={2} value={form.mitigation ?? ""} onChange={(e) => set("mitigation", e.target.value || null)} />
          </Field>
          <Field label="Contingency">
            <Textarea rows={2} value={form.contingency ?? ""} onChange={(e) => set("contingency", e.target.value || null)} />
          </Field>
          <Field label="Escalation trigger">
            <Textarea rows={2} value={form.escalation_trigger ?? ""} onChange={(e) => set("escalation_trigger", e.target.value || null)} />
          </Field>
          <Field label="Evidence">
            <Textarea rows={2} value={form.evidence ?? ""} onChange={(e) => set("evidence", e.target.value || null)} />
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Owner">
            <Select value={form.owner_id ?? ""} onChange={(e) => set("owner_id", e.target.value || null)}>
              <option value="">None</option>
              {members.map((m) => (
                <option key={m.user.id} value={m.user.id}>
                  {m.user.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Due / review date">
            <Input type="date" value={form.due_date ?? ""} onChange={(e) => set("due_date", e.target.value || null)} />
          </Field>
          <Field label="Milestone at stake">
            <Select value={form.milestone_id ?? ""} onChange={(e) => set("milestone_id", e.target.value || null)}>
              <option value="">None</option>
              {milestones?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="Related work items" hint="Ctrl/⌘-click to select several">
          <Select
            multiple
            className="h-28"
            value={form.work_item_ids ?? []}
            onChange={(e) => set("work_item_ids", Array.from(e.target.selectedOptions, (o) => o.value))}
          >
            {items
              ?.filter((w) => !["initiative", "epic"].includes(w.type))
              .map((w) => (
                <option key={w.id} value={w.id}>
                  {w.key} {w.title}
                </option>
              ))}
          </Select>
        </Field>
        <FormError error={create.error ?? update.error} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={create.isPending || update.isPending}>
            {item ? "Save" : "Log item"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function HeatMap({ risks, cell, onCell }: { risks: Raid[]; cell: string | null; onCell: (c: string | null) => void }) {
  const counts = new Map<string, number>();
  for (const r of risks) if (r.probability !== null) counts.set(`${r.probability}-${r.impact}`, (counts.get(`${r.probability}-${r.impact}`) ?? 0) + 1);
  return (
    <div>
      <div className="flex gap-2">
        <div className="flex flex-col justify-center">
          <span className="-rotate-180 text-[10px] uppercase tracking-wider text-faint [writing-mode:vertical-rl]">Probability</span>
        </div>
        <div className="grid flex-1 grid-cols-5 gap-1" role="group" aria-label="Open risks by probability and impact">
          {[5, 4, 3, 2, 1].flatMap((p) =>
            [1, 2, 3, 4, 5].map((i) => {
              const key = `${p}-${i}`;
              const n = counts.get(key) ?? 0;
              const score = p * i;
              return (
                <button
                  key={key}
                  type="button"
                  aria-label={`Probability ${p}, impact ${i}: ${n} risk${n === 1 ? "" : "s"}`}
                  aria-pressed={cell === key}
                  onClick={() => onCell(cell === key ? null : key)}
                  className={cx(
                    "flex aspect-square items-center justify-center rounded-md text-xs font-semibold transition",
                    score >= 15 ? "bg-bad/25 text-bad" : score >= 10 ? "bg-warn/25 text-warn" : "bg-ok/15 text-ok",
                    n === 0 && "opacity-40",
                    cell === key && "ring-2 ring-accent",
                  )}
                >
                  {n || ""}
                </button>
              );
            }),
          )}
        </div>
      </div>
      <p className="mt-1 pl-6 text-center text-[10px] uppercase tracking-wider text-faint">Impact →</p>
    </div>
  );
}

export default function RaidPage() {
  const { project, members } = useProjectCtx();
  const { canWrite } = useSession();
  const raid = useRaid(project.id);
  const [type, setType] = useState<"all" | Raid["type"]>("all");
  const [showClosed, setShowClosed] = useState(false);
  const [cell, setCell] = useState<string | null>(null);
  const [editing, setEditing] = useState<Raid | "new" | null>(null);
  const today = todayIso();

  useEffect(() => {
    const hash = window.location.hash;
    if (hash.startsWith("#raid-") && raid.data) document.getElementById(hash.slice(1))?.scrollIntoView({ block: "center" });
  }, [raid.data]);

  const openRisks = useMemo(() => (raid.data ?? []).filter((r) => r.type === "risk" && OPEN.has(r.status)), [raid.data]);
  if (raid.isPending) return <Spinner label="Loading RAID log" />;
  if (raid.error) return <ErrorState error={raid.error} retry={() => raid.refetch()} />;

  const list = raid.data.filter(
    (r) =>
      (type === "all" || r.type === type) &&
      (showClosed || OPEN.has(r.status)) &&
      (!cell || (r.type === "risk" && `${r.probability}-${r.impact}` === cell)),
  );
  const counts = Object.fromEntries(TYPES.map((t) => [t, raid.data.filter((r) => r.type === t && OPEN.has(r.status)).length]));

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_300px]">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <div role="tablist" aria-label="RAID type" className="flex flex-wrap gap-1">
            {(["all", ...TYPES] as const).map((t) => (
              <button
                key={t}
                role="tab"
                aria-selected={type === t}
                type="button"
                onClick={() => setType(t)}
                className={cx(
                  "rounded-lg px-3 py-1.5 text-sm",
                  type === t ? "bg-accent-soft font-medium text-fg" : "text-muted hover:bg-surface-2",
                )}
              >
                {t === "all" ? "All" : t === "dependency" ? "Dependencies" : `${humanize(t)}s`}
                {t !== "all" && <span className="ml-1 text-[11px] text-faint">{counts[t]}</span>}
              </button>
            ))}
          </div>
          <label className="ml-2 flex items-center gap-2 text-sm text-muted">
            <input type="checkbox" checked={showClosed} onChange={(e) => setShowClosed(e.target.checked)} className="accent-[var(--accent)]" />
            Include closed
          </label>
          {cell && (
            <Button size="sm" variant="ghost" onClick={() => setCell(null)}>
              Clear heat-map filter
            </Button>
          )}
          {canWrite && (
            <Button className="ml-auto" variant="primary" onClick={() => setEditing("new")}>
              <Plus className="size-4" aria-hidden /> Log RAID item
            </Button>
          )}
        </div>

        {list.length === 0 ? (
          <EmptyState title="Nothing here">No {type === "all" ? "RAID items" : type === "dependency" ? "dependencies" : `${type}s`} match these filters.</EmptyState>
        ) : (
          <ul className="space-y-2">
            {list.map((r) => {
              const overdue = r.due_date && r.due_date < today && OPEN.has(r.status);
              return (
                <li key={r.id} id={`raid-${r.id}`} className="panel scroll-mt-24 p-4 target:ring-2 target:ring-accent">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11px] text-faint">{r.key}</span>
                    <Badge>{humanize(r.type)}</Badge>
                    {r.score !== null ? <Badge tone={scoreTone(r.score)}>Score {r.score} (P{r.probability}×I{r.impact})</Badge> : <Badge tone={r.priority === "critical" ? "bad" : r.priority === "high" ? "warn" : "neutral"}>{humanize(r.priority)} · impact {r.impact}</Badge>}
                    <Badge tone={OPEN.has(r.status) ? "accent" : "neutral"}>{humanize(r.status)}</Badge>
                    {r.due_date && <span className={cx("text-[11px]", overdue ? "font-semibold text-bad" : "text-faint")}>{overdue ? "Overdue review · " : "Review "}{fmtDate(r.due_date)}</span>}
                    <span className="ml-auto flex items-center gap-1.5 text-xs text-muted">
                      <MemberAvatar members={members} userId={r.owner_id} size={20} /> {memberName(members, r.owner_id)}
                    </span>
                  </div>
                  <h3 className="mt-2 font-medium">{r.title}</h3>
                  {r.description && <p className="mt-1 text-sm text-muted">{r.description}</p>}
                  <dl className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
                    {r.mitigation && (
                      <div>
                        <dt className="font-semibold text-faint">Mitigation</dt>
                        <dd className="text-muted">{r.mitigation}</dd>
                      </div>
                    )}
                    {r.contingency && (
                      <div>
                        <dt className="font-semibold text-faint">Contingency</dt>
                        <dd className="text-muted">{r.contingency}</dd>
                      </div>
                    )}
                    {r.escalation_trigger && (
                      <div>
                        <dt className="font-semibold text-faint">Escalate when</dt>
                        <dd className="text-muted">{r.escalation_trigger}</dd>
                      </div>
                    )}
                    {r.evidence && (
                      <div>
                        <dt className="font-semibold text-faint">Evidence</dt>
                        <dd className="text-muted">{r.evidence}</dd>
                      </div>
                    )}
                  </dl>
                  {canWrite && (
                    <div className="mt-3 flex justify-end">
                      <Button size="sm" variant="secondary" onClick={() => setEditing(r)}>
                        Edit
                      </Button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <aside className="space-y-4">
        <Panel title="Risk heat map">
          <HeatMap risks={openRisks} cell={cell} onCell={(c) => {
            setCell(c);
            if (c) setType("risk");
          }} />
          <p className="mt-3 text-[11px] text-faint">Open risks only. Click a cell to filter. Red cells (score ≥ 15) turn project health red.</p>
        </Panel>
      </aside>
      {editing && <RaidDialog item={editing === "new" ? null : editing} defaultType={type === "all" ? "risk" : type} onClose={() => setEditing(null)} />}
    </div>
  );
}
