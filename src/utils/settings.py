from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PathsConfig(BaseModel):
    data_dir: str = "data"
    raw_dir: str = "data/raw/documents"
    uploads_dir: str = "data/raw/documents/uploads"
    processed_dir: str = "data/processed"
    chunks_dir: str = "data/processed/chunks"
    metadata_dir: str = "data/processed/metadata"
    indexes_dir: str = "data/processed/indexes"
    app_db_path: str = "data/processed/metadata/app.db"


class IngestionConfig(BaseModel):
    supported_extensions: list[str] = Field(
        default_factory=lambda: [".pdf", ".txt", ".md", ".html", ".htm"]
    )
    deduplicate_documents: bool = True
    max_document_chars: int = 500_000
    max_upload_size_mb: int = 25


class BM25Config(BaseModel):
    lowercase: bool = True
    strip_punctuation: bool = True
    remove_stopwords: bool = True
    stemming: bool = False
    min_token_length: int = 2


class RetrievalCacheConfig(BaseModel):
    enabled: bool = True
    max_entries: int = 256


class CleaningConfig(BaseModel):
    normalize_whitespace: bool = True
    drop_null_bytes: bool = True


class ChunkingConfig(BaseModel):
    strategy: Literal["token", "char"] = "token"
    chunk_size: int = 800
    chunk_overlap: int = 120
    max_chars_fallback: int = 4000


class PreprocessingConfig(BaseModel):
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)


class OpenAIEmbeddingsConfig(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    organization: str | None = None
    request_timeout_s: float = 30.0
    max_retries: int = 3
    usd_per_1k_tokens: float = 0.0


class SentenceTransformersConfig(BaseModel):
    model_name: str = "all-MiniLM-L6-v2"
    local_files_only: bool = False


class EmbeddingsConfig(BaseModel):
    provider: Literal["openai", "sentence_transformers"] = "openai"
    model: str = "text-embedding-3-small"
    batch_size: int = 64
    openai: OpenAIEmbeddingsConfig = Field(default_factory=OpenAIEmbeddingsConfig)
    sentence_transformers: SentenceTransformersConfig = Field(
        default_factory=SentenceTransformersConfig
    )


class FaissConfig(BaseModel):
    metric: Literal["cosine", "l2"] = "cosine"
    normalize: bool = True


class ChromaConfig(BaseModel):
    persist_dir: str = "data/processed/indexes/chroma"
    collection_name: str = "rag-smart-qa"


class PineconeConfig(BaseModel):
    api_key: str | None = None
    environment: str | None = None
    index_name: str = "rag-smart-qa"


class VectorStoreConfig(BaseModel):
    provider: Literal["chroma", "faiss", "pinecone"] = "chroma"
    top_k: int = 8
    faiss: FaissConfig = Field(default_factory=FaissConfig)
    chroma: ChromaConfig = Field(default_factory=ChromaConfig)
    pinecone: PineconeConfig = Field(default_factory=PineconeConfig)


class QueryRewriteConfig(BaseModel):
    enabled: bool = True
    model: str = "gpt-4o-mini"


class HybridConfig(BaseModel):
    enabled: bool = False
    fusion_method: Literal["weighted", "rrf"] = "weighted"
    # Number of BM25 candidates to retrieve from the *full corpus*.
    bm25_k: int = 200
    # Number of dense candidates to retrieve (typically >= top_k).
    dense_k: int = 40
    # Fusion weight: final_score = dense_weight * dense + (1-dense_weight) * bm25
    dense_weight: float = 0.65
    rrf_k: int = 60
    min_dense_score: float = 0.0
    min_sparse_score: float = 0.0


class RerankConfig(BaseModel):
    enabled: bool = False
    provider: Literal["lexical", "cross_encoder"] = "lexical"
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    query_weight: float = 0.6
    retrieval_weight: float = 0.4
    min_query_term_coverage: float = 0.1


class AnswerabilityConfig(BaseModel):
    answerable_top_score: float = 0.3
    partial_top_score: float = 0.18
    evidence_score_threshold: float = 0.16
    min_supporting_hits: int = 1
    min_query_term_coverage: float = 0.2


class RetrievalConfig(BaseModel):
    query_rewrite: QueryRewriteConfig = Field(default_factory=QueryRewriteConfig)
    bm25: BM25Config = Field(default_factory=BM25Config)
    cache: RetrievalCacheConfig = Field(default_factory=RetrievalCacheConfig)
    hybrid: HybridConfig = Field(default_factory=HybridConfig)
    rerank: RerankConfig = Field(default_factory=RerankConfig)
    min_score: float = 0.2
    refuse_if_top_score_below: float = 0.35
    refuse_if_top_gap_below: float = 0.03
    debug_top_n: int = 5


class GenerationPricingConfig(BaseModel):
    input_usd_per_1k_tokens: float | None = None
    output_usd_per_1k_tokens: float | None = None
    pricing_source: str | None = None


class GenerationConfig(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_output_tokens: int = 700
    strict_refusal: bool = True
    answerability: AnswerabilityConfig = Field(default_factory=AnswerabilityConfig)
    pricing: GenerationPricingConfig = Field(default_factory=GenerationPricingConfig)


class CorsConfig(BaseModel):
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("allow_origins", mode="before")
    @classmethod
    def _normalize_allow_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    cors: CorsConfig = Field(
        default_factory=lambda: CorsConfig(
            allow_origins=["*", "http://localhost:3000", "http://127.0.0.1:3000"]
        )
    )
    enable_debug_retrieval_endpoint: bool = False
    request_timeout_s: float = 60.0
    retrieval_timeout_s: float = 15.0
    generation_timeout_s: float = 30.0
    max_query_length: int = 4000
    max_upload_files: int = 10


class RateLimitConfig(BaseModel):
    enabled: bool = True
    requests_per_minute: int = 60
    burst: int = 10
    key_strategy: Literal["ip", "user_or_ip"] = "user_or_ip"
    exempt_paths: list[str] = Field(
        default_factory=lambda: [
            "/health",
            "/healthz",
            "/readyz",
            "/readiness",
            "/api/v1/readiness",
            "/metrics",
            "/api/v1/metrics",
        ]
    )


class SummaryConfig(BaseModel):
    enabled: bool = True
    model: str | None = None
    max_context_chars: int = 18000
    max_points: int = 5


class StorageConfig(BaseModel):
    provider: Literal["local"] = "local"


class AuthConfig(BaseModel):
    enabled: bool = False
    provider: Literal["none", "clerk", "firebase", "header", "api_key"] = "none"
    header_user_id: str = "x-user-id"
    api_key_header: str = "x-api-key"
    api_keys: list[str] = Field(default_factory=list)
    demo_user_id: str = "local-user"
    exempt_paths: list[str] = Field(
        default_factory=lambda: [
            "/health",
            "/healthz",
            "/readyz",
            "/readiness",
            "/api/v1/readiness",
            "/metrics",
            "/api/v1/metrics",
        ]
    )

    @field_validator("api_keys", mode="before")
    @classmethod
    def _normalize_api_keys(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class PrometheusConfig(BaseModel):
    enabled: bool = True
    endpoint: str = "/metrics"


class MonitoringConfig(BaseModel):
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)


class EvaluationConfig(BaseModel):
    dataset_path: str = "evaluation/datasets/gold.jsonl"
    judge_model: str = "gpt-4o-mini"
    enable_llm_judge: bool = False


class LoadTestConfig(BaseModel):
    """HTTP load test settings.

    Why this exists:
    - Load handling can't be inferred from offline evaluation.
    - We keep a small built-in runner so teams can reproduce numbers locally/CI.
    """

    base_url: str = "http://localhost:8000"
    endpoint: str = "/query"
    concurrency: int = 20
    total_requests: int = 200
    timeout_s: float = 60.0
    # If provided, sample questions from the evaluation dataset.
    use_eval_questions: bool = True


class AppConfig(BaseModel):
    name: str = "rag-smart-qa"
    environment: str = "dev"


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    summaries: SummaryConfig = Field(default_factory=SummaryConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    load_test: LoadTestConfig = Field(default_factory=LoadTestConfig)
