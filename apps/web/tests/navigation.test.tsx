import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Footer } from "@/components/footer";
import { SiteHeader } from "@/components/site-header";

describe("public navigation", () => {
  it("exposes demo, architecture, evaluation, sign-in, and Arabic routes", () => {
    render(
      <>
        <SiteHeader />
        <Footer />
      </>,
    );

    expect(screen.getByRole("link", { name: "GulfDocs home" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getAllByRole("link", { name: "Architecture" })).toHaveLength(
      2,
    );
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/signin",
    );
    expect(screen.getByRole("link", { name: "العربية" })).toHaveAttribute(
      "href",
      "/ar",
    );
    expect(
      screen.getByText(/no compliance certification claims/i),
    ).toBeInTheDocument();
  });
});
