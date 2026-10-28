import type { components } from "./api-types";

type S = components["schemas"];
export type Me = S["MeOut"];
export type Member = S["MemberOut"];
export type DemoPersona = S["DemoPersona"];
export type Project = S["ProjectOut"];
export type ProjectSummary = S["ProjectSummary"];
export type ProjectCreate = S["ProjectCreate"];
export type ProjectUpdate = S["ProjectUpdate"];
export type ProjectTemplate = S["ProjectTemplate"];
export type ProjectHealth = S["ProjectHealth"];
export type HealthSignal = S["HealthSignal"];
export type WorkItem = S["WorkItemOut"];
export type WorkItemDetail = S["WorkItemDetail"];
export type WorkItemCreate = S["WorkItemCreate"];
export type WorkItemUpdate = S["WorkItemUpdate"];
export type Link = S["LinkOut"];
export type Milestone = S["MilestoneOut"];
export type MilestoneCreate = S["MilestoneCreate"];
export type MilestoneUpdate = S["MilestoneUpdate"];
export type Sprint = S["SprintOut"];
export type Raid = S["RaidOut"];
export type RaidCreate = S["RaidCreate"];
export type RaidUpdate = S["RaidUpdate"];
export type Decision = S["DecisionOut"];
export type DecisionCreate = S["DecisionCreate"];
export type DecisionUpdate = S["DecisionUpdate"];
export type AuditEvent = S["AuditOut"];
export type Dashboard = S["DashboardOut"];
export type SearchHit = S["SearchHit"];
export type Kpi = S["Kpi"];

export type WorkItemStatus = WorkItem["status"];
export type WorkItemType = WorkItem["type"];
export type Priority = WorkItem["priority"];
export type HealthLevel = ProjectHealth["level"];

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const ORG_KEY = "pf.orgId";

export function getActiveOrg(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(ORG_KEY);
  } catch {
    return null;
  }
}

export function setActiveOrg(id: string | null) {
  try {
    if (id) window.localStorage.setItem(ORG_KEY, id);
    else window.localStorage.removeItem(ORG_KEY);
  } catch {
    /* storage unavailable: fall back to the default organization */
  }
}

function describe(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => {
        const field = d.loc?.filter((p) => p !== "body").join(".");
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return "Request failed";
}

export async function api<T = unknown>(
  path: string,
  init: { method?: string; body?: unknown; query?: Record<string, string | string[] | undefined> } = {},
): Promise<T> {
  const url = new URL(`/api${path}`, window.location.origin);
  for (const [k, v] of Object.entries(init.query ?? {})) {
    if (v === undefined) continue;
    for (const one of Array.isArray(v) ? v : [v]) url.searchParams.append(k, one);
  }
  const headers: Record<string, string> = { "X-Requested-With": "projectforge" };
  const org = getActiveOrg();
  if (org) headers["X-Org-Id"] = org;
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(url, {
    method: init.method ?? "GET",
    headers,
    credentials: "same-origin",
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, describe(data?.detail) || res.statusText);
  return data as T;
}
