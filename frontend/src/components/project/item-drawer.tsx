"use client";

import { Link2, Plus, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { MemberAvatar, StatusBadge, TypeIcon } from "@/components/domain";
import { useSession } from "@/components/shell/session";
import { Badge, Button, cx, ErrorState, Field, FormError, Input, Select, Spinner, Textarea } from "@/components/ui";
import type { WorkItemDetail, WorkItemUpdate } from "@/lib/api";
import { fmtDate, fmtRelative, humanize, PRIORITY_ORDER, STATUS_LABEL, STATUS_ORDER, TYPE_LABEL, TYPE_LEVEL } from "@/lib/format";
import { useCreateLink, useDeleteItem, useDeleteLink, useUpdateItem, useWorkItem } from "@/lib/queries";
import { useProjectCtx } from "./context";

export function ItemDrawer() {
  const { openItemId, openItem } = useProjectCtx();
  const detail = useWorkItem(openItemId);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!openItemId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !(e.target as HTMLElement)?.closest("dialog")) openItem(null);
    };
    window.addEventListener("keydown", onKey);
    panelRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [openItemId, openItem]);

  if (!openItemId) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="presentation">
      <button type="button" aria-label="Close work item" className="absolute inset-0 bg-black/40" onClick={() => openItem(null)} />
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label="Work item details"
        className="relative flex h-full w-full max-w-xl flex-col border-l border-line bg-surface shadow-2xl outline-none"
      >
        {detail.isPending ? (
          <Spinner />
        ) : detail.error ? (
          <div className="p-5">
            <ErrorState error={detail.error} />
          </div>
        ) : (
          <ItemDetail key={detail.data.id + detail.data.updated_at} item={detail.data} onClose={() => openItem(null)} />
        )}
      </div>
    </div>
  );
}

function ItemDetail({ item, onClose }: { item: WorkItemDetail; onClose: () => void }) {
  const { project, members, items, sprints, milestones, openItem } = useProjectCtx();
  const { canWrite } = useSession();
  const update = useUpdateItem(project.id);
  const del = useDeleteItem(project.id);
  const addLink = useCreateLink(project.id);
  const removeLink = useDeleteLink(project.id);
  const [title, setTitle] = useState(item.title);
  const [description, setDescription] = useState(item.description ?? "");
  const [newAc, setNewAc] = useState("");
  const [linkTarget, setLinkTarget] = useState("");
  const [linkDir, setLinkDir] = useState<"blocks" | "blocked_by">("blocked_by");

  const save = (body: WorkItemUpdate) => update.mutate({ id: item.id, ...body });
  const ro = !canWrite;
  const parents = (items ?? []).filter((w) => w.id !== item.id && TYPE_LEVEL[w.type] < TYPE_LEVEL[item.type]);
  const linkable = (items ?? []).filter((w) => w.id !== item.id && !item.links.some((l) => l.item.id === w.id));

  async function submitLink() {
    if (!linkTarget) return;
    const [sourceId, targetId] = linkDir === "blocks" ? [item.id, linkTarget] : [linkTarget, item.id];
    await addLink.mutateAsync({ sourceId, targetId, type: "blocks" });
    setLinkTarget("");
  }

  return (
    <>
      <header className="flex items-start gap-3 border-b border-line px-5 py-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs text-muted">
            <TypeIcon type={item.type} />
            <span className="font-mono">{item.key}</span>
            <StatusBadge status={item.status} />
          </div>
          {ro ? (
            <h2 className="mt-1 text-lg font-semibold">{item.title}</h2>
          ) : (
            <input
              aria-label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onBlur={() => title.trim() && title !== item.title && save({ title })}
              className="mt-1 w-full rounded bg-transparent text-lg font-semibold outline-none focus:ring-2 focus:ring-accent/30"
            />
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
          <X className="size-4" />
        </Button>
      </header>

      <div className="scrollbar-thin flex-1 space-y-5 overflow-y-auto px-5 py-4">
        <FormError error={update.error ?? addLink.error ?? del.error} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Status">
            <Select disabled={ro} value={item.status} onChange={(e) => save({ status: e.target.value as WorkItemDetail["status"] })}>
              {STATUS_ORDER.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Priority">
            <Select disabled={ro} value={item.priority} onChange={(e) => save({ priority: e.target.value as WorkItemDetail["priority"] })}>
              {PRIORITY_ORDER.map((p) => (
                <option key={p} value={p}>
                  {humanize(p)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Type">
            <Select disabled={ro} value={item.type} onChange={(e) => save({ type: e.target.value as WorkItemDetail["type"] })}>
              {Object.entries(TYPE_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Assignee">
            <Select disabled={ro} value={item.assignee_id ?? ""} onChange={(e) => save({ assignee_id: e.target.value || null })}>
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.user.id} value={m.user.id}>
                  {m.user.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Story points">
            <Input
              disabled={ro}
              type="number"
              min={0}
              max={100}
              defaultValue={item.story_points ?? ""}
              onBlur={(e) => {
                const v = e.target.value === "" ? null : Number(e.target.value);
                if (v !== item.story_points) save({ story_points: v });
              }}
            />
          </Field>
          <Field label="Parent">
            <Select disabled={ro} value={item.parent_id ?? ""} onChange={(e) => save({ parent_id: e.target.value || null })}>
              <option value="">None</option>
              {parents.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.key} {w.title}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Sprint">
            <Select disabled={ro} value={item.sprint_id ?? ""} onChange={(e) => save({ sprint_id: e.target.value || null })}>
              <option value="">No sprint</option>
              {sprints?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({humanize(s.status)})
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Milestone">
            <Select disabled={ro} value={item.milestone_id ?? ""} onChange={(e) => save({ milestone_id: e.target.value || null })}>
              <option value="">None</option>
              {milestones?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Start">
            <Input disabled={ro} type="date" defaultValue={item.start_date ?? ""} onBlur={(e) => e.target.value !== (item.start_date ?? "") && save({ start_date: e.target.value || null })} />
          </Field>
          <Field label="Due">
            <Input disabled={ro} type="date" defaultValue={item.due_date ?? ""} onBlur={(e) => e.target.value !== (item.due_date ?? "") && save({ due_date: e.target.value || null })} />
          </Field>
        </div>

        <Field label="Description">
          <Textarea
            readOnly={ro}
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            onBlur={() => description !== (item.description ?? "") && save({ description: description || null })}
          />
        </Field>

        <section aria-labelledby="ac-h">
          <h3 id="ac-h" className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
            Acceptance criteria ({item.acceptance_criteria.length})
          </h3>
          {item.acceptance_criteria.length === 0 && <p className="text-xs text-faint">None yet. Stories without acceptance criteria are not ready.</p>}
          <ul className="space-y-1.5">
            {item.acceptance_criteria.map((c) => (
              <li key={String(c.id)} className="group flex gap-2 rounded-lg border border-line bg-surface-2 p-2 text-sm">
                {c.format === "gherkin" && <Badge tone="info">GWT</Badge>}
                <span className="flex-1">{String(c.text)}</span>
                {!ro && (
                  <button
                    type="button"
                    aria-label="Remove criterion"
                    className="text-faint opacity-0 hover:text-bad group-hover:opacity-100 focus:opacity-100"
                    onClick={() =>
                      save({
                        acceptance_criteria: item.acceptance_criteria
                          .filter((x) => x.id !== c.id)
                          .map((x) => ({ id: String(x.id), text: String(x.text), format: x.format === "gherkin" ? "gherkin" : "plain" })),
                      })
                    }
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                )}
              </li>
            ))}
          </ul>
          {!ro && (
            <form
              className="mt-2 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                const text = newAc.trim();
                if (!text) return;
                save({
                  acceptance_criteria: [
                    ...item.acceptance_criteria.map((x) => ({ id: String(x.id), text: String(x.text), format: x.format === "gherkin" ? ("gherkin" as const) : ("plain" as const) })),
                    { text, format: /^given\b/i.test(text) ? "gherkin" : "plain" },
                  ],
                });
                setNewAc("");
              }}
            >
              <Input value={newAc} onChange={(e) => setNewAc(e.target.value)} placeholder="Given … when … then …" aria-label="New acceptance criterion" />
              <Button type="submit" size="md" aria-label="Add criterion">
                <Plus className="size-4" />
              </Button>
            </form>
          )}
        </section>

        <section aria-labelledby="dep-h">
          <h3 id="dep-h" className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
            Dependencies & links
          </h3>
          {item.links.length === 0 && <p className="text-xs text-faint">No dependencies.</p>}
          <ul className="space-y-1.5">
            {item.links.map((l) => (
              <li key={l.link_id} className="flex items-center gap-2 rounded-lg border border-line bg-surface-2 p-2 text-sm">
                <Badge tone={l.type === "blocks" ? (l.direction === "incoming" ? "warn" : "accent") : "neutral"}>
                  {l.type === "blocks" ? (l.direction === "incoming" ? "Blocked by" : "Blocks") : humanize(l.type)}
                </Badge>
                <button type="button" className="min-w-0 flex-1 truncate text-left hover:text-accent-ink" onClick={() => openItem(l.item.id)}>
                  <span className="font-mono text-[11px] text-faint">{l.item.key}</span> {l.item.title}
                </button>
                <StatusBadge status={l.item.status} />
                {!ro && (
                  <button type="button" aria-label={`Remove link to ${l.item.key}`} className="text-faint hover:text-bad" onClick={() => removeLink.mutate(l.link_id)}>
                    <X className="size-3.5" />
                  </button>
                )}
              </li>
            ))}
          </ul>
          {!ro && (
            <div className="mt-2 flex flex-wrap gap-2">
              <Select value={linkDir} onChange={(e) => setLinkDir(e.target.value as "blocks" | "blocked_by")} className="w-32" aria-label="Link direction">
                <option value="blocked_by">Blocked by</option>
                <option value="blocks">Blocks</option>
              </Select>
              <Select value={linkTarget} onChange={(e) => setLinkTarget(e.target.value)} className="min-w-0 flex-1" aria-label="Linked item">
                <option value="">Choose an item…</option>
                {linkable.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.key} {w.title}
                  </option>
                ))}
              </Select>
              <Button onClick={() => void submitLink().catch(() => undefined)} disabled={!linkTarget} loading={addLink.isPending}>
                <Link2 className="size-4" aria-hidden /> Link
              </Button>
            </div>
          )}
        </section>

        {item.children.length > 0 && (
          <section aria-labelledby="child-h">
            <h3 id="child-h" className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
              Children ({item.children.length})
            </h3>
            <ul className="space-y-1">
              {item.children.map((c) => (
                <li key={c.id}>
                  <button type="button" onClick={() => openItem(c.id)} className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-surface-2">
                    <TypeIcon type={c.type} />
                    <span className="font-mono text-[11px] text-faint">{c.key}</span>
                    <span className="min-w-0 flex-1 truncate">{c.title}</span>
                    <MemberAvatar members={members} userId={c.assignee_id} size={20} />
                    <StatusBadge status={c.status} />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section aria-labelledby="hist-h">
          <h3 id="hist-h" className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
            History
          </h3>
          <ol className="space-y-2 border-l border-line pl-3">
            {item.history.map((h) => (
              <li key={h.id} className="text-xs">
                <span className="font-medium">{h.actor_label}</span> <span className="text-muted">{h.summary}</span>
                <span className="block text-[11px] text-faint">{fmtRelative(h.created_at)}</span>
              </li>
            ))}
          </ol>
        </section>
        <p className="text-[11px] text-faint">
          Created {fmtDate(item.created_at.slice(0, 10), true)}
          {item.completed_at && ` · completed ${fmtDate(item.completed_at.slice(0, 10), true)}`}
        </p>
      </div>

      {canWrite && (
        <footer className="flex justify-end border-t border-line px-5 py-3">
          <Button
            variant="danger"
            size="sm"
            loading={del.isPending}
            onClick={() => {
              if (window.confirm(`Delete ${item.key}? Children move up to its parent. This is recorded in the audit log.`)) {
                del.mutate(item.id, { onSuccess: onClose });
              }
            }}
          >
            <Trash2 className={cx("size-3.5")} aria-hidden /> Delete
          </Button>
        </footer>
      )}
    </>
  );
}
