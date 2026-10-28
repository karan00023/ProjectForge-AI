"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Logo } from "@/components/shell/logo";
import { Avatar, Badge, Button, Field, FormError, Input, Panel } from "@/components/ui";
import { api, setActiveOrg, type DemoPersona } from "@/lib/api";
import { humanize } from "@/lib/format";

export default function LoginPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const personas = useQuery({
    queryKey: ["demo-personas"],
    queryFn: () => api<DemoPersona[]>("/auth/demo-personas"),
    retry: false,
  });

  async function finish() {
    setActiveOrg(null);
    qc.clear();
    router.replace("/");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy("password");
    try {
      await api("/auth/login", { method: "POST", body: { email, password } });
      await finish();
    } catch (err) {
      setError(err);
      setBusy(null);
    }
  }

  async function demo(p: DemoPersona) {
    setError(null);
    setBusy(p.email);
    try {
      await api("/auth/demo-login", { method: "POST", body: { email: p.email } });
      await finish();
    } catch (err) {
      setError(err);
      setBusy(null);
    }
  }

  const groups = (personas.data ?? []).reduce<Record<string, DemoPersona[]>>((acc, p) => {
    (acc[p.organization] ??= []).push(p);
    return acc;
  }, {});

  return (
    <main className="mx-auto grid min-h-dvh max-w-6xl items-center gap-10 px-4 py-10 lg:grid-cols-[1.1fr_1fr]">
      <section className="space-y-6">
        <Logo large />
        <h1 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          Run delivery with{" "}
          <span className="bg-gradient-to-r from-accent via-accent-2 to-accent-3 bg-clip-text text-transparent">
            evidence, not guesswork
          </span>
          .
        </h1>
        <p className="max-w-xl text-muted">
          ProjectForge AI is a project management operating system for technical programs: portfolio health you can
          trace to records, dependency-aware plans, RAID and decision logs — with AI agents that prepare the work and
          humans who approve it.
        </p>
        <ul className="grid gap-3 text-sm sm:grid-cols-2">
          <li className="panel flex gap-2 p-3">
            <ShieldCheck className="size-4 shrink-0 text-ok" aria-hidden />
            Every red/amber status links to the records that caused it.
          </li>
          <li className="panel flex gap-2 p-3">
            <Sparkles className="size-4 shrink-0 text-accent-ink" aria-hidden />
            AI drafts and investigates; consequential changes need approval.
          </li>
        </ul>
      </section>

      <div className="space-y-4">
        {personas.data && personas.data.length > 0 && (
          <Panel
            title={
              <span className="flex items-center gap-2">
                Explore the demo <Badge tone="accent">Synthetic data</Badge>
              </span>
            }
          >
            <p className="mb-3 text-xs text-muted">
              Sign in as a fictional persona. Each role sees different permissions; Orbital Health Labs is a separate
              tenant whose data Meridian users can never see.
            </p>
            <div className="space-y-4">
              {Object.entries(groups).map(([org, list]) => (
                <div key={org}>
                  <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">{org}</h3>
                  <ul className="grid gap-1.5 sm:grid-cols-2">
                    {list.map((p) => (
                      <li key={p.email}>
                        <button
                          type="button"
                          onClick={() => demo(p)}
                          disabled={busy !== null}
                          className="flex w-full items-center gap-2.5 rounded-lg border border-line bg-surface-2 px-2.5 py-2 text-left transition hover:border-accent disabled:opacity-60"
                        >
                          <Avatar name={p.name} color={p.avatar_color} size={28} />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium">{p.name}</span>
                            <span className="block truncate text-[11px] text-muted">{p.title}</span>
                          </span>
                          <Badge tone={p.role === "viewer" ? "neutral" : "accent"}>{humanize(p.role)}</Badge>
                          {busy === p.email ? (
                            <span className="sr-only">Signing in</span>
                          ) : (
                            <ArrowRight className="size-3.5 text-faint" aria-hidden />
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </Panel>
        )}

        <Panel title="Sign in with email">
          <form onSubmit={onSubmit} className="space-y-3">
            <Field label="Email">
              <Input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <Field label="Password">
              <Input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            <FormError error={error} />
            <Button type="submit" variant="primary" className="w-full" loading={busy === "password"}>
              Sign in
            </Button>
          </form>
        </Panel>
      </div>
    </main>
  );
}
