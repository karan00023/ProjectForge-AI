"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type AuditEvent,
  type Dashboard,
  type Decision,
  type DecisionCreate,
  type DecisionUpdate,
  type Link,
  type Me,
  type Member,
  type Milestone,
  type MilestoneCreate,
  type MilestoneUpdate,
  type Project,
  type ProjectCreate,
  type ProjectSummary,
  type ProjectTemplate,
  type ProjectUpdate,
  type Raid,
  type RaidCreate,
  type RaidUpdate,
  type SearchHit,
  type Sprint,
  type WorkItem,
  type WorkItemCreate,
  type WorkItemDetail,
  type WorkItemUpdate,
} from "./api";

export const qk = {
  me: ["me"] as const,
  members: ["members"] as const,
  dashboard: ["dashboard"] as const,
  projects: ["projects"] as const,
  templates: ["templates"] as const,
  project: (id: string) => ["project", id] as const,
  items: (id: string) => ["project", id, "items"] as const,
  links: (id: string) => ["project", id, "links"] as const,
  milestones: (id: string) => ["project", id, "milestones"] as const,
  sprints: (id: string) => ["project", id, "sprints"] as const,
  raid: (id: string) => ["project", id, "raid"] as const,
  decisions: (id: string) => ["project", id, "decisions"] as const,
  item: (id: string) => ["item", id] as const,
  activity: (projectId?: string) => ["activity", projectId ?? "all"] as const,
  search: (q: string) => ["search", q] as const,
};

export const useMe = () => useQuery({ queryKey: qk.me, queryFn: () => api<Me>("/auth/me"), retry: false });
export const useMembers = () =>
  useQuery({ queryKey: qk.members, queryFn: () => api<Member[]>("/org/members"), staleTime: 60_000 });
export const useDashboard = () => useQuery({ queryKey: qk.dashboard, queryFn: () => api<Dashboard>("/dashboard") });
export const useProjects = () =>
  useQuery({ queryKey: qk.projects, queryFn: () => api<ProjectSummary[]>("/projects") });
export const useTemplates = () =>
  useQuery({ queryKey: qk.templates, queryFn: () => api<ProjectTemplate[]>("/project-templates"), staleTime: Infinity });
export const useProject = (id: string) =>
  useQuery({ queryKey: qk.project(id), queryFn: () => api<ProjectSummary>(`/projects/${id}`) });
export const useWorkItems = (id: string) =>
  useQuery({ queryKey: qk.items(id), queryFn: () => api<WorkItem[]>(`/projects/${id}/work-items`) });
export const useLinks = (id: string) =>
  useQuery({ queryKey: qk.links(id), queryFn: () => api<Link[]>(`/projects/${id}/links`) });
export const useMilestones = (id: string) =>
  useQuery({ queryKey: qk.milestones(id), queryFn: () => api<Milestone[]>(`/projects/${id}/milestones`) });
export const useSprints = (id: string) =>
  useQuery({ queryKey: qk.sprints(id), queryFn: () => api<Sprint[]>(`/projects/${id}/sprints`) });
export const useRaid = (id: string) =>
  useQuery({ queryKey: qk.raid(id), queryFn: () => api<Raid[]>(`/projects/${id}/raid`) });
export const useDecisions = (id: string) =>
  useQuery({ queryKey: qk.decisions(id), queryFn: () => api<Decision[]>(`/projects/${id}/decisions`) });
export const useWorkItem = (id: string | null) =>
  useQuery({
    queryKey: qk.item(id ?? "none"),
    queryFn: () => api<WorkItemDetail>(`/work-items/${id}`),
    enabled: !!id,
  });
export const useActivity = (projectId?: string, limit = 50) =>
  useQuery({
    queryKey: qk.activity(projectId),
    queryFn: () => api<AuditEvent[]>("/activity", { query: { project_id: projectId, limit: String(limit) } }),
  });
export const useSearch = (q: string) =>
  useQuery({
    queryKey: qk.search(q),
    queryFn: () => api<SearchHit[]>("/search", { query: { q } }),
    enabled: q.trim().length > 0,
    staleTime: 10_000,
  });

/** Any write can change health, KPIs and activity, so refresh the project and portfolio views. */
function useInvalidateProject() {
  const qc = useQueryClient();
  return (projectId?: string) => {
    if (projectId) qc.invalidateQueries({ queryKey: ["project", projectId] });
    qc.invalidateQueries({ queryKey: qk.projects });
    qc.invalidateQueries({ queryKey: qk.dashboard });
    qc.invalidateQueries({ queryKey: ["activity"] });
    qc.invalidateQueries({ queryKey: ["item"] });
  };
}

export function useCreateProject() {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: (body: ProjectCreate) => api<Project>("/projects", { method: "POST", body }),
    onSuccess: () => invalidate(),
  });
}

export function useUpdateProject(id: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: (body: ProjectUpdate) => api<Project>(`/projects/${id}`, { method: "PATCH", body }),
    onSuccess: () => invalidate(id),
  });
}

export function useCreateItem(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: (body: WorkItemCreate) =>
      api<WorkItem>(`/projects/${projectId}/work-items`, { method: "POST", body }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useUpdateItem(projectId: string) {
  const qc = useQueryClient();
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: ({ id, ...body }: WorkItemUpdate & { id: string }) =>
      api<WorkItem>(`/work-items/${id}`, { method: "PATCH", body }),
    // Optimistic update keeps drag-and-drop on the board instant.
    onMutate: async ({ id, ...body }) => {
      await qc.cancelQueries({ queryKey: qk.items(projectId) });
      const previous = qc.getQueryData<WorkItem[]>(qk.items(projectId));
      qc.setQueryData<WorkItem[]>(qk.items(projectId), (items) =>
        items?.map((w) => (w.id === id ? ({ ...w, ...body } as WorkItem) : w)),
      );
      return { previous };
    },
    onError: (_e, _v, context) => {
      if (context?.previous) qc.setQueryData(qk.items(projectId), context.previous);
    },
    onSettled: () => invalidate(projectId),
  });
}

export function useDeleteItem(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: (id: string) => api(`/work-items/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useCreateLink(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: ({ sourceId, targetId, type }: { sourceId: string; targetId: string; type: Link["type"] }) =>
      api<Link>(`/work-items/${sourceId}/links`, { method: "POST", body: { target_id: targetId, type } }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useDeleteLink(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: (linkId: string) => api(`/work-item-links/${linkId}`, { method: "DELETE" }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useCreateMilestone(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: (body: MilestoneCreate) =>
      api<Milestone>(`/projects/${projectId}/milestones`, { method: "POST", body }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useUpdateMilestone(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: ({ id, ...body }: MilestoneUpdate & { id: string }) =>
      api<Milestone>(`/milestones/${id}`, { method: "PATCH", body }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useRebaseline(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api<Milestone>(`/milestones/${id}/rebaseline`, { method: "POST", body: { reason } }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useCreateRaid(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: (body: RaidCreate) => api<Raid>(`/projects/${projectId}/raid`, { method: "POST", body }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useUpdateRaid(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: ({ id, ...body }: RaidUpdate & { id: string }) =>
      api<Raid>(`/raid/${id}`, { method: "PATCH", body }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useCreateDecision(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: (body: DecisionCreate) =>
      api<Decision>(`/projects/${projectId}/decisions`, { method: "POST", body }),
    onSuccess: () => invalidate(projectId),
  });
}

export function useUpdateDecision(projectId: string) {
  const invalidate = useInvalidateProject();
  return useMutation({
    mutationFn: ({ id, ...body }: DecisionUpdate & { id: string }) =>
      api<Decision>(`/decisions/${id}`, { method: "PATCH", body }),
    onSuccess: () => invalidate(projectId),
  });
}
