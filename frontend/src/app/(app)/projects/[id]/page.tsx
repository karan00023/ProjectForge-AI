"use client";

import { Pencil } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { ActivityList } from "@/components/activity-list";
import { HealthExplanation, MemberAvatar, memberName, ProgressSummary } from "@/components/domain";
import { useProjectCtx } from "@/components/project/context";
import { useSession } from "@/components/shell/session";
import { Badge, Button, cx, Dialog, Field, FormError, Input, Meter, Panel, Select, Spinner, Textarea } from "@/components/ui";
import type { ProjectUpdate } from "@/lib/api";
import { fmtDate, humanize } from "@/lib/format";
import { useActivity, useRaid, useUpdateProject } from "@/lib/queries";

const PHASES = ["idea", "discovery", "business_case", "planning", "requirements", "engineering", "testing", "release", "monitoring", "closure"] as const;

function EditProjectDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { project, members } = useProjectCtx();
  const update = useUpdateProject(project.id);
  const [form, setForm] = useState<ProjectUpdate>({
    name: project.name,
    description: project.description,
    status: project.status,
    phase: project.phase,
    methodology: project.methodology,
    start_date: project.start_date,
    target_date: project.target_date,
    owner_id: project.owner_id,
  });
  const [wipProgress, setWipProgress] = useState(String(project.wip_limits.in_progress ?? ""));
  const [wipReview, setWipReview] = useState(String(project.wip_limits.in_review ?? ""));
  const set = <K extends keyof ProjectUpdate>(k: K, v: ProjectUpdate[K]) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const wip: Record<string, number> = {};
    if (wipProgress) wip.in_progress = Number(wipProgress);
    if (wipReview) wip.in_review = Number(wipReview);
    await update.mutateAsync({ ...form, wip_limits: wip });
    onClose();
  }

  return (
    <Dialog open={open} onClose={onClose} title={`Edit ${project.key}`} wide>
      <form onSubmit={(e) => void submit(e).catch(() => undefined)} className="space-y-3">
        <Field label="Name">
          <Input required value={form.name ?? ""} onChange={(e) => set("name", e.target.value)} />
        </Field>
        <Field label="Description">
          <Textarea rows={4} value={form.description ?? ""} onChange={(e) => set("description", e.target.value || null)} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Status">
            <Select value={form.status ?? "active"} onChange={(e) => set("status", e.target.value as ProjectUpdate["status"])}>
              {["proposed", "active", "on_hold", "completed", "cancelled"].map((s) => (
                <option key={s} value={s}>
                  {humanize(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Lifecycle phase">
            <Select value={form.phase ?? "planning"} onChange={(e) => set("phase", e.target.value as ProjectUpdate["phase"])}>
              {PHASES.map((s) => (
                <option key={s} value={s}>
                  {humanize(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Delivery method">
            <Select value={form.methodology ?? "scrum"} onChange={(e) => set("methodology", e.target.value as ProjectUpdate["methodology"])}>
              {["scrum", "kanban", "waterfall", "hybrid"].map((s) => (
                <option key={s} value={s}>
                  {humanize(s)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Start">
            <Input type="date" value={form.start_date ?? ""} onChange={(e) => set("start_date", e.target.value || null)} />
          </Field>
          <Field label="Target">
            <Input type="date" value={form.target_date ?? ""} onChange={(e) => set("target_date", e.target.value || null)} />
          </Field>
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
          <Field label="WIP limit: In progress" hint="Board warns above this">
            <Input type="number" min={1} max={99} value={wipProgress} onChange={(e) => setWipProgress(e.target.value)} />
          </Field>
          <Field label="WIP limit: Review">
            <Input type="number" min={1} max={99} value={wipReview} onChange={(e) => setWipReview(e.target.value)} />
          </Field>
        </div>
        <FormError error={update.error} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={update.isPending}>
            Save changes
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export default function ProjectOverview() {
  const { project, members, sprints, milestones } = useProjectCtx();
  const { canWrite } = useSession();
  const raid = useRaid(project.id);
  const activity = useActivity(project.id, 12);
  const [editing, setEditing] = useState(false);
  const activeSprint = sprints?.find((s) => s.status === "active");
  const openRisks = (raid.data ?? []).filter((r) => ["open", "in_progress", "monitoring"].includes(r.status)).slice(0, 5);

  return (
    <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
      <div className="space-y-4">
        <Panel
          title="Health — why this status"
          action={<span className="text-[11px] text-faint">Rules {project.health.rules_version}</span>}
        >
          <HealthExplanation projectId={project.id} health={project.health} />
        </Panel>

        <Panel title="Milestones" action={<Link href={`/projects/${project.id}/timeline`} className="text-xs text-accent-ink hover:underline">Timeline</Link>} bodyClassName="p-2">
          {!milestones ? (
            <Spinner />
          ) : milestones.length === 0 ? (
            <p className="p-3 text-sm text-muted">No milestones yet.</p>
          ) : (
            <ul className="divide-y divide-line">
              {milestones.map((m) => (
                <li key={m.id} className="flex flex-wrap items-center gap-3 p-2.5 text-sm">
                  <span className="min-w-0 flex-1">
                    <span className="font-medium">{m.name}</span>
                    <span className="block text-[11px] text-muted">
                      Baseline {fmtDate(m.baseline_date)} · {m.status === "completed" ? `done ${fmtDate(m.actual_date)}` : `forecast ${fmtDate(m.planned_date)}`} · {memberName(members, m.owner_id)}
                    </span>
                  </span>
                  <span className="text-[11px] tabular-nums text-muted">
                    {m.deliverables_done}/{m.deliverables_total} deliverables
                  </span>
                  {m.overdue ? (
                    <Badge tone="bad">Overdue</Badge>
                  ) : m.variance_working_days > 0 ? (
                    <Badge tone={m.variance_working_days > 10 ? "bad" : m.variance_working_days > 5 ? "warn" : "neutral"}>
                      +{m.variance_working_days} wd vs baseline
                    </Badge>
                  ) : m.status === "completed" ? (
                    <Badge tone="ok">Completed</Badge>
                  ) : (
                    <Badge tone="ok">On baseline</Badge>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Recent activity" bodyClassName="p-2">
          {activity.data ? <ActivityList events={activity.data} compact /> : <Spinner />}
        </Panel>
      </div>

      <div className="space-y-4">
        <Panel
          title="About"
          action={
            canWrite && (
              <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
                <Pencil className="size-3.5" aria-hidden /> Edit
              </Button>
            )
          }
        >
          <p className="whitespace-pre-line text-sm text-muted">{project.description || "No description."}</p>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div>
              <dt className="text-faint">Owner</dt>
              <dd className="mt-1 flex items-center gap-1.5">
                <MemberAvatar members={members} userId={project.owner_id} size={20} /> {memberName(members, project.owner_id)}
              </dd>
            </div>
            <div>
              <dt className="text-faint">WIP limits</dt>
              <dd className="mt-1">
                {Object.keys(project.wip_limits).length
                  ? Object.entries(project.wip_limits).map(([k, v]) => `${humanize(k)} ≤ ${v}`).join(", ")
                  : "None"}
              </dd>
            </div>
          </dl>
          <div className="mt-4">
            <ProgressSummary health={project.health} />
          </div>
        </Panel>

        <Panel title="Current sprint">
          {!sprints ? (
            <Spinner />
          ) : !activeSprint ? (
            <p className="text-sm text-muted">No active sprint.</p>
          ) : (
            <div className="space-y-2 text-sm">
              <p className="font-medium">{activeSprint.name}</p>
              {activeSprint.goal && <p className="text-xs text-muted">Goal: {activeSprint.goal}</p>}
              <p className="text-xs text-muted">
                {fmtDate(activeSprint.start_date)} → {fmtDate(activeSprint.end_date)}
              </p>
              <div className="flex justify-between text-xs">
                <span className="text-muted">Done / committed</span>
                <span className="tabular-nums">
                  {activeSprint.done_points}/{activeSprint.committed_points} pts
                </span>
              </div>
              <Meter value={activeSprint.done_points} max={activeSprint.committed_points} tone="ok" label="Sprint points done" />
              {activeSprint.capacity_points !== null && (
                <p className={cx("text-xs", activeSprint.committed_points > activeSprint.capacity_points ? "text-warn" : "text-muted")}>
                  Committed {activeSprint.committed_points} of {activeSprint.capacity_points} pts capacity
                  {activeSprint.committed_points > activeSprint.capacity_points && " — over capacity"}
                </p>
              )}
              <Link href={`/projects/${project.id}/board`} className="text-xs text-accent-ink hover:underline">
                Open board
              </Link>
            </div>
          )}
        </Panel>

        <Panel title="Open risks & issues" action={<Link href={`/projects/${project.id}/raid`} className="text-xs text-accent-ink hover:underline">RAID</Link>} bodyClassName="p-2">
          {!raid.data ? (
            <Spinner />
          ) : openRisks.length === 0 ? (
            <p className="p-3 text-sm text-muted">Nothing open.</p>
          ) : (
            <ul className="divide-y divide-line">
              {openRisks.map((r) => (
                <li key={r.id}>
                  <Link href={`/projects/${project.id}/raid#raid-${r.id}`} className="block rounded-lg p-2.5 hover:bg-surface-2">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[11px] text-faint">{r.key}</span>
                      <Badge>{humanize(r.type)}</Badge>
                      {r.score !== null && <Badge tone={r.score >= 15 ? "bad" : r.score >= 10 ? "warn" : "neutral"}>{r.score}</Badge>}
                    </div>
                    <p className="mt-1 text-sm">{r.title}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
      {canWrite && editing && <EditProjectDialog open={editing} onClose={() => setEditing(false)} />}
    </div>
  );
}
