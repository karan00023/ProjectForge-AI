"use client";

import { useParams, usePathname } from "next/navigation";
import { HealthBadge } from "@/components/domain";
import { ProjectProvider } from "@/components/project/context";
import { ItemDrawer } from "@/components/project/item-drawer";
import { Badge, ErrorState, Spinner, TabLinks } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fmtDate, humanize } from "@/lib/format";
import { useProject } from "@/lib/queries";

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const { id } = useParams<{ id: string }>();
  const pathname = usePathname();
  const project = useProject(id);

  if (project.isPending) return <Spinner label="Loading project" />;
  if (project.error) {
    if (project.error instanceof ApiError && project.error.status === 404) {
      return <ErrorState error={new Error("This project does not exist or you do not have access to it.")} />;
    }
    return <ErrorState error={project.error} retry={() => project.refetch()} />;
  }
  const p = project.data;
  const base = `/projects/${p.id}`;
  const tabs = [
    { key: "overview", label: "Overview", href: base },
    { key: "board", label: "Board", href: `${base}/board` },
    { key: "backlog", label: "Backlog", href: `${base}/backlog` },
    { key: "timeline", label: "Timeline", href: `${base}/timeline` },
    { key: "raid", label: "RAID", href: `${base}/raid` },
    { key: "decisions", label: "Decisions", href: `${base}/decisions` },
    { key: "activity", label: "Activity", href: `${base}/activity` },
  ];
  const active = tabs.find((t) => t.key !== "overview" && pathname.startsWith(t.href))?.key ?? "overview";

  return (
    <ProjectProvider project={p}>
      <div className="space-y-4">
        <header className="space-y-3 border-b border-line">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-xs text-muted">
                <span className="font-mono">{p.key}</span>
                <Badge>{humanize(p.kind)}</Badge>
                <Badge>{humanize(p.methodology)}</Badge>
                <Badge tone="accent">{humanize(p.phase)}</Badge>
              </div>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">{p.name}</h1>
              <p className="text-xs text-muted">
                {humanize(p.status)} · {fmtDate(p.start_date, true)} → {fmtDate(p.target_date, true)}
              </p>
            </div>
            <HealthBadge level={p.health.level} className="text-xs" />
          </div>
          <TabLinks tabs={tabs} active={active} />
        </header>
        {children}
      </div>
      <ItemDrawer />
    </ProjectProvider>
  );
}
