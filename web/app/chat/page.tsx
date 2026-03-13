import { PageHeader } from "@/components/page-header";
import { ChatPanel } from "@/features/chat/chat-panel";

export default function ChatPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Chat"
        title="Grounded multi-turn Q&A"
        description="Switch retrieval modes, keep follow-ups in one session, and inspect exact source passages on the right."
      />
      <ChatPanel />
    </div>
  );
}
