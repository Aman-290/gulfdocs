import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { DemoQuestionPanel } from "@/components/demo-question-panel";
import { publicDemo } from "@/lib/public-demo";

describe("DemoQuestionPanel", () => {
  it("switches between grounded and unsupported precomputed answers", async () => {
    const user = userEvent.setup();
    render(<DemoQuestionPanel questions={publicDemo.questions} />);
    expect(screen.getByText(/due within 30 days/i)).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "What is the delivery address?" }),
    );
    expect(
      screen.getByText(/could not find enough evidence/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Page 1" })).toHaveAttribute(
      "href",
      "#page-1",
    );
  });
});
