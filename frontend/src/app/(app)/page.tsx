"use client";

import { AlertTriangle, CalendarClock, ChevronDown, Gavel, Info, OctagonX, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ActivityList } from "@/components/activity-list";
import { HealthBadge, HealthExplanation, PriorityIcon, ProgressSummary, TypeIcon } from "@/components/domain";
import { useSession } from "@/components/shell/session";
import { Badge, cx, EmptyState, ErrorState, Panel, Spinner } from "@/components/ui";
import type { Kpi, ProjectSummary } from "@/lib/api";
import { fmtDate, fmtRelative, humanize } from "@/lib/format";
import { useDashboard } from "@/lib/queries";

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

function KpiTile({ kpi }: { kpi: Kpi }) {
  const accent: Record<string, string> = {
    active_projects: "from-accent/70",
    projects_red: "from-bad/70",
    completed_14d: "from-accent-2/70",
    milestone_on_time: "from-accent-3/70",
    critical_raid: "from-warn/70",
  };
  return (
    <div className="panel relative overflow-hidden p-4">
      <div className={cx("absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r to-transparent", accent[kpi.id] ?? "from-accent/70")} />
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">{kpi.label}</p>
        <span title={kpi.definition} className="text-faint">
          <Info className="size-3.5" aria-hidden />
          <span className="sr-only">Definition: {kpi.definition}</span>
        </span>
      </div>
      <p className="mt-2 text-3xl font-semibold tabular-nums">{kpi.display}</p>
      {kpi.denominator !== null && kpi.denominator !== undefined && (
        <p className="mt-1 text-[11px] text-faint">
          {kpi.numerator} of {kpi.denominator}
          {kpi.id === "milestone_on_time" ? " completed milestones" : " projects"}
        </p>
      )}
    </div>
  );
}

function ProjectHealthCard({ p }: { p: ProjectSummary }) {
  const [open, setOpen] = useState(false);
  const top = p.health.signals.slice(0, 2);
  return (
    <article className="panel flex flex-col gap-3 p-4">
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <Link href={`/projects/${p.id}`} className="group">
            <span className="font-mono text-[11px] text-faint">{p.key}</span>
            <h3 className="truncate font-semibold group-hover:text-accent-ink">{p.name}</h3>
          </Link>
          <p className="mt-0.5 text-[11px] text-muted">
            {humanize(p.phase)} · {humanize(p.methodology)} · target {fmtDate(p.target_date)}
          </p>
        </div>
        <HealthBadge level={p.health.level} />
      </header>
      <ProgressSummary health={p.health} />
      {top.length > 0 && !open && (
        <ul className="space-y-1">
          {top.map((s) => (
            <li key={s.code} className="flex gap-1.5 text-xs text-muted">
              <span aria-hidden className={cx("mt-1.5 size-1.5 shrink-0 rounded-full", s.level === "red" ? "bg-bad" : "bg-warn")} />
              <span className="line-clamp-2">{s.message}</span>
            </li>
          ))}
        </ul>
      )}
      {open && <HealthExplanation projectId={p.id} health={p.health} />}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="mt-auto inline-flex items-center gap-1 self-start text-xs text-accent-ink hover:underline"
      >
        <ChevronDown className={cx("size-3.5 transition", open && "rotate-180")} aria-hidden />
        {open ? "Hide explanation" : `Why ${p.health.level}? (${p.health.signals.length} rule${p.health.signals.length === 1 ? "" : "s"})`}
      </button>
    </article>
  );
}

export default function CommandCenter() {
  const { me } = useSession();
  const dash = useDashboard();

  if (dash.isPending) return <Spinner label="Evaluating portfolio" />;
  if (dash.error) return <ErrorState error={dash.error} retry={() => dash.refetch()} />;
  const d = dash.data;
  const keyOf = Object.fromEntries(d.projects.map((p) => [p.id, p.key]));

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {greeting()}, {me.user.name.split(" ")[0]}
          </h1>
          <p className="text-sm text-muted">
            Portfolio evaluated on {fmtDate(d.evaluated_on, true)} from {d.projects.length} project
            {d.projects.length === 1 ? "" : "s"} in {me.organization.name}.
          </p>
        </div>
        {me.previous_seen_at && (
          <Link
            href="/activity?since=last"
            className="panel inline-flex items-center gap-2 px-3 py-2 text-sm hover:border-accent"
          >
            <Sparkles className="size-4 text-accent-ink" aria-hidden />
            <span>
              <strong className="tabular-nums">{d.changes_since_last_visit}</strong> change
              {d.changes_since_last_visit === 1 ? "" : "s"} by others since your last visit{" "}
              <span className="text-muted">({fmtRelative(me.previous_seen_at)})</span>
            </span>
          </Link>
        )}
      </header>

      <section aria-label="Key indicators" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {d.kpis.map((k) => (
          <KpiTile key={k.id} kpi={k} />
        ))}
      </section>

      <section aria-labelledby="portfolio-heading" className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 id="portfolio-heading" className="text-sm font-semibold tracking-wide">
            Portfolio health
          </h2>
          <span className="text-[11px] text-faint">Rule-based · every status links to its evidence</span>
        </div>
        {d.projects.length === 0 ? (
          <EmptyState
            title="No projects yet"
            action={
              <Link href="/projects?new=1" className="text-sm text-accent-ink hover:underline">
                Create your first project
              </Link>
            }
          >
            Projects you create appear here with explainable health.
          </EmptyState>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {d.projects.map((p) => (
              <ProjectHealthCard key={p.id} p={p} />
            ))}
          </div>
        )}
      </section>

      <div className="grid items-start gap-4 xl:grid-cols-3">
        <Panel
          title={
            <span className="flex items-center gap-2">
              <OctagonX className="size-4 text-bad" aria-hidden /> Critical risks & issues
            </span>
          }
          bodyClassName="p-2"
        >
          {d.critical_risks.length === 0 ? (
            <p className="p-3 text-sm text-muted">No open risks scoring ≥ 15 and no critical issues.</p>
          ) : (
            <ul className="divide-y divide-line">
              {d.critical_risks.map((r) => (
                <li key={r.id}>
                  <Link href={`/projects/${r.project_id}/raid#raid-${r.id}`} className="block rounded-lg p-2.5 hover:bg-surface-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-faint">{r.key}</span>
                      <Badge tone="bad">{r.score !== null ? `Score ${r.score}` : humanize(r.priority)}</Badge>
                      <Badge>{humanize(r.type)}</Badge>
                    </div>
                    <p className="mt-1 text-sm">{r.title}</p>
                    {r.escalation_trigger && (
                      <p className="mt-0.5 line-clamp-1 text-[11px] text-muted">Escalate if: {r.escalation_trigger}</p>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title={
            <span className="flex items-center gap-2">
              <AlertTriangle className="size-4 text-warn" aria-hidden /> Blocked work
            </span>
          }
          bodyClassName="p-2"
        >
          {d.blocked_items.length === 0 ? (
            <p className="p-3 text-sm text-muted">Nothing is blocked.</p>
          ) : (
            <ul className="divide-y divide-line">
              {d.blocked_items.map((w) => (
                <li key={w.id}>
                  <Link href={`/projects/${w.project_id}/board?item=${w.id}`} className="flex items-start gap-2 rounded-lg p-2.5 hover:bg-surface-2">
                    <TypeIcon type={w.type} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm">
                        <span className="mr-1.5 font-mono text-[11px] text-faint">{w.key}</span>
                        {w.title}
                      </p>
                      {w.description && <p className="mt-0.5 line-clamp-2 text-[11px] text-muted">{w.description}</p>}
                    </div>
                    <PriorityIcon priority={w.priority} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title={
            <span className="flex items-center gap-2">
              <CalendarClock className="size-4 text-accent-3" aria-hidden /> Next 21 days
            </span>
          }
          bodyClassName="p-2"
        >
          {d.deadlines.length === 0 ? (
            <p className="p-3 text-sm text-muted">No milestones or due dates in the next three weeks.</p>
          ) : (
            <ul className="divide-y divide-line">
              {d.deadlines.map((x) => (
                <li key={x.entity_type + x.id}>
                  <Link
                    href={
                      x.entity_type === "milestone"
                        ? `/projects/${x.project_id}/timeline#ms-${x.id}`
                        : `/projects/${x.project_id}/backlog?item=${x.id}`
                    }
                    className="flex items-center gap-2 rounded-lg p-2.5 text-sm hover:bg-surface-2"
                  >
                    <span className={cx("w-14 shrink-0 text-xs tabular-nums", x.overdue ? "font-semibold text-bad" : "text-muted")}>
                      {fmtDate(x.date)}
                    </span>
                    <span className="min-w-0 flex-1 truncate">
                      {x.entity_type === "milestone" ? <Badge tone="accent">Milestone</Badge> : <span className="font-mono text-[11px] text-faint">{x.label}</span>}{" "}
                      {x.title}
                    </span>
                    {x.overdue && <Badge tone="bad">Overdue</Badge>}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="grid items-start gap-4 xl:grid-cols-[1fr_2fr]">
        <Panel
          title={
            <span className="flex items-center gap-2">
              <Gavel className="size-4 text-accent-ink" aria-hidden /> Decisions awaiting approval
            </span>
          }
          bodyClassName="p-2"
        >
          {d.pending_decisions.length === 0 ? (
            <p className="p-3 text-sm text-muted">No proposed decisions are waiting.</p>
          ) : (
            <ul className="divide-y divide-line">
              {d.pending_decisions.map((x) => (
                <li key={x.id}>
                  <Link href={`/projects/${x.project_id}/decisions#dec-${x.id}`} className="block rounded-lg p-2.5 hover:bg-surface-2">
                    <span className="font-mono text-[11px] text-faint">{x.key}</span>
                    <p className="text-sm">{x.title}</p>
                    <p className="text-[11px] text-muted">Proposed {fmtRelative(x.created_at)}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel
          title="Recent activity"
          action={
            <Link href="/activity" className="text-xs text-accent-ink hover:underline">
              View all
            </Link>
          }
          bodyClassName="p-2"
        >
          <ActivityList events={d.recent_activity} projectKeys={keyOf} compact />
        </Panel>
      </div>
    </div>
  );
}
