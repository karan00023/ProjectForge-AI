"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { ActivityList } from "@/components/activity-list";
import { useSession } from "@/components/shell/session";
import { ErrorState, Field, Panel, Select, Spinner } from "@/components/ui";
import { fmtRelative } from "@/lib/format";
import { useActivity, useProjects } from "@/lib/queries";

export default function ActivityPage() {
  const params = useSearchParams();
  const { me } = useSession();
  const projects = useProjects();
  const [projectId, setProjectId] = useState<string>("");
  const [onlyNew, setOnlyNew] = useState(params.get("since") === "last");
  const feed = useActivity(projectId || undefined, 200);
  const since = me.previous_seen_at;
  const keys = Object.fromEntries((projects.data ?? []).map((p) => [p.id, p.key]));
  const events = (feed.data ?? []).filter(
    (e) => !onlyNew || !since || (new Date(e.created_at) > new Date(since) && e.actor_user_id !== me.user.id),
  );

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Activity</h1>
        <p className="text-sm text-muted">Every change is recorded in the audit log with who made it and when.</p>
      </header>
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-60">
          <Field label="Project">
            <Select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">All projects</option>
              {projects.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.key} — {p.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
        {since && (
          <label className="flex h-9 items-center gap-2 text-sm">
            <input type="checkbox" checked={onlyNew} onChange={(e) => setOnlyNew(e.target.checked)} className="accent-[var(--accent)]" />
            Only changes by others since my last visit ({fmtRelative(since)})
          </label>
        )}
      </div>
      <Panel bodyClassName="p-2">
        {feed.isPending ? (
          <Spinner />
        ) : feed.error ? (
          <ErrorState error={feed.error} retry={() => feed.refetch()} />
        ) : (
          <ActivityList events={events} projectKeys={keys} since={onlyNew ? null : since} />
        )}
      </Panel>
    </div>
  );
}
