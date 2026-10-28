"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError } from "@/lib/api";

type ThemePref = "light" | "dark" | "system";
const THEME_KEY = "pf.theme";

const ThemeContext = createContext<{ theme: ThemePref; resolved: "light" | "dark"; setTheme: (t: ThemePref) => void }>({
  theme: "system",
  resolved: "dark",
  setTheme: () => {},
});

export const useTheme = () => useContext(ThemeContext);

function resolve(pref: ThemePref): "light" | "dark" {
  if (pref !== "system") return pref;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function readPref(): ThemePref {
  try {
    const v = window.localStorage.getItem(THEME_KEY);
    return v === "light" || v === "dark" || v === "system" ? v : "system";
  } catch {
    return "system";
  }
}

function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemePref>("system");
  const [resolved, setResolved] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const pref = readPref();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync from storage after hydration
    setThemeState(pref);
    setResolved(resolve(pref));
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => {
      if (readPref() === "system") {
        const r = resolve("system");
        document.documentElement.dataset.theme = r;
        setResolved(r);
      }
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const setTheme = useCallback((t: ThemePref) => {
    try {
      window.localStorage.setItem(THEME_KEY, t);
    } catch {
      /* preference is per-session only */
    }
    const r = resolve(t);
    document.documentElement.dataset.theme = r;
    setThemeState(t);
    setResolved(r);
  }, []);

  return <ThemeContext.Provider value={{ theme, resolved, setTheme }}>{children}</ThemeContext.Provider>;
}

/** Runs before first paint (inlined in <head>) so the page never flashes the wrong theme. */
export const themeBootScript = `(function(){try{var p=localStorage.getItem("${THEME_KEY}")||"system";var r=p==="system"?(matchMedia("(prefers-color-scheme: light)").matches?"light":"dark"):p;document.documentElement.dataset.theme=r}catch(e){document.documentElement.dataset.theme="dark"}})()`;

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            refetchOnWindowFocus: true,
            retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
}
