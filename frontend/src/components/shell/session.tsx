"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, type ReactNode } from "react";
import { Spinner } from "@/components/ui";
import { api, ApiError, setActiveOrg, type Me } from "@/lib/api";
import { useMe } from "@/lib/queries";

type Session = {
  me: Me;
  /** viewer < member < admin < owner — mirrors backend role checks for UI affordances only. */
  canWrite: boolean;
  canAdmin: boolean;
  signOut: () => Promise<void>;
  switchOrg: (id: string) => void;
};

const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const s = useContext(SessionContext);
  if (!s) throw new Error("useSession outside SessionGate");
  return s;
}

export function SessionGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const qc = useQueryClient();
  const me = useMe();
  const unauthorized = me.error instanceof ApiError && (me.error.status === 401 || me.error.status === 404);

  useEffect(() => {
    if (unauthorized) {
      // A stale org selection (404) or an expired session (401) both restart at sign-in.
      setActiveOrg(null);
      router.replace("/login");
    }
  }, [unauthorized, router]);

  const signOut = useCallback(async () => {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    setActiveOrg(null);
    qc.clear();
    router.replace("/login");
  }, [qc, router]);

  const switchOrg = useCallback(
    (id: string) => {
      setActiveOrg(id);
      qc.clear();
      router.replace("/");
    },
    [qc, router],
  );

  if (me.isPending || unauthorized) return <Spinner label="Loading workspace" />;
  if (me.error || !me.data) {
    return (
      <div role="alert" className="mx-auto mt-20 max-w-md text-center text-sm text-muted">
        The API is unreachable. Is the backend running on port 8000?
      </div>
    );
  }
  const role = me.data.role;
  return (
    <SessionContext.Provider
      value={{
        me: me.data,
        canWrite: role !== "viewer",
        canAdmin: role === "admin" || role === "owner",
        signOut,
        switchOrg,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}
