import { API_BASE_URL } from "@/lib/config";
import type {
  ChatQueryResponse,
  ChatSessionDetail,
  ChatSession,
  DashboardPayload,
  DocumentDetail,
  DocumentItem,
  SettingsPayload,
  SummaryPayload
} from "@/types/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => request<DashboardPayload>("/api/dashboard"),
  documents: () => request<{ documents: DocumentItem[] }>("/api/documents"),
  document: (id: string) => request<DocumentDetail>(`/api/documents/${id}`),
  documentSummary: (id: string) => request<SummaryPayload>(`/api/documents/${id}/summary`),
  deleteDocument: (id: string) =>
    request<DocumentItem>(`/api/documents/${id}`, { method: "DELETE" }),
  reindexDocument: (id: string) =>
    request<{ document: DocumentDetail }>(`/api/documents/${id}/reindex`, { method: "POST" }),
  chatSessions: () => request<{ sessions: ChatSession[] }>("/api/chat/sessions"),
  chatSession: (id: string) => request<ChatSessionDetail>(`/api/chat/sessions/${id}`),
  deleteChatSession: (id: string) =>
    request<{ deleted: boolean }>(`/api/chat/sessions/${id}`, { method: "DELETE" }),
  chatQuery: (body: {
    question: string;
    session_id?: string;
    retrieval_mode: string;
    top_k: number;
  }) =>
    request<ChatQueryResponse>("/api/chat/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }),
  settings: () => request<SettingsPayload>("/api/settings")
};
