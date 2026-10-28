import { defineConfig, devices } from "@playwright/test";

// Starts the FastAPI backend and the Next.js frontend unless they are already running.
// The backend needs a migrated PostgreSQL database (see README); global setup reloads the demo data.
const CI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  retries: CI ? 1 : 0,
  reporter: CI ? [["list"], ["html", { open: "never" }]] : "list",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure", colorScheme: "dark" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] }, testIgnore: /mobile\.spec/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /mobile\.spec/ },
  ],
  webServer: [
    {
      command: "uv run uvicorn app.main:app --port 8000",
      cwd: "../backend",
      url: "http://localhost:8000/api/healthz",
      reuseExistingServer: !CI,
      timeout: 60_000,
    },
    {
      command: CI ? "npm run build && npm run start" : "npm run dev",
      url: "http://localhost:3000/login",
      reuseExistingServer: !CI,
      timeout: 180_000,
    },
  ],
});
