"use client";

import { useState, type FormEvent } from "react";
import { Button, Dialog, Field, FormError, Input, Select, Textarea } from "@/components/ui";
import type { WorkItemCreate, WorkItemStatus, WorkItemType } from "@/lib/api";
import { PRIORITY_ORDER, STATUS_LABEL, STATUS_ORDER, TYPE_LABEL, TYPE_LEVEL, humanize } from "@/lib/format";
import { useCreateItem } from "@/lib/queries";
import { useProjectCtx } from "./context";

export function NewItemDialog({
  open,
  onClose,
  defaults,
}: {
  open: boolean;
  onClose: () => void;
  defaults?: Partial<Pick<WorkItemCreate, "status" | "type" | "parent_id" | "sprint_id">>;
}) {
  const { project, members, items, sprints, milestones } = useProjectCtx();
  const create = useCreateItem(project.id);
  const [type, setType] = useState<WorkItemType>(defaults?.type ?? "story");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<WorkItemStatus>(defaults?.status ?? "backlog");
  const [priority, setPriority] = useState<WorkItemCreate["priority"]>("medium");
  const [points, setPoints] = useState("");
  const [assignee, setAssignee] = useState("");
  const [parent, setParent] = useState(defaults?.parent_id ?? "");
  const [sprint, setSprint] = useState(defaults?.sprint_id ?? "");
  const [milestone, setMilestone] = useState("");
  const [due, setDue] = useState("");

  const parents = (items ?? []).filter((w) => TYPE_LEVEL[w.type] < TYPE_LEVEL[type] && w.status !== "cancelled");

  async function submit(e: FormEvent) {
    e.preventDefault();
    await create.mutateAsync({
      type,
      title,
      description: description || null,
      status,
      priority,
      story_points: points === "" ? null : Number(points),
      assignee_id: assignee || null,
      parent_id: parent || null,
      sprint_id: sprint || null,
      milestone_id: milestone || null,
      due_date: due || null,
    });
    setTitle("");
    setDescription("");
    onClose();
  }

  return (
    <Dialog open={open} onClose={onClose} title={`New work item in ${project.key}`} wide>
      <form onSubmit={(e) => void submit(e).catch(() => undefined)} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-[10rem_1fr]">
          <Field label="Type">
            <Select value={type} onChange={(e) => setType(e.target.value as WorkItemType)}>
              {Object.entries(TYPE_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Title">
            <Input required autoFocus value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} />
          </Field>
        </div>
        <Field label="Description">
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Status">
            <Select value={status} onChange={(e) => setStatus(e.target.value as WorkItemStatus)}>
              {STATUS_ORDER.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Priority">
            <Select value={priority} onChange={(e) => setPriority(e.target.value as WorkItemCreate["priority"])}>
              {PRIORITY_ORDER.map((p) => (
                <option key={p} value={p}>
                  {humanize(p)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Story points">
            <Input type="number" min={0} max={100} value={points} onChange={(e) => setPoints(e.target.value)} />
          </Field>
          <Field label="Assignee">
            <Select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.user.id} value={m.user.id}>
                  {m.user.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Parent">
            <Select value={parent} onChange={(e) => setParent(e.target.value)}>
              <option value="">None</option>
              {parents.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.key} {w.title}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Due date">
            <Input type="date" value={due} onChange={(e) => setDue(e.target.value)} />
          </Field>
          <Field label="Sprint">
            <Select value={sprint} onChange={(e) => setSprint(e.target.value)}>
              <option value="">No sprint</option>
              {sprints
                ?.filter((s) => s.status !== "closed")
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field label="Milestone">
            <Select value={milestone} onChange={(e) => setMilestone(e.target.value)}>
              <option value="">None</option>
              {milestones
                ?.filter((m) => m.status === "open")
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
            </Select>
          </Field>
        </div>
        <FormError error={create.error} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={create.isPending}>
            Create
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
