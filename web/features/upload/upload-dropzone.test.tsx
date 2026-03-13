import { render, screen } from "@testing-library/react";

import { UploadDropzone } from "@/features/upload/upload-dropzone";

test("renders upload prompt", () => {
  render(<UploadDropzone />);
  expect(screen.getByText(/Drop files to ingest and index/i)).toBeInTheDocument();
});
