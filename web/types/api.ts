export type DocumentItem = {
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
  collection_name?: string | null;
  error_message?: string | null;
  metadata: Record<string, unknown>;
};

export type DocumentDetail = DocumentItem & {
  preview: Array<{ page: number; text: string }>;
  chunks: Array<{ chunk_id: string; page: number; text: string; metadata: Record<string, unknown> }>;
  summary?: SummaryPayload | null;
};

export type SummaryPayload = {
  document_id: string;
  status: string;
  title?: string | null;
  summary?: string | null;
  key_insights: string[];
  important_points: string[];
  topics: string[];
  keywords: string[];
  error_message?: string | null;
  method?: string | null;
  generated_at?: string | null;
};

export type Citation = {
  id: string;
  document_id?: string | null;
  chunk_id: string;
  source: string;
  page: number;
  excerpt: string;
  score: number;
  created_at: string;
};

export type ChatMessage = {
  id: string;
  session_id: string;
  role: string;
  content: string;
  confidence?: number | null;
  refusal?: boolean;
  latency_ms?: number | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type ChatSession = {
  id: string;
  owner_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatSessionDetail = ChatSession & {
  messages: ChatMessage[];
};

export type ChatQueryResponse = {
  session_id: string;
  answer: string;
  confidence: number;
  refusal: { is_refusal: boolean; reason: string };
  citations: Citation[];
  sources: Array<{
    chunk_id: string;
    source: string;
    page: number;
    score: number;
    text: string;
  }>;
  timing: Record<string, unknown>;
};

export type DashboardPayload = {
  stats: {
    total_documents: number;
    total_chunks: number;
    total_sessions: number;
    indexing_status: Record<string, number>;
  };
  recent_documents: DocumentItem[];
  recent_sessions: ChatSession[];
};

export type SettingsPayload = {
  app_name: string;
  environment: string;
  default_generation_model: string;
  default_embedding_model: string;
  vector_store_provider: string;
  auth_enabled: boolean;
  auth_provider: string;
  summaries_enabled: boolean;
  default_retrieval_mode: string;
};
