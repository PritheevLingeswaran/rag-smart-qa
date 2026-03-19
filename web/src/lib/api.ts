const API_BASE = "/api/backend";

interface ApiEnvelopeError {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  const payload = (await response.json().catch(() => ({}))) as ApiEnvelopeError & T;
  if (!response.ok) {
    const message =
      payload.error?.message ||
      (typeof payload === "object" && payload ? JSON.stringify(payload) : response.statusText);
    throw new ApiError(response.status, message, payload);
  }

  return payload as T;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ChatQueryRequest {
  question: string;
  session_id?: string;
  retrieval_mode?:
    | "dense"
    | "bm25"
    | "hybrid_weighted"
    | "hybrid_rrf"
    | "hybrid_rrf_rerank";
  top_k?: number;
}

export interface Citation {
  id: string;
  document_id: string | null;
  chunk_id: string;
  source: string;
  page: number;
  excerpt: string;
  score: number;
  created_at: string;
}

export interface QueryResponse {
  session_id: string;
  answer: string;
  confidence: number;
  refusal: {
    is_refusal: boolean;
    reason: string;
  };
  citations: Citation[];
  sources: Array<{
    chunk_id: string;
    source: string;
    page: number;
    score: number;
    text: string;
  }>;
  timing: {
    total_latency_ms?: number | null;
    retrieval_latency_ms?: number | null;
    rerank_latency_ms?: number | null;
    generation_latency_ms?: number | null;
    embedding_tokens?: number | null;
    embedding_cost_usd?: number | null;
    llm_tokens_in?: number | null;
    llm_tokens_out?: number | null;
    llm_cost_usd?: number | null;
  };
}

export async function postQuery(body: ChatQueryRequest): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/api/v1/chat/query", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export interface ChatSession {
  id: string;
  owner_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionListResponse {
  sessions: ChatSession[];
}

export async function getChatSessions(): Promise<ChatSession[]> {
  const response = await apiFetch<ChatSessionListResponse>("/api/v1/chat/sessions");
  return response.sessions;
}

export interface Document {
  id: string;
  filename: string;
  stored_path: string;
  file_type: string;
  size_bytes: number;
  pages: number;
  chunks_created: number;
  upload_time: string;
  indexing_status: string;
  summary_status: string;
  collection_name: string | null;
  error_message: string | null;
  metadata: Record<string, unknown>;
}

export interface DocumentDetail extends Document {
  preview: Array<{
    page: number;
    text: string;
  }>;
  chunks: Array<{
    chunk_id: string;
    page: number;
    text: string;
    metadata: Record<string, unknown>;
  }>;
  summary: DocumentSummary | null;
}

export interface DocumentSummary {
  document_id: string;
  status: string;
  title: string | null;
  summary: string | null;
  key_insights: string[];
  important_points: string[];
  topics: string[];
  keywords: string[];
  error_message: string | null;
  method: string | null;
  generated_at: string | null;
}

export interface DocumentListResponse {
  documents: Document[];
}

export interface UploadResponse {
  documents: Array<{
    id: string;
    filename: string;
    stored_path: string;
    file_type: string;
    size_bytes: number;
    indexing_status: string;
    summary_status: string;
    upload_time: string;
  }>;
}

export async function getDocuments(): Promise<Document[]> {
  const response = await apiFetch<DocumentListResponse>("/api/v1/documents");
  return response.documents;
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  return apiFetch<DocumentDetail>(`/api/v1/documents/${id}`);
}

export async function getDocumentSummary(id: string): Promise<DocumentSummary> {
  return apiFetch<DocumentSummary>(`/api/v1/documents/${id}/summary`);
}

export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("files", file);

  const response = await apiFetch<UploadResponse>("/api/v1/documents/upload", {
    method: "POST",
    body: formData,
  });
  return response.documents[0];
}

export async function deleteDocument(id: string): Promise<void> {
  await apiFetch(`/api/v1/documents/${id}`, { method: "DELETE" });
}

export interface DashboardResponse {
  stats: {
    total_documents: number;
    total_chunks: number;
    total_sessions: number;
    indexing_status: Record<string, number>;
  };
  recent_documents: Document[];
  recent_sessions: ChatSession[];
}

export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>("/api/v1/dashboard");
}

export interface UserSettings {
  app_name: string;
  environment: string;
  default_generation_model: string;
  default_embedding_model: string;
  vector_store_provider: string;
  auth_enabled: boolean;
  auth_provider: string;
  summaries_enabled: boolean;
  default_retrieval_mode: string;
}

export async function getSettings(): Promise<UserSettings> {
  return apiFetch<UserSettings>("/api/v1/settings");
}
