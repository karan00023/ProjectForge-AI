"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { HealthBadge, MemberAvatar, ProgressSummary } from "@/components/domain";
import { useSession } from "@/components/shell/session";
import { Button, Dialog, EmptyState, ErrorState, Field, FormError, Input, Select, Spinner, Textarea } from "@/components/ui";
import type { ProjectCreate } from "@/lib/api";
import { fmtDate, humanize } from "@/lib/format";
import { useCreateProject, useMembers, useProjects, useTemplates } from "@/lib/queries";

function suggestKey(name: string): string {
  const words = name.toUpperCase().replace(/[^A-Z0-9 ]/g, "").split(/\s+/).filter(Boolean);
  const key = words.length > 1 ? words.map((w) => w[0]).join("") : (words[0] ?? "");
  return key.slice(0, 6);
}

function CreateProjectDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const templates = useTemplates();
  const create = useCreateProject();
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [keyTouched, setKeyTouched] = useState(false);
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState("");
  const [methodology, setMethodology] = useState<ProjectCreate["methodology"]>("scrum");
  const [kind, setKind] = useState<ProjectCreate["kind"]>("general");
  const [start, setStart] = useState("");
  const [target, setTarget] = useState("");
  const chosen = templates.data?.find((t) => t.id === template);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const project = await create.mutateAsync({
      name,
      key,
      description: description || null,
      template: template || null,
      methodology: chosen?.methodology ?? methodology,
      kind: chosen?.kind ?? kind,
      start_date: start || null,
      target_date: target || null,
    });
    // Navigate away directly; closing first would let the page's close handler rewrite the URL.
    router.push(`/projects/${project.id}`);
  }

  return (
    <Dialog open={open} onClose={onClose} title="Create project" wide>
      <form onSubmit={(e) => void submit(e).catch(() => undefined)} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_8rem]">
          <Field label="Name">
            <Input
              required
              autoFocus
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (!keyTouched) setKey(suggestKey(e.target.value));
              }}
              placeholder="e.g. Billing platform modernization"
            />
          </Field>
          <Field label="Key" hint="2–8 letters/digits">
            <Input
              required
              value={key}
              pattern="[A-Za-z][A-Za-z0-9]{1,7}"
              onChange={(e) => {
                setKeyTouched(true);
                setKey(e.target.value.toUpperCase());
              }}
              className="font-mono uppercase"
            />
          </Field>
        </div>
        <Field label="Description">
          <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Problem, outcome, scope." />
        </Field>
        <Field label="Start from" hint={chosen ? chosen.description : "An empty project, or a template with standard epics and milestones."}>
          <Select value={template} onChange={(e) => setTemplate(e.target.value)}>
            <option value="">Blank project</option>
            {templates.data?.map((t) => (
              <option key={t.id} value={t.id}>
                Template: {t.name}
              </option>
            ))}
          </Select>
        </Field>
        {chosen && (
          <div className="grid gap-3 rounded-lg border border-line bg-surface-2 p-3 text-xs sm:grid-cols-2">
            <div>
              <p className="mb-1 font-semibold text-muted">Epics created</p>
              <ul className="list-inside list-disc space-y-0.5">
                {chosen.epics.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mb-1 font-semibold text-muted">Milestones (baselined from start date)</p>
              <ul className="list-inside list-disc space-y-0.5">
                {chosen.milestones.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
        {!chosen && (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Delivery method">
              <Select value={methodology} onChange={(e) => setMethodology(e.target.value as ProjectCreate["methodology"])}>
                {["scrum", "kanban", "waterfall", "hybrid"].map((m) => (
                  <option key={m} value={m}>
                    {humanize(m)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Project type">
              <Select value={kind} onChange={(e) => setKind(e.target.value as ProjectCreate["kind"])}>
                <option value="general">General</option>
                <option value="software">Software delivery</option>
                <option value="data_platform">Data platform</option>
                <option value="ai_product">AI product</option>
              </Select>
            </Field>
          </div>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Start date">
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </Field>
          <Field label="Target date">
            <Input type="date" value={target} min={start || undefined} onChange={(e) => setTarget(e.target.value)} />
          </Field>
        </div>
        <FormError error={create.error} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={create.isPending}>
            Create project
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export default function ProjectsPage() {
  const params = useSearchParams();
  const router = useRouter();
  const { canWrite } = useSession();
  const projects = useProjects();
  const members = useMembers();
  const [open, setOpen] = useState(params.get("new") === "1");

  const close = () => {
    setOpen(false);
    if (params.get("new")) router.replace("/projects");
  };

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted">Health is re-evaluated from records on every view.</p>
        </div>
        {canWrite && (
          <Button variant="primary" onClick={() => setOpen(true)}>
            <Plus className="size-4" aria-hidden /> New project
          </Button>
        )}
      </header>
      {projects.isPending ? (
        <Spinner />
      ) : projects.error ? (
        <ErrorState error={projects.error} retry={() => projects.refetch()} />
      ) : projects.data.length === 0 ? (
        <EmptyState title="No projects in this organization yet">
          {canWrite ? "Create one manually or from a template." : "Ask an organization member to create one."}
        </EmptyState>
      ) : (
        <div className="panel overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="border-b border-line text-left text-[11px] uppercase tracking-wider text-faint">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Project</th>
                <th className="px-4 py-2.5 font-semibold">Health</th>
                <th className="px-4 py-2.5 font-semibold">Phase</th>
                <th className="px-4 py-2.5 font-semibold">Owner</th>
                <th className="px-4 py-2.5 font-semibold">Target</th>
                <th className="w-64 px-4 py-2.5 font-semibold">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {projects.data.map((p) => (
                <tr key={p.id} className="hover:bg-surface-2/60">
                  <td className="px-4 py-3">
                    <Link href={`/projects/${p.id}`} className="group block">
                      <span className="font-mono text-[11px] text-faint">{p.key}</span>
                      <span className="block font-medium group-hover:text-accent-ink">{p.name}</span>
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <HealthBadge level={p.health.level} />
                    <span className="mt-1 block text-[11px] text-faint">
                      {p.health.signals.length} rule{p.health.signals.length === 1 ? "" : "s"} fired
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {humanize(p.phase)}
                    <span className="block text-[11px] text-faint">
                      {humanize(p.methodology)} · {humanize(p.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <MemberAvatar members={members.data} userId={p.owner_id} />
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted">{fmtDate(p.target_date)}</td>
                  <td className="px-4 py-3">
                    <ProgressSummary health={p.health} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {canWrite && <CreateProjectDialog open={open} onClose={close} />}
    </div>
  );
}
