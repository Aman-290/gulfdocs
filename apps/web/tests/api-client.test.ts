import { beforeEach, describe, expect, it, vi } from "vitest";
import { GulfDocsApi } from "@/lib/api-client";

const document = {
  id: "doc-1",
  filename: "invoice.pdf",
  status: "ready",
  size_bytes: 20,
  page_count: 1,
  content_type: "application/pdf",
  document_type: "invoice",
  detected_language: "en",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("GulfDocsApi", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("calls every authenticated document operation", async () => {
    const fetcher =
      vi.fn<
        (input: string | URL | Request, init?: RequestInit) => Promise<Response>
      >();
    fetcher.mockImplementation(async (input: string | URL | Request) => {
      const url = String(input);
      if (url.endsWith("/download"))
        return new Response(new Blob(["pdf"]), { status: 200 });
      if (url.endsWith("/extraction"))
        return json({ document_id: "doc-1", fields: [], issues: [] });
      if (url.endsWith("/questions")) return json([]);
      if (url.endsWith("/audit")) return json([]);
      if (url.endsWith("/documents")) return json([document]);
      return json(document);
    });
    vi.stubGlobal("fetch", fetcher);
    const api = new GulfDocsApi(async () => "dev:reviewer");

    expect(await api.listDocuments()).toHaveLength(1);
    expect((await api.getDocument("doc-1")).filename).toBe("invoice.pdf");
    await api.getExtraction("doc-1");
    await api.getQuestions("doc-1");
    await api.getAudit("doc-1");
    expect((await api.download("doc-1")).size).toBeGreaterThan(0);
    await api.correctField("doc-1", "total", "100", "verified");
    await api.approve("doc-1", "looks good");
    await api.ask("doc-1", "What is the total?");
    await api.retry("doc-1");
    expect(fetcher).toHaveBeenCalledTimes(10);
    expect(fetcher.mock.calls.every((call) => call[1]?.headers)).toBe(true);
  });

  it("performs the direct signed upload handshake", async () => {
    const progress: number[] = [];
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        json(
          {
            document_id: "doc-1",
            upload_url: "https://signed.invalid/upload",
            required_headers: { "Content-Type": "application/pdf" },
          },
          201,
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(json(document));
    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal("crypto", { randomUUID: () => "idempotency-key-123" });
    const api = new GulfDocsApi(async () => "dev:reviewer");
    const result = await api.upload(
      new File(["%PDF-1.7"], "invoice.pdf", { type: "application/pdf" }),
      (value) => progress.push(value),
    );
    expect(result.id).toBe("doc-1");
    expect(progress).toEqual([30, 75, 100]);
    expect(fetcher.mock.calls[1][0]).toBe("https://signed.invalid/upload");
  });

  it("returns safe API errors and rejects missing sessions", async () => {
    const signedOut = new GulfDocsApi(async () => null);
    await expect(signedOut.listDocuments()).rejects.toMatchObject({
      status: 401,
    });
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          json({ detail: "Daily limit reached", request_id: "req-1" }, 429),
        ),
    );
    const api = new GulfDocsApi(async () => "dev:reviewer");
    await expect(api.listDocuments()).rejects.toEqual(
      expect.objectContaining({
        message: "Daily limit reached",
        status: 429,
        requestId: "req-1",
      }),
    );
  });
});
