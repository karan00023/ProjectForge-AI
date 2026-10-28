import { expect, test } from "@playwright/test";
import { expectAccessible, loginAs, projectId } from "./helpers";

test.describe("Phase 1 journeys", () => {
  test("command center shows explainable portfolio health with drill-down to evidence", async ({ page }) => {
    await loginAs(page, "Priya Raman");
    const dpm = page.locator("article", { hasText: "Enterprise Data Platform Migration" });
    await expect(dpm.getByText("At risk")).toBeVisible();
    await dpm.getByRole("button", { name: /Why red\?/ }).click();
    await expect(dpm.getByText(/work items? blocked, 2 of them milestone deliverables/)).toBeVisible();
    // Evidence chips link to the records that triggered the rule.
    await dpm.getByRole("link", { name: "DPM-32" }).first().click();
    const drawer = page.getByRole("dialog", { name: "Work item details" });
    await expect(drawer.getByText("Enable CDC on ORDERS_DB", { exact: false }).first()).toBeVisible();
    await expect(drawer.getByText("Acceptance criteria (3)")).toBeVisible();
  });

  test("create a project from a template, add work, and it persists", async ({ page }) => {
    await loginAs(page, "Priya Raman");
    await page.goto("/projects?new=1");
    const dialog = page.getByRole("dialog", { name: "Create project" });
    const key = `E${Date.now().toString(36).slice(-5).toUpperCase()}`;
    await dialog.getByLabel("Name").fill("Warehouse telemetry migration");
    await dialog.getByLabel(/^Key/).fill(key);
    await dialog.getByLabel(/^Start from/).selectOption("data-migration");
    await expect(dialog.getByText("CDC ingestion (Bronze)")).toBeVisible();
    await dialog.getByRole("button", { name: "Create project" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Warehouse telemetry migration" })).toBeVisible();

    await page.getByRole("link", { name: "Backlog" }).click();
    await expect(page.getByText(`${key}-1`)).toBeVisible();
    await page.getByRole("button", { name: "New item" }).click();
    const create = page.getByRole("dialog", { name: /New work item/ });
    await create.getByLabel("Title").fill("Profile sensor event tables");
    await create.getByLabel("Story points").fill("5");
    await create.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("button", { name: /Profile sensor event tables/ })).toBeVisible();

    await page.reload();
    await expect(page.getByRole("button", { name: /Profile sensor event tables/ })).toBeVisible();
    await page.getByRole("link", { name: "Timeline" }).click();
    await expect(page.getByRole("button", { name: /Environments ready/ })).toBeVisible();
  });

  test("moving a card on the board updates status and the audit trail", async ({ page }) => {
    await loginAs(page, "Priya Raman");
    const pid = await projectId(page, "TWS");
    await page.goto(`/projects/${pid}/board`);
    const todo = page.getByRole("region", { name: "To do column" });
    const card = todo.getByRole("button", { name: /Remove member and revoke access/ });
    await expect(card).toBeVisible();
    await card.dragTo(page.getByRole("region", { name: "In progress column" }));
    const inProgress = page.getByRole("region", { name: "In progress column" });
    await expect(inProgress.getByRole("button", { name: /Remove member and revoke access/ })).toBeVisible();
    await inProgress.getByRole("button", { name: /Remove member and revoke access/ }).click();
    const drawer = page.getByRole("dialog", { name: "Work item details" });
    await expect(drawer.getByLabel("Status")).toHaveValue("in_progress");
    await expect(drawer.getByText(/Moved TWS-\d+ from todo to in_progress/)).toBeVisible();
  });

  test("logging a high risk turns a project red, with the risk as evidence", async ({ page }) => {
    await loginAs(page, "Marcus Bell");
    const pid = await projectId(page, "TWS");
    await page.goto(`/projects/${pid}/raid`);
    await page.getByRole("button", { name: "Log RAID item" }).click();
    const dialog = page.getByRole("dialog", { name: /Log risk/ });
    await dialog.getByLabel("Title").fill("Key customer pilots slip past beta");
    await dialog.getByLabel("Probability (1–5)").selectOption("5");
    await dialog.getByLabel("Impact (1–5)").selectOption("4");
    await expect(dialog.getByText("Score = probability × impact = 20")).toBeVisible();
    await dialog.getByRole("button", { name: "Log item" }).click();
    await expect(page.getByText("Key customer pilots slip past beta")).toBeVisible();
    await page.getByRole("link", { name: "Overview" }).click();
    await expect(page.getByText(/open risk scored ≥ 15/)).toBeVisible();
  });

  test("decisions record who accepted them", async ({ page }) => {
    await loginAs(page, "Sofia Okafor");
    const pid = await projectId(page, "DPM");
    await page.goto(`/projects/${pid}/decisions`);
    const proposed = page.locator("li", { hasText: "Reconciliation tolerance of 0.01%" });
    await proposed.getByRole("button", { name: "Accept" }).click();
    await expect(proposed.getByText(/Accepted by Sofia Okafor/)).toBeVisible();
  });

  test("command palette searches across records", async ({ page }) => {
    await loginAs(page, "Priya Raman");
    await page.keyboard.press("Control+k");
    await page.getByRole("combobox", { name: "Search or run a command" }).fill("billing accuracy");
    await page.getByRole("option", { name: /RAG-R1/ }).click();
    await expect(page).toHaveURL(/\/raid#raid-/);
  });
});

test.describe("permissions and isolation", () => {
  test("a viewer can read but not change anything", async ({ page }) => {
    await loginAs(page, "Elena Morales");
    await page.goto("/projects");
    await expect(page.getByRole("button", { name: "New project" })).toHaveCount(0);
    const pid = await projectId(page, "DPM");
    await page.goto(`/projects/${pid}/board`);
    await expect(page.getByText("Read-only: your role cannot change work items.")).toBeVisible();
    await page.getByRole("button", { name: /DPM-35/ }).click();
    await expect(page.getByRole("dialog", { name: "Work item details" }).getByLabel("Status")).toBeDisabled();
  });

  test("another tenant cannot see Meridian's projects", async ({ page }) => {
    await loginAs(page, "Priya Raman");
    const dpm = await projectId(page, "DPM");
    await page.getByRole("button", { name: "Sign out" }).first().click();
    await loginAs(page, "Noah Kim");
    await expect(page.getByText("Clinical Trials Portal").first()).toBeVisible();
    await expect(page.getByText("Enterprise Data Platform Migration")).toHaveCount(0);
    await page.goto(`/projects/${dpm}`);
    await expect(page.getByText("This project does not exist or you do not have access to it.")).toBeVisible();
  });
});

test.describe("accessibility", () => {
  test("core screens have no serious axe violations", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: /Priya Raman/ })).toBeVisible();
    await expectAccessible(page);
    await loginAs(page, "Priya Raman");
    await expectAccessible(page);
    const pid = await projectId(page, "DPM");
    for (const section of ["", "/board", "/backlog", "/timeline", "/raid", "/decisions"]) {
      await page.goto(`/projects/${pid}${section}`);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await page.waitForLoadState("networkidle");
      await expectAccessible(page);
    }
  });

  test("light theme passes contrast checks too", async ({ browser }) => {
    const ctx = await browser.newContext({ colorScheme: "light" });
    const page = await ctx.newPage();
    await loginAs(page, "Priya Raman");
    await page.waitForLoadState("networkidle");
    await expectAccessible(page);
    const pid = await projectId(page, "RAG");
    await page.goto(`/projects/${pid}/raid`);
    await page.waitForLoadState("networkidle");
    await expectAccessible(page);
    await ctx.close();
  });
});
