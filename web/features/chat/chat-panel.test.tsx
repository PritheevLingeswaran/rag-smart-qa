import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ChatPanel } from "@/features/chat/chat-panel";

test("renders chat composer", () => {
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <ChatPanel />
    </QueryClientProvider>
  );
  expect(screen.getByPlaceholderText(/Ask a question about the uploaded documents/i)).toBeInTheDocument();
});
