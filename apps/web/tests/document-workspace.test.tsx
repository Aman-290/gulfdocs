import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DocumentWorkspace } from "@/components/document-workspace";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    getToken: async () => "dev:reviewer",
    user: { displayName: "reviewer" },
    signOut: vi.fn(),
  }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

const document = {
  id: "doc-1",
  filename: "invoice.pdf",
  status: "needs_review",
  size_bytes: 100,
  page_count: 2,
  content_type: "application/pdf",
  document_type: "invoice",
  detected_language: "en",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};
const extraction = {
  document_id: "doc-1",
  schema_version: "invoice-v1",
  document_type: "invoice",
  approved_output: null,
  fields: [
    {
      key: "total",
      value: "100.00",
      confidence: 0.9,
      citations: [{ page: 1, quote: "Total 100.00" }],
    },
  ],
  issues: [
    {
      code: "total_mismatch",
      severity: "error",
      description: "Total does not match",
      related_fields: ["total"],
      source_page: 1,
      suggested_action: "Verify the total",
      resolved: false,
    },
  ],
};
const answer = {
  question_id: "q1",
  answer: "The total is 100.00.",
  citations: [{ page: 1, quote: "Total 100.00" }],
  supported: true,
  model_name: "fake-grounded",
  prompt_version: "qa-v1",
  latency_ms: 12,
  created_at: "2026-01-01T00:00:00Z",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}
function wrapper(children: React.ReactNode) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

describe("DocumentWorkspace", () => {
  let documentStatus = "needs_review";
  beforeEach(() => {
    documentStatus = "needs_review";
    let questionCreated = false;
    vi.stubGlobal("URL", {
      createObjectURL: () => "blob:pdf",
      revokeObjectURL: vi.fn(),
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/download")) return new Response(new Blob(["pdf"]));
        if (url.endsWith("/extraction"))
          return init?.method === "PATCH"
            ? json(extraction.fields[0])
            : json(extraction);
        if (url.endsWith("/questions")) {
          if (init?.method === "POST") {
            questionCreated = true;
            return json(answer, 201);
          }
          return json(questionCreated ? [answer] : []);
        }
        if (url.endsWith("/audit"))
          return json([
            {
              id: "a1",
              event_type: "processing_completed",
              safe_metadata: { status: "needs_review" },
              created_at: "2026-01-01T00:00:00Z",
            },
          ]);
        if (url.endsWith("/approve"))
          return json({ ...document, status: "approved" });
        if (url.endsWith("/retry")) {
          documentStatus = "queued";
          return json({ ...document, status: documentStatus });
        }
        return json({ ...document, status: documentStatus });
      }),
    );
  });

  it("shows cited fields, validation issues, corrections, Q&A, and audit history", async () => {
    render(wrapper(<DocumentWorkspace documentId="doc-1" />));
    expect(await screen.findByText("Total does not match")).toBeInTheDocument();
    expect(screen.getByText("Page 1 · “Total 100.00”")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /100.00/i }));
    fireEvent.change(screen.getByLabelText("Correct Total"), {
      target: { value: "101.00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Total" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/extraction"),
        expect.objectContaining({ method: "PATCH" }),
      ),
    );

    fireEvent.click(screen.getByRole("tab", { name: "Q&A" }));
    fireEvent.change(screen.getByLabelText("Question"), {
      target: { value: "What is the total?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("The total is 100.00.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Activity" }));
    expect(await screen.findByText("processing completed")).toBeInTheDocument();
    expect(screen.getByText(/needs_review/)).toBeInTheDocument();
  });

  it("offers a retry action for a failed processing run", async () => {
    documentStatus = "failed";
    render(wrapper(<DocumentWorkspace documentId="doc-1" />));
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/retry"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});
