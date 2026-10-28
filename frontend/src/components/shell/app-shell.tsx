"use client";

import { Activity, FolderKanban, Gauge, Keyboard, LogOut, Moon, Search, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { HealthBadge } from "@/components/domain";
import { useTheme } from "@/components/providers";
import { Avatar, Badge, Button, cx, Dialog, Select } from "@/components/ui";
import { humanize } from "@/lib/format";
import { useProjects } from "@/lib/queries";
import { CommandPalette } from "./command-palette";
import { Logo } from "./logo";
import { useSession } from "./session";

const NAV = [
  { href: "/", label: "Command Center", icon: Gauge, match: (p: string) => p === "/" },
  { href: "/projects", label: "Projects", icon: FolderKanban, match: (p: string) => p.startsWith("/projects") },
  { href: "/activity", label: "Activity", icon: Activity, match: (p: string) => p.startsWith("/activity") },
];

const SHORTCUTS: [string, string][] = [
  ["⌘K / Ctrl K or /", "Open command palette & search"],
  ["g then d", "Go to Command Center"],
  ["g then p", "Go to Projects"],
  ["g then a", "Go to Activity"],
  ["?", "Show keyboard shortcuts"],
  ["Esc", "Close dialogs and panels"],
];

function isTyping(e: KeyboardEvent): boolean {
  const t = e.target as HTMLElement | null;
  return !!t && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName));
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { me, signOut, switchOrg } = useSession();
  const { resolved, setTheme } = useTheme();
  const projects = useProjects();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const pendingG = useRef<number | null>(null);

  const closePalette = useCallback(() => setPaletteOpen(false), []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
        return;
      }
      if (isTyping(e) || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "/") {
        e.preventDefault();
        setPaletteOpen(true);
      } else if (e.key === "?") {
        setHelpOpen(true);
      } else if (e.key === "g") {
        pendingG.current = window.setTimeout(() => (pendingG.current = null), 1000);
      } else if (pendingG.current) {
        const dest = { d: "/", p: "/projects", a: "/activity" }[e.key];
        window.clearTimeout(pendingG.current);
        pendingG.current = null;
        if (dest) router.push(dest);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [router]);

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[248px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="no-print sticky top-0 hidden h-dvh flex-col border-r border-line bg-surface/60 backdrop-blur lg:flex">
        <div className="px-4 py-4">
          <Link href="/" aria-label="ProjectForge AI home">
            <Logo />
          </Link>
        </div>
        <nav aria-label="Main" className="space-y-0.5 px-2">
          {NAV.map(({ href, label, icon: Icon, match }) => (
            <Link
              key={href}
              href={href}
              aria-current={match(pathname) ? "page" : undefined}
              className={cx(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition",
                match(pathname) ? "bg-accent-soft font-medium text-fg" : "text-muted hover:bg-surface-2 hover:text-fg",
              )}
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-6 px-4 text-[10px] font-semibold uppercase tracking-wider text-faint">Projects</div>
        <ul className="scrollbar-thin mt-1 flex-1 space-y-0.5 overflow-y-auto px-2">
          {projects.data?.map((p) => {
            const href = `/projects/${p.id}`;
            const active = pathname.startsWith(href);
            return (
              <li key={p.id}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cx(
                    "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm",
                    active ? "bg-surface-2 text-fg" : "text-muted hover:bg-surface-2 hover:text-fg",
                  )}
                >
                  <span
                    aria-hidden
                    className={cx(
                      "size-2 rounded-full",
                      p.health.level === "red" ? "bg-bad" : p.health.level === "amber" ? "bg-warn" : "bg-ok",
                    )}
                  />
                  <span className="font-mono text-[11px] text-faint">{p.key}</span>
                  <span className="truncate">{p.name}</span>
                  <span className="sr-only">
                    <HealthBadge level={p.health.level} />
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="space-y-3 border-t border-line p-3">
          {me.memberships.length > 1 && (
            <label className="block">
              <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-faint">Organization</span>
              <Select value={me.organization.id} onChange={(e) => switchOrg(e.target.value)} aria-label="Switch organization">
                {me.memberships.map((m) => (
                  <option key={m.organization.id} value={m.organization.id}>
                    {m.organization.name}
                  </option>
                ))}
              </Select>
            </label>
          )}
          <div className="flex items-center gap-2.5">
            <Avatar name={me.user.name} color={me.user.avatar_color} size={32} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{me.user.name}</p>
              <p className="truncate text-[11px] text-muted">
                {humanize(me.role)} · {me.organization.name}
              </p>
            </div>
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setTheme(resolved === "dark" ? "light" : "dark")}
              aria-label={resolved === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            >
              {resolved === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setHelpOpen(true)} aria-label="Keyboard shortcuts">
              <Keyboard className="size-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => void signOut()} className="ml-auto">
              <LogOut className="size-4" aria-hidden /> Sign out
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-col pb-16 lg:pb-0">
        {/* Top bar */}
        <header className="no-print sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-bg/70 px-4 backdrop-blur">
          <Link href="/" className="lg:hidden" aria-label="ProjectForge AI home">
            <Logo compact />
          </Link>
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="flex h-9 flex-1 items-center gap-2 rounded-lg border border-line bg-surface-2 px-3 text-left text-sm text-faint transition hover:border-line-strong sm:max-w-md"
          >
            <Search className="size-4" aria-hidden />
            <span className="flex-1 truncate">Search or jump to…</span>
            <kbd className="hidden rounded border border-line px-1.5 text-[10px] sm:inline">⌘K</kbd>
          </button>
          <div className="ml-auto flex items-center gap-2">
            {me.organization.is_demo && (
              <span className="hidden sm:block">
                <Badge tone="accent">Demo · synthetic data</Badge>
              </span>
            )}
            <span className="lg:hidden">
              <Avatar name={me.user.name} color={me.user.avatar_color} size={28} />
            </span>
          </div>
        </header>

        <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-5 sm:px-6">
          {children}
        </main>
      </div>

      {/* Mobile bottom navigation */}
      <nav
        aria-label="Main"
        className="no-print fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-line bg-surface/95 backdrop-blur lg:hidden"
      >
        {NAV.map(({ href, label, icon: Icon, match }) => (
          <Link
            key={href}
            href={href}
            aria-current={match(pathname) ? "page" : undefined}
            className={cx(
              "flex flex-col items-center gap-0.5 py-2 text-[11px]",
              match(pathname) ? "text-accent-ink" : "text-muted",
            )}
          >
            <Icon className="size-5" aria-hidden />
            {label.replace("Command Center", "Home")}
          </Link>
        ))}
        <button
          type="button"
          onClick={() => void signOut()}
          className="flex flex-col items-center gap-0.5 py-2 text-[11px] text-muted"
        >
          <LogOut className="size-5" aria-hidden />
          Sign out
        </button>
      </nav>

      <CommandPalette open={paletteOpen} onClose={closePalette} />
      <Dialog open={helpOpen} onClose={() => setHelpOpen(false)} title="Keyboard shortcuts">
        <dl className="space-y-2 text-sm">
          {SHORTCUTS.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4">
              <dt>
                <kbd className="rounded border border-line bg-surface-2 px-1.5 py-0.5 font-mono text-xs">{k}</kbd>
              </dt>
              <dd className="text-muted">{v}</dd>
            </div>
          ))}
        </dl>
      </Dialog>
    </div>
  );
}
