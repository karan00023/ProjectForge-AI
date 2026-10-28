"use client";

import { Check, Plus, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { memberName } from "@/components/domain";
import { useProjectCtx } from "@/components/project/context";
import { useSession } from "@/components/shell/session";
import { Badge, Button, Dialog, EmptyState, ErrorState, Field, FormError, Input, Select, Spinner, Textarea } from "@/components/ui";
import type { Decision, DecisionCreate } from "@/lib/api";
import { fmtRelative, humanize } from "@/lib/format";
import { useCreateDecision, useDecisions, useUpdateDecision } from "@/lib/queries";

const TONE = { proposed: "warn", accepted: "ok", rejected: "bad", superseded: "neutral" } as const;

function DecisionDialog({ decisions, onClose }: { decisions: Decision[]; onClose: () => void }) {
  const { project } = useProjectCtx();
  const create = useCreateDecision(project.id);
  const [form, setForm] = useState<DecisionCreate>({ title: "", decision: "", status: "proposed", alternatives: [] });
  const [alts, setAlts] = useState([{ option: "", pros: "", cons: "" }]);
  const set = <K extends keyof DecisionCreate>(k: K, v: DecisionCreate[K]) => setForm((f) => ({ ...f, [k]: v }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    await create.mutateAsync({ ...form, alternatives: alts.filter((a) => a.option.trim()) });
    onClose();
  }

  return (
    <Dialog open onClose={onClose} title="Record a decision" wide>
      <form onSubmit={(e) => void submit(e).catch(() => undefined)} className="space-y-3">
        <Field label="Title">
          <Input required value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="e.g. Use log-based CDC for order data" />
        </Field>
        <Field label="Context" hint="What forced a decision? Constraints, deadlines, evidence.">
          <Textarea rows={2} value={form.context ?? ""} onChange={(e) => set("context", e.target.value || null)} />
        </Field>
        <Field label="Decision">
          <Textarea required rows={2} value={form.decision} onChange={(e) => set("decision", e.target.value)} />
        </Field>
        <Field label="Rationale">
          <Textarea rows={2} value={form.rationale ?? ""} onChange={(e) => set("rationale", e.target.value || null)} />
        </Field>
        <fieldset className="space-y-2">
          <legend className="text-xs font-medium text-muted">Alternatives considered</legend>
          {alts.map((a, i) => (
            <div key={i} className="grid gap-2 sm:grid-cols-3">
              <Input aria-label={`Alternative ${i + 1}`} placeholder="Option" value={a.option} onChange={(e) => setAlts(alts.map((x, j) => (j === i ? { ...x, option: e.target.value } : x)))} />
              <Input aria-label={`Alternative ${i + 1} pros`} placeholder="Pros" value={a.pros} onChange={(e) => setAlts(alts.map((x, j) => (j === i ? { ...x, pros: e.target.value } : x)))} />
              <Input aria-label={`Alternative ${i + 1} cons`} placeholder="Cons" value={a.cons} onChange={(e) => setAlts(alts.map((x, j) => (j === i ? { ...x, cons: e.target.value } : x)))} />
            </div>
          ))}
          <Button type="button" size="sm" variant="ghost" onClick={() => setAlts([...alts, { option: "", pros: "", cons: "" }])}>
            <Plus className="size-3.5" aria-hidden /> Add alternative
          </Button>
        </fieldset>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Status" hint="Accepting records you as the decision maker, now.">
            <Select value={form.status} onChange={(e) => set("status", e.target.value as Decision["status"])}>
              <option value="proposed">Proposed (needs approval)</option>
              <option value="accepted">Accepted</option>
            </Select>
          </Field>
          <Field label="Supersedes">
            <Select value={form.supersedes_id ?? ""} onChange={(e) => set("supersedes_id", e.target.value || null)}>
              <option value="">Nothing</option>
              {decisions
                .filter((d) => d.status === "accepted")
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.key} {d.title}
                  </option>
                ))}
            </Select>
          </Field>
        </div>
        <Field label="Impact">
          <Textarea rows={2} value={form.impact ?? ""} onChange={(e) => set("impact", e.target.value || null)} />
        </Field>
        <FormError error={create.error} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={create.isPending}>
            Record decision
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export default function DecisionsPage() {
  const { project, members } = useProjectCtx();
  const { canWrite } = useSession();
  const decisions = useDecisions(project.id);
  const update = useUpdateDecision(project.id);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const hash = window.location.hash;
    if (hash.startsWith("#dec-") && decisions.data) document.getElementById(hash.slice(1))?.scrollIntoView({ block: "center" });
  }, [decisions.data]);

  if (decisions.isPending) return <Spinner label="Loading decision log" />;
  if (decisions.error) return <ErrorState error={decisions.error} retry={() => decisions.refetch()} />;
  const byId = Object.fromEntries(decisions.data.map((d) => [d.id, d]));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted">An explicit record of what was decided, when, why, and by whom.</p>
        {canWrite && (
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus className="size-4" aria-hidden /> Record decision
          </Button>
        )}
      </div>
      <FormError error={update.error} />
      {decisions.data.length === 0 ? (
        <EmptyState title="No decisions recorded">Decisions logged here can be cited by reports and agents later.</EmptyState>
      ) : (
        <ol className="space-y-3">
          {decisions.data.map((d) => (
            <li key={d.id} id={`dec-${d.id}`} className="panel scroll-mt-24 p-4 target:ring-2 target:ring-accent">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-[11px] text-faint">{d.key}</span>
                <Badge tone={TONE[d.status]}>{humanize(d.status)}</Badge>
                {d.supersedes_id && byId[d.supersedes_id] && <Badge>Supersedes {byId[d.supersedes_id]!.key}</Badge>}
                <span className="ml-auto text-[11px] text-faint">
                  {d.decided_at
                    ? `${humanize(d.status)} by ${memberName(members, d.decided_by_id)} ${fmtRelative(d.decided_at)}`
                    : `Proposed ${fmtRelative(d.created_at)}`}
                </span>
              </div>
              <h3 className="mt-2 font-medium">{d.title}</h3>
              <dl className="mt-2 space-y-2 text-sm">
                {d.context && (
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wider text-faint">Context</dt>
                    <dd className="text-muted">{d.context}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-[11px] font-semibold uppercase tracking-wider text-faint">Decision</dt>
                  <dd>{d.decision}</dd>
                </div>
                {d.rationale && (
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wider text-faint">Rationale</dt>
                    <dd className="text-muted">{d.rationale}</dd>
                  </div>
                )}
                {d.alternatives.length > 0 && (
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wider text-faint">Alternatives considered</dt>
                    <dd>
                      <ul className="mt-1 space-y-1">
                        {d.alternatives.map((a, i) => (
                          <li key={i} className="rounded-md border border-line bg-surface-2 px-2 py-1 text-xs">
                            <strong>{String(a.option)}</strong>
                            {a.pros ? <span className="text-ok"> + {String(a.pros)}</span> : null}
                            {a.cons ? <span className="text-bad"> − {String(a.cons)}</span> : null}
                          </li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                )}
                {d.impact && (
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wider text-faint">Impact</dt>
                    <dd className="text-muted">{d.impact}</dd>
                  </div>
                )}
              </dl>
              {canWrite && d.status === "proposed" && (
                <div className="mt-3 flex justify-end gap-2">
                  <Button size="sm" variant="danger" onClick={() => update.mutate({ id: d.id, status: "rejected" })}>
                    <X className="size-3.5" aria-hidden /> Reject
                  </Button>
                  <Button size="sm" variant="primary" onClick={() => update.mutate({ id: d.id, status: "accepted" })}>
                    <Check className="size-3.5" aria-hidden /> Accept
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      {creating && <DecisionDialog decisions={decisions.data} onClose={() => setCreating(false)} />}
    </div>
  );
}
