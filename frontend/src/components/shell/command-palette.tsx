"use client";

import { CornerDownLeft, FileSearch, Hash, Moon, Navigation, Search, Sun } from "lucide-react";
import { useRouter } from "next/navigation";
import { useDeferredValue, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useTheme } from "@/components/providers";
import { cx } from "@/components/ui";
import type { SearchHit } from "@/lib/api";
import { useProjects, useSearch } from "@/lib/queries";
import { useSession } from "./session";

type Command = { id: string; label: string; hint?: string; group: string; icon: ReactNode; run: () => void };

function hitHref(h: SearchHit): string {
  switch (h.entity_type) {
    case "project":
      return `/projects/${h.id}`;
    case "work_item":
      return `/projects/${h.project_id}/backlog?item=${h.id}`;
    case "raid_item":
      return `/projects/${h.project_id}/raid#raid-${h.id}`;
    case "decision":
      return `/projects/${h.project_id}/decisions#dec-${h.id}`;
  }
}

const SECTIONS = [
  ["", "Overview"],
  ["/board", "Board"],
  ["/backlog", "Backlog"],
  ["/timeline", "Timeline"],
  ["/raid", "RAID"],
  ["/decisions", "Decisions"],
] as const;

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const { signOut, canWrite } = useSession();
  const { resolved, setTheme } = useTheme();
  const projects = useProjects();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const deferred = useDeferredValue(query);
  const search = useSearch(deferred.trim().length >= 2 ? deferred : "");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) {
      el.showModal();
      setQuery("");
      setActive(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
    if (!open && el.open) el.close();
  }, [open]);

  const commands = useMemo<Command[]>(() => {
    const go = (href: string) => () => {
      onClose();
      router.push(href);
    };
    const base: Command[] = [
      { id: "nav-home", label: "Command Center", hint: "g d", group: "Navigate", icon: <Navigation className="size-4" />, run: go("/") },
      { id: "nav-projects", label: "All projects", hint: "g p", group: "Navigate", icon: <Navigation className="size-4" />, run: go("/projects") },
      { id: "nav-activity", label: "Activity feed", hint: "g a", group: "Navigate", icon: <Navigation className="size-4" />, run: go("/activity") },
    ];
    if (canWrite) {
      base.push({ id: "new-project", label: "Create project…", group: "Actions", icon: <Hash className="size-4" />, run: go("/projects?new=1") });
    }
    base.push({
      id: "theme",
      label: resolved === "dark" ? "Switch to light theme" : "Switch to dark theme",
      group: "Actions",
      icon: resolved === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />,
      run: () => {
        setTheme(resolved === "dark" ? "light" : "dark");
        onClose();
      },
    });
    base.push({ id: "signout", label: "Sign out", group: "Actions", icon: <CornerDownLeft className="size-4" />, run: () => void signOut() });
    for (const p of projects.data ?? []) {
      for (const [suffix, name] of SECTIONS) {
        base.push({
          id: `p-${p.id}${suffix}`,
          label: `${p.key} · ${name}`,
          hint: p.name,
          group: "Projects",
          icon: <Hash className="size-4" />,
          run: go(`/projects/${p.id}${suffix}`),
        });
      }
    }
    return base;
  }, [projects.data, router, onClose, canWrite, resolved, setTheme, signOut]);

  const q = query.trim().toLowerCase();
  const filtered = q
    ? commands.filter((c) => `${c.label} ${c.hint ?? ""}`.toLowerCase().includes(q)).slice(0, 8)
    : // Without a query, show navigation, actions and each project's overview only.
      commands.filter((c) => c.group !== "Projects" || !c.id.includes("/")).slice(0, 12);
  const hits: Command[] = (search.data ?? []).slice(0, 8).map((h) => ({
    id: `hit-${h.id}`,
    label: `${h.label} · ${h.title}`,
    hint: h.entity_type.replace("_", " "),
    group: "Search results",
    icon: <FileSearch className="size-4" />,
    run: () => {
      onClose();
      router.push(hitHref(h));
    },
  }));
  const all = [...filtered, ...hits];
  const activeIndex = Math.min(active, Math.max(all.length - 1, 0));

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((activeIndex + 1) % Math.max(all.length, 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((activeIndex - 1 + all.length) % Math.max(all.length, 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      all[activeIndex]?.run();
    }
  }

  let lastGroup = "";
  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onCancel={onClose}
      aria-label="Command palette"
      className="panel mx-auto mt-[12vh] w-[calc(100%-2rem)] max-w-xl overflow-hidden p-0 text-fg"
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      {open && (
        <div onKeyDown={onKeyDown}>
          <div className="flex items-center gap-2 border-b border-line px-4">
            <Search className="size-4 text-faint" aria-hidden />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setActive(0);
              }}
              placeholder="Search work, risks, decisions — or jump to a page"
              aria-label="Search or run a command"
              role="combobox"
              aria-expanded="true"
              aria-controls="palette-list"
              aria-activedescendant={all[activeIndex] ? `cmd-${all[activeIndex].id}` : undefined}
              className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-faint focus-visible:outline-none"
            />
            <kbd className="rounded border border-line px-1.5 text-[10px] text-faint">Esc</kbd>
          </div>
          <ul id="palette-list" role="listbox" className="scrollbar-thin max-h-[50vh] overflow-y-auto p-2">
            {all.length === 0 && (
              <li className="px-3 py-6 text-center text-sm text-muted">
                {search.isFetching ? "Searching…" : "No matches"}
              </li>
            )}
            {all.map((c, i) => {
              const header = c.group !== lastGroup ? c.group : null;
              lastGroup = c.group;
              return (
                <li key={c.id} role="presentation">
                  {header && (
                    <div className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-faint">{header}</div>
                  )}
                  <div
                    id={`cmd-${c.id}`}
                    role="option"
                    aria-selected={i === activeIndex}
                    onMouseEnter={() => setActive(i)}
                    onClick={c.run}
                    className={cx(
                      "flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm",
                      i === activeIndex ? "bg-accent-soft text-fg" : "text-muted",
                    )}
                  >
                    <span className="text-faint">{c.icon}</span>
                    <span className="min-w-0 flex-1 truncate">{c.label}</span>
                    {c.hint && <span className="truncate text-[11px] text-faint">{c.hint}</span>}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </dialog>
  );
}
