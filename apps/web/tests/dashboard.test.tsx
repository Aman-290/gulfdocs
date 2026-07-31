import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "@/components/dashboard";

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

const records = [
  {
    id: "doc-1",
    filename: "Arabic invoice.pdf",
    status: "needs_review",
    size_bytes: 12000,
    page_count: 2,
    content_type: "application/pdf",
    document_type: "invoice",
    detected_language: "ar",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
  },
  {
    id: "doc-2",
    filename: "Signed contract.pdf",
    status: "approved",
    size_bytes: 24000,
    page_count: 5,
    content_type: "application/pdf",
    document_type: "contract",
    detected_language: "en",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-03T00:00:00Z",
  },
];

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

describe("Dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify(records), { status: 200 }),
        ),
    );
  });

  it("renders workspace metrics and combines search and structured filters", async () => {
    render(wrapper(<Dashboard />));
    expect(await screen.findByText("Arabic invoice.pdf")).toBeInTheDocument();
    expect(screen.getByText("Signed contract.pdf")).toBeInTheDocument();
    expect(
      screen.getByText("Need review").closest("article"),
    ).toHaveTextContent("1");
    fireEvent.change(screen.getByPlaceholderText("Search filename"), {
      target: { value: "contract" },
    });
    expect(screen.queryByText("Arabic invoice.pdf")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search documents"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("Language"), {
      target: { value: "ar" },
    });
    expect(screen.getByText("Arabic invoice.pdf")).toBeInTheDocument();
    expect(screen.queryByText("Signed contract.pdf")).not.toBeInTheDocument();
  });

  it("rejects a non-PDF before upload", async () => {
    const { container } = render(wrapper(<Dashboard />));
    await screen.findByText("Arabic invoice.pdf");
    const input = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(input, {
      target: {
        files: [new File(["text"], "notes.txt", { type: "text/plain" })],
      },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Choose a PDF file",
    );
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  });
});
