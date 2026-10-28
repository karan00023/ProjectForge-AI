"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { createContext, useCallback, useContext, type ReactNode } from "react";
import type { Member, Milestone, ProjectSummary, Sprint, WorkItem } from "@/lib/api";
import { useMembers, useMilestones, useSprints, useWorkItems } from "@/lib/queries";

type ProjectCtx = {
  project: ProjectSummary;
  members: Member[];
  items: WorkItem[] | undefined;
  sprints: Sprint[] | undefined;
  milestones: Milestone[] | undefined;
  /** Opens the work-item drawer by putting ?item=<id> in the URL (shareable, back-button friendly). */
  openItem: (id: string | null) => void;
  openItemId: string | null;
};

const Ctx = createContext<ProjectCtx | null>(null);

export function useProjectCtx(): ProjectCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useProjectCtx outside ProjectProvider");
  return v;
}

export function ProjectProvider({ project, children }: { project: ProjectSummary; children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const members = useMembers();
  const items = useWorkItems(project.id);
  const sprints = useSprints(project.id);
  const milestones = useMilestones(project.id);
  const openItemId = params.get("item");

  const openItem = useCallback(
    (id: string | null) => {
      const next = new URLSearchParams(params.toString());
      if (id) next.set("item", id);
      else next.delete("item");
      const qs = next.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, pathname, router],
  );

  return (
    <Ctx.Provider
      value={{
        project,
        members: members.data ?? [],
        items: items.data,
        sprints: sprints.data,
        milestones: milestones.data,
        openItem,
        openItemId,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}
