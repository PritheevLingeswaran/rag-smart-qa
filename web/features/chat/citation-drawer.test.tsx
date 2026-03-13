import { fireEvent, render, screen } from "@testing-library/react";

import { CitationDrawer } from "@/features/chat/citation-drawer";

test("shows clicked citation content", () => {
  render(
    <CitationDrawer
      citation={{
        id: "c1",
        chunk_id: "chunk-1",
        source: "manual.pdf",
        page: 2,
        excerpt: "Important cited passage",
        score: 0.9,
        created_at: "2026-03-13T00:00:00Z",
        document_id: "doc-1"
      }}
    />
  );
  expect(screen.getByText(/Important cited passage/i)).toBeInTheDocument();
});
