import { expect, test } from "@playwright/test";

test("a recruiter can inspect the public synthetic demo", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /try public demo/i }).click();
  await expect(page).toHaveURL(/\/demo$/);
  await expect(
    page.getByRole("heading", { name: /inspect the evidence/i }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Does the printed total match the line items?",
    })
    .click();
  await expect(page.getByText(/printed total is AED 12,862.50/i)).toBeVisible();
  await expect(page.getByRole("link", { name: "Page 1" })).toBeVisible();
});

test("Arabic RTL experience fits a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/ar");
  const main = page.locator("main[lang='ar']");
  await expect(main).toHaveAttribute("dir", "rtl");
  await expect(main.getByRole("heading", { level: 1 })).toBeVisible();
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
});
