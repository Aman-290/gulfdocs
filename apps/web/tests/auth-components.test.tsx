import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "@/components/protected-route";
import { SignInForm } from "@/components/sign-in-form";

const mocks = vi.hoisted(() => ({
  auth: {
    user: null as { displayName: string } | null,
    loading: false,
    firebaseConfigured: false,
    signInLocal: vi.fn(),
    signInGoogle: vi.fn(),
    signInEmail: vi.fn(),
    signOut: vi.fn(),
    getToken: vi.fn(),
  },
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ useAuth: () => mocks.auth }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, push: mocks.push }),
}));

describe("authentication components", () => {
  beforeEach(() => {
    mocks.auth.user = null;
    mocks.auth.loading = false;
    mocks.auth.firebaseConfigured = false;
    vi.clearAllMocks();
  });

  it("redirects a signed-out protected route", async () => {
    render(
      <ProtectedRoute>
        <p>Private content</p>
      </ProtectedRoute>,
    );
    expect(screen.queryByText("Private content")).not.toBeInTheDocument();
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/signin"));
  });

  it("uses the clearly labelled local adapter outside production", async () => {
    render(<SignInForm />);
    expect(screen.getByText("Local development adapter")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Test identity"), {
      target: { value: "qa-reviewer" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Enter local workspace" }),
    );
    await waitFor(() =>
      expect(mocks.auth.signInLocal).toHaveBeenCalledWith("qa-reviewer"),
    );
    expect(mocks.push).toHaveBeenCalledWith("/dashboard");
  });

  it("renders private content for an authenticated reviewer", () => {
    mocks.auth.user = { displayName: "reviewer" };
    render(
      <ProtectedRoute>
        <p>Private content</p>
      </ProtectedRoute>,
    );
    expect(screen.getByText("Private content")).toBeInTheDocument();
  });
});
