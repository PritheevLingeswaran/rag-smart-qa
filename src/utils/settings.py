from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    data_dir: str = "data"
    raw_dir: str = "data/raw/documents"
    processed_dir: str = "data/processed"
    chunks_dir: str = "data/processed/chunks"
    metadata_dir: str = "data/processed/metadata"
    indexes_dir: str = "data/processed/indexes"


class IngestionConfig(BaseModel):
    supported_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".txt"])


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
    # Number of BM25 candidates to retrieve from the *full corpus*.
    bm25_k: int = 200
    # Number of dense candidates to retrieve (typically >= top_k).
    dense_k: int = 40
    # Fusion weight: final_score = dense_weight * dense + (1-dense_weight) * bm25
    dense_weight: float = 0.65


class RerankConfig(BaseModel):
    enabled: bool = False
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RetrievalConfig(BaseModel):
    query_rewrite: QueryRewriteConfig = Field(default_factory=QueryRewriteConfig)
    hybrid: HybridConfig = Field(default_factory=HybridConfig)
    rerank: RerankConfig = Field(default_factory=RerankConfig)
    min_score: float = 0.2


class GenerationConfig(BaseModel):
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_output_tokens: int = 700
    strict_refusal: bool = True


class CorsConfig(BaseModel):
    allow_origins: list[str] = Field(default_factory=lambda: ["*"])


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    cors: CorsConfig = Field(default_factory=CorsConfig)


class PrometheusConfig(BaseModel):
    enabled: bool = True
    endpoint: str = "/metrics"


class MonitoringConfig(BaseModel):
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)


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
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    load_test: LoadTestConfig = Field(default_factory=LoadTestConfig)
