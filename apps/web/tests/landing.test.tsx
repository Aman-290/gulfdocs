import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "@/app/page";

describe("public landing page", () => {
  it("presents the product and recruiter demo without exaggerated claims", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Business documents, made inspectable.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /try public demo/i }),
    ).toHaveAttribute("href", "/demo");
    expect(
      screen.getByText(/anonymous uploads are disabled/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText("فاتورة تجريبية · الصفحة ١").closest("div"),
    ).toHaveAttribute("dir", "rtl");
  });
});
