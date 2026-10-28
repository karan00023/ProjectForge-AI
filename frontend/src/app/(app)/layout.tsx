"use client";

import { Suspense } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { SessionGate } from "@/components/shell/session";
import { Spinner } from "@/components/ui";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionGate>
      <AppShell>
        <Suspense fallback={<Spinner />}>{children}</Suspense>
      </AppShell>
    </SessionGate>
  );
}
