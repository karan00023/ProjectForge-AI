"use client";

import { ActivityList } from "@/components/activity-list";
import { useProjectCtx } from "@/components/project/context";
import { useSession } from "@/components/shell/session";
import { ErrorState, Panel, Spinner } from "@/components/ui";
import { useActivity } from "@/lib/queries";

export default function ProjectActivityPage() {
  const { project } = useProjectCtx();
  const { me } = useSession();
  const feed = useActivity(project.id, 200);
  return (
    <Panel bodyClassName="p-2">
      {feed.isPending ? (
        <Spinner />
      ) : feed.error ? (
        <ErrorState error={feed.error} retry={() => feed.refetch()} />
      ) : (
        <ActivityList events={feed.data} since={me.previous_seen_at} />
      )}
    </Panel>
  );
}
