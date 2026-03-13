import { render, screen } from "@testing-library/react";

import { SummaryCard } from "@/features/summaries/summary-card";

test("renders summary content", () => {
  render(
    <SummaryCard
      summary={{
        document_id: "doc-1",
        status: "ready",
        title: "Guide",
        summary: "Short summary.",
        key_insights: ["Insight A"],
        important_points: ["Point A"],
        topics: [],
        keywords: [],
        generated_at: "2026-03-13T00:00:00Z"
      }}
    />
  );
  expect(screen.getByText(/Short summary/i)).toBeInTheDocument();
});
