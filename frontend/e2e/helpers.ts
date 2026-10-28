import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export async function loginAs(page: Page, name: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: new RegExp(name) }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(name.split(" ")[0]!, { timeout: 30_000 });
}

export async function projectId(page: Page, key: string): Promise<string> {
  return page.evaluate(async (k) => {
    const res = await fetch("/api/projects");
    const list: { id: string; key: string }[] = await res.json();
    return list.find((p) => p.key === k)!.id;
  }, key);
}

/** Fails on serious or critical WCAG 2.1 A/AA violations. */
export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(
    blocking.map((v) => `${v.id}: ${v.help} (${v.nodes.length}) e.g. ${v.nodes[0]?.target.join(" ")}`),
  ).toEqual([]);
}
