import { expect, test } from "@playwright/test";
import { loginAs, projectId } from "./helpers";

test("mobile: review status and open a work item", async ({ page }) => {
  await loginAs(page, "Priya Raman");
  const nav = page.getByRole("navigation", { name: "Main" }).last();
  await expect(nav.getByRole("link", { name: "Projects" })).toBeVisible();
  await expect(page.getByText("Portfolio health")).toBeVisible();
  const pid = await projectId(page, "DPM");
  await page.goto(`/projects/${pid}/board`);
  await page.getByRole("button", { name: /DPM-35/ }).click();
  const drawer = page.getByRole("dialog", { name: "Work item details" });
  await expect(drawer.getByLabel("Status")).toBeVisible();
  // No horizontal page overflow at phone width.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
