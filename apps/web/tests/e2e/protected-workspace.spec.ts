import { expect, test } from "@playwright/test";

const document = {
  id: "11111111-1111-4111-8111-111111111111",
  filename: "Gulf supplier invoice.pdf",
  status: "needs_review",
  size_bytes: 12000,
  page_count: 2,
  content_type: "application/pdf",
  document_type: "invoice",
  detected_language: "mixed",
  created_at: "2026-07-31T08:00:00Z",
  updated_at: "2026-07-31T08:02:00Z",
};

test("private workspace redirects signed-out users", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/signin$/);
  await expect(page.getByText("Local development adapter")).toBeVisible();
});

test("reviewer opens a private document and sees grounded evidence", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("gulfdocs.development-user", "playwright-reviewer"),
  );
  await page.route("http://localhost:8000/**", async (route) => {
    const url = route.request().url();
    if (url.endsWith("/api/v1/documents"))
      return route.fulfill({ json: [document] });
    if (url.endsWith("/download"))
      return route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: "%PDF-1.4\n%%EOF",
      });
    if (url.endsWith("/extraction"))
      return route.fulfill({
        json: {
          document_id: document.id,
          schema_version: "invoice-v1",
          document_type: "invoice",
          approved_output: null,
          fields: [
            {
              key: "total",
              value: "1,250.00 AED",
              confidence: 0.96,
              citations: [{ page: 1, quote: "Total AED 1,250.00" }],
            },
          ],
          issues: [],
        },
      });
    if (url.endsWith("/questions"))
      return route.fulfill({
        json: [
          {
            question_id: "22222222-2222-4222-8222-222222222222",
            answer: "The total is AED 1,250.00.",
            citations: [{ page: 1, quote: "Total AED 1,250.00" }],
            supported: true,
            model_name: "fake-grounded",
            prompt_version: "qa-v1",
            latency_ms: 18,
            created_at: "2026-07-31T08:04:00Z",
          },
        ],
      });
    if (url.endsWith("/audit"))
      return route.fulfill({
        json: [
          {
            id: "33333333-3333-4333-8333-333333333333",
            event_type: "processing_completed",
            safe_metadata: { status: "needs_review" },
            created_at: "2026-07-31T08:03:00Z",
          },
        ],
      });
    return route.fulfill({ json: document });
  });

  await page.goto("/dashboard");
  await expect(page.getByText(document.filename)).toBeVisible();
  await Promise.all([
    page.waitForURL(`**/documents/${document.id}`),
    page.getByRole("row", { name: new RegExp(document.filename) }).click(),
  ]);
  await expect(page.getByText("1,250.00 AED")).toBeVisible();
  await expect(page.getByText("Page 1 · “Total AED 1,250.00”")).toBeVisible();
  await page.getByRole("tab", { name: "Q&A" }).click();
  await expect(page.getByText("The total is AED 1,250.00.")).toBeVisible();
  await page.getByRole("tab", { name: "Activity" }).click();
  await expect(page.getByText("processing completed")).toBeVisible();
  await page.setViewportSize({ width: 820, height: 1180 });
  const hasTabletOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(hasTabletOverflow).toBe(false);
});
