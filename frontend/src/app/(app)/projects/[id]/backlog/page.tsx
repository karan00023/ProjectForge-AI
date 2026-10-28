"use client";

import { ChevronRight, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { MemberAvatar, PriorityIcon, StatusBadge, TypeIcon } from "@/components/domain";
import { useProjectCtx } from "@/components/project/context";
import { NewItemDialog } from "@/components/project/new-item";
import { useSession } from "@/components/shell/session";
import { Button, cx, EmptyState, Input, Spinner } from "@/components/ui";
import type { WorkItem, WorkItemType } from "@/lib/api";
import { fmtDate, todayIso, TYPE_LEVEL } from "@/lib/format";

type Node = { item: WorkItem; children: Node[] };

function buildTree(items: WorkItem[]): Node[] {
  const byId = new Map(items.map((w) => [w.id, { item: w, children: [] as Node[] }]));
  const roots: Node[] = [];
  for (const node of byId.values()) {
    const parent = node.item.parent_id ? byId.get(node.item.parent_id) : undefined;
    (parent ? parent.children : roots).push(node);
  }
  return roots;
}

/** Keep a node if it or any descendant matches. */
function filterTree(nodes: Node[], keep: (w: WorkItem) => boolean): Node[] {
  return nodes.flatMap((n) => {
    const children = filterTree(n.children, keep);
    return keep(n.item) || children.length ? [{ item: n.item, children }] : [];
  });
}

export default function BacklogPage() {
  const { items, sprints, members, openItem } = useProjectCtx();
  const { canWrite } = useSession();
  const [query, setQuery] = useState("");
  const [hideDone, setHideDone] = useState(false);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [creating, setCreating] = useState<{ parent_id?: string; type?: WorkItemType } | null>(null);
  const sprintName = Object.fromEntries((sprints ?? []).map((s) => [s.id, s.name]));

  const tree = useMemo(() => {
    if (!items) return [];
    const q = query.trim().toLowerCase();
    return filterTree(
      buildTree(items),
      (w) =>
        (!hideDone || (w.status !== "done" && w.status !== "cancelled")) &&
        (!q || w.title.toLowerCase().includes(q) || w.key.toLowerCase().includes(q) || w.labels.some((l) => l.includes(q))),
    );
  }, [items, query, hideDone]);

  if (!items) return <Spinner label="Loading backlog" />;
  const today = todayIso();

  const rows: { node: Node; depth: number }[] = [];
  const walk = (nodes: Node[], depth: number) => {
    for (const n of nodes) {
      rows.push({ node: n, depth });
      if (!collapsed.has(n.item.id)) walk(n.children, depth + 1);
    }
  };
  walk(tree, 0);

  const toggle = (id: string) =>
    setCollapsed((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by title, key or label"
          aria-label="Filter backlog"
          className="max-w-xs"
        />
        <label className="flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={hideDone} onChange={(e) => setHideDone(e.target.checked)} className="accent-[var(--accent)]" />
          Hide done & cancelled
        </label>
        <span className="text-[11px] text-faint">{items.length} items</span>
        {canWrite && (
          <Button variant="primary" className="ml-auto" onClick={() => setCreating({})}>
            <Plus className="size-4" aria-hidden /> New item
          </Button>
        )}
      </div>

      {rows.length === 0 ? (
        <EmptyState title={items.length ? "No items match the filter" : "The backlog is empty"}>
          {canWrite && !items.length ? "Start with an epic, then break it into stories." : undefined}
        </EmptyState>
      ) : (
        <div className="panel overflow-x-auto">
          <table className="w-full min-w-[880px] text-sm" aria-label="Backlog hierarchy">
            <thead className="border-b border-line text-left text-[11px] uppercase tracking-wider text-faint">
              <tr>
                <th className="px-3 py-2 font-semibold">Item</th>
                <th className="px-3 py-2 font-semibold">Status</th>
                <th className="px-3 py-2 font-semibold">Pts</th>
                <th className="px-3 py-2 font-semibold">Assignee</th>
                <th className="px-3 py-2 font-semibold">Sprint</th>
                <th className="px-3 py-2 font-semibold">Due</th>
                <th className="w-10 px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map(({ node, depth }) => {
                const w = node.item;
                const overdue = w.due_date && w.status !== "done" && w.status !== "cancelled" && w.due_date < today;
                const canHaveChildren = TYPE_LEVEL[w.type] < 5;
                return (
                  <tr key={w.id} className="hover:bg-surface-2/60">
                    <td className="py-1.5 pr-3" style={{ paddingLeft: 12 + depth * 20 }}>
                      <div className="flex items-center gap-1.5">
                        {node.children.length ? (
                          <button
                            type="button"
                            onClick={() => toggle(w.id)}
                            aria-expanded={!collapsed.has(w.id)}
                            aria-label={`${collapsed.has(w.id) ? "Expand" : "Collapse"} ${w.key}`}
                            className="text-faint hover:text-fg"
                          >
                            <ChevronRight className={cx("size-4 transition", !collapsed.has(w.id) && "rotate-90")} />
                          </button>
                        ) : (
                          <span className="w-4" />
                        )}
                        <TypeIcon type={w.type} />
                        <PriorityIcon priority={w.priority} />
                        <button type="button" onClick={() => openItem(w.id)} className="min-w-0 truncate text-left hover:text-accent-ink">
                          <span className="mr-1.5 font-mono text-[11px] text-faint">{w.key}</span>
                          <span className={cx(TYPE_LEVEL[w.type] <= 1 && "font-semibold", (w.status === "done" || w.status === "cancelled") && "text-muted line-through decoration-faint")}>{w.title}</span>
                        </button>
                        {node.children.length > 0 && <span className="text-[11px] text-faint">({node.children.length})</span>}
                      </div>
                    </td>
                    <td className="px-3 py-1.5">
                      <StatusBadge status={w.status} />
                    </td>
                    <td className="px-3 py-1.5 tabular-nums text-muted">{w.story_points ?? "—"}</td>
                    <td className="px-3 py-1.5">
                      <MemberAvatar members={members} userId={w.assignee_id} size={20} />
                    </td>
                    <td className="max-w-40 truncate px-3 py-1.5 text-xs text-muted">{w.sprint_id ? sprintName[w.sprint_id] : "—"}</td>
                    <td className={cx("px-3 py-1.5 text-xs tabular-nums", overdue ? "font-semibold text-bad" : "text-muted")}>{fmtDate(w.due_date)}</td>
                    <td className="px-3 py-1.5">
                      {canWrite && canHaveChildren && (
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Add child to ${w.key}`}
                          onClick={() =>
                            setCreating({
                              parent_id: w.id,
                              type: w.type === "epic" || w.type === "initiative" || w.type === "feature" ? "story" : "subtask",
                            })
                          }
                        >
                          <Plus className="size-3.5" />
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {creating && <NewItemDialog open onClose={() => setCreating(null)} defaults={creating} />}
    </div>
  );
}
