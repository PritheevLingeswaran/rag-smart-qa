import { render, screen } from "@testing-library/react";

import { DocumentsTable } from "@/features/documents/documents-table";

test("renders document rows", () => {
  render(
    <DocumentsTable
      documents={[
        {
          id: "doc-1",
          filename: "Guide.pdf",
          stored_path: "/tmp/guide.pdf",
          file_type: "pdf",
          size_bytes: 10,
          pages: 2,
          chunks_created: 5,
          upload_time: "2026-03-13T00:00:00Z",
          indexing_status: "ready",
          summary_status: "ready",
          collection_name: null,
          error_message: null,
          metadata: {}
        }
      ]}
    />
  );
  expect(screen.getByText(/Guide.pdf/i)).toBeInTheDocument();
});
