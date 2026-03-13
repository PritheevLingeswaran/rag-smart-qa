from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.api_common import ChunkPreview, PreviewPage


class UploadResponseItem(BaseModel):
    id: str
    filename: str
    stored_path: str
    file_type: str
    size_bytes: int
    indexing_status: str
    summary_status: str
    upload_time: str


class UploadResponse(BaseModel):
    documents: list[UploadResponseItem]


class DocumentSummaryPreview(BaseModel):
    document_id: str
    status: str
    title: str | None = None
    summary: str | None = None
    key_insights: list[str] = Field(default_factory=list)
    important_points: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    error_message: str | None = None
    method: str | None = None
    generated_at: str | None = None


class DocumentItem(BaseModel):
    id: str
    filename: str
    stored_path: str
    file_type: str
    size_bytes: int
    pages: int
    chunks_created: int
    upload_time: str
    indexing_status: str
    summary_status: str
    collection_name: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentListResponse(BaseModel):
    documents: list[DocumentItem]


class DocumentDetailResponse(DocumentItem):
    preview: list[PreviewPage] = Field(default_factory=list)
    chunks: list[ChunkPreview] = Field(default_factory=list)
    summary: DocumentSummaryPreview | None = None


class ReindexResponse(BaseModel):
    document: DocumentDetailResponse


class DashboardStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_sessions: int
    indexing_status: dict[str, int] = Field(default_factory=dict)


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_documents: list[DocumentItem]
    recent_sessions: list[dict[str, object]]
