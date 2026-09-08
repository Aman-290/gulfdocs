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

const metrics = {
  generated_at: "2026-07-31T08:03:00Z",
  usage: {
    usage_date: "2026-07-31",
    uploads_used: 1,
    uploads_limit: 5,
    questions_used: 1,
    questions_limit: 20,
    generated_tokens: 20,
  },
  quality: {
    total_documents: 1,
    failed_documents: 0,
    needs_review_documents: 1,
    approved_documents: 0,
    failure_rate: 0,
    needs_review_rate: 1,
    average_processing_ms: 120,
    median_processing_ms: 120,
    p95_processing_ms: 120,
  },
  daily_tokens: [],
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
    if (url.endsWith("/metrics/summary"))
      return route.fulfill({ json: metrics });
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
    () => globalThis.document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(hasTabletOverflow).toBe(false);
});

test("reviewer uploads, observes processing, corrects, approves, and verifies isolation", async ({
  page,
}) => {
  const fixture = "../../data/synthetic/en-invoice-table.pdf";
  let uploaded = false;
  let listAfterUpload = 0;
  let corrected = false;
  let approved = false;
  await page.addInitScript(() =>
    localStorage.setItem("gulfdocs.development-user", "journey-reviewer"),
  );
  await page.route("http://localhost:8000/**", async (route) => {
    const request = route.request();
    const url = request.url();
    if (url.endsWith("/metrics/summary"))
      return route.fulfill({ json: metrics });
    if (url.endsWith("/signed-upload")) {
      return route.fulfill({
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "PUT, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }
    if (request.headers()["authorization"] === "Bearer dev:bob") {
      return route.fulfill({
        status: 404,
        json: { detail: "Document was not found" },
      });
    }
    if (url.endsWith("/uploads/presign")) {
      return route.fulfill({
        status: 201,
        json: {
          document_id: document.id,
          upload_url: "http://localhost:8000/signed-upload",
          method: "PUT",
          expires_at: "2026-07-31T09:00:00Z",
          required_headers: { "Content-Type": "application/pdf" },
        },
      });
    }
    if (url.endsWith("/uploads/complete")) {
      uploaded = true;
      return route.fulfill({ json: { ...document, status: "queued" } });
    }
    if (url.endsWith("/api/v1/documents")) {
      if (!uploaded) return route.fulfill({ json: [] });
      listAfterUpload += 1;
      return route.fulfill({
        json: [
          {
            ...document,
            status:
              listAfterUpload === 1
                ? "processing"
                : approved
                  ? "approved"
                  : "needs_review",
          },
        ],
      });
    }
    if (url.endsWith("/download"))
      return route.fulfill({
        contentType: "application/pdf",
        body: "%PDF-1.4\n%%EOF",
      });
    if (url.endsWith("/extraction")) {
      if (request.method() === "PATCH") {
        corrected = true;
        return route.fulfill({
          json: {
            key: "total",
            value: "682.50",
            confidence: 1,
            citations: [{ page: 1, quote: "Total: 682.50" }],
          },
        });
      }
      return route.fulfill({
        json: {
          document_id: document.id,
          schema_version: "invoice-v1",
          document_type: "invoice",
          approved_output: approved ? { total: "682.50" } : null,
          fields: [
            {
              key: "total",
              value: corrected ? "682.50" : "680.00",
              confidence: corrected ? 1 : 0.55,
              citations: [{ page: 1, quote: "Total: 682.50" }],
            },
          ],
          issues: corrected
            ? []
            : [
                {
                  code: "total_mismatch",
                  severity: "error",
                  description: "Total requires review",
                  related_fields: ["total"],
                  source_page: 1,
                  suggested_action: "Correct the total",
                  resolved: false,
                },
              ],
        },
      });
    }
    if (url.endsWith("/approve")) {
      approved = true;
      return route.fulfill({ json: { ...document, status: "approved" } });
    }
    if (url.endsWith("/questions")) return route.fulfill({ json: [] });
    if (url.endsWith("/audit"))
      return route.fulfill({
        json: [
          {
            id: "44444444-4444-4444-8444-444444444444",
            event_type: approved ? "document_approved" : "upload_completed",
            safe_metadata: {},
            created_at: "2026-07-31T08:10:00Z",
          },
        ],
      });
    return route.fulfill({
      json: { ...document, status: approved ? "approved" : "needs_review" },
    });
  });

  await page.goto("/dashboard");
  await expect(page.getByText("No documents yet")).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles(fixture);
  await expect(
    page.getByRole("row", { name: /Gulf supplier invoice\.pdf Processing/ }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("row", { name: /Gulf supplier invoice\.pdf Needs review/ }),
  ).toBeVisible();
  await page.getByRole("row", { name: new RegExp(document.filename) }).click();
  await expect(page.getByText("Total requires review")).toBeVisible();
  await page.getByRole("button", { name: /680.00/ }).click();
  await page.getByLabel("Correct Total").fill("682.50");
  await page.getByRole("button", { name: "Save Total" }).click();
  await expect(page.getByText("No unresolved validation issues")).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("approved", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Activity" }).click();
  await expect(page.getByText("document approved")).toBeVisible();
  const unauthorizedStatus = await page.evaluate(async (documentId) => {
    const response = await fetch(
      `http://localhost:8000/api/v1/documents/${documentId}`,
      { headers: { Authorization: "Bearer dev:bob" } },
    );
    return response.status;
  }, document.id);
  expect(unauthorizedStatus).toBe(404);
});
