from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from api.deps import get_current_user_id, get_document_service, get_metadata_service
from schemas.api_common import ApiErrorResponse, SourceCitation
from schemas.documents import (
    DashboardResponse,
    DocumentDetailResponse,
    DocumentItem,
    DocumentListResponse,
    ReindexResponse,
    UploadResponse,
)
from services.document_service import DocumentService
from services.metadata_service import MetadataService

router = APIRouter(tags=["documents"])


@router.post(
    "/documents/upload",
    response_model=UploadResponse,
    responses={400: {"model": ApiErrorResponse}},
)
@router.post("/upload", response_model=UploadResponse, include_in_schema=False)
def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),  # noqa: B008
    collection_name: str | None = Form(default=None),
    owner_id: str = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> UploadResponse:
    max_files = int(document_service.settings.api.max_upload_files)
    if len(files) > max_files:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "too_many_files",
                "message": f"Upload supports at most {max_files} files per request.",
            },
        )
    documents = document_service.create_upload_records(
        files=files,
        owner_id=owner_id,
        collection_name=collection_name,
    )
    background_tasks.add_task(document_service.rebuild_indexes, owner_id=owner_id)
    return UploadResponse(documents=documents)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    search: str | None = None,
    sort: str = "upload_time",
    order: str = "desc",
    owner_id: str = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentListResponse:
    documents = document_service.list_documents(owner_id, search=search, sort=sort, order=order)
    return DocumentListResponse(documents=[DocumentItem.model_validate(doc) for doc in documents])


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    responses={404: {"model": ApiErrorResponse}},
)
def get_document(
    document_id: str,
    owner_id: str = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentDetailResponse:
    return DocumentDetailResponse.model_validate(
        document_service.get_document_detail(document_id, owner_id)
    )


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentItem,
    responses={404: {"model": ApiErrorResponse}},
)
def delete_document(
    document_id: str,
    owner_id: str = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DocumentItem:
    return DocumentItem.model_validate(document_service.delete_document(document_id, owner_id))


@router.post("/documents/{document_id}/reindex", response_model=ReindexResponse)
def reindex_document(
    document_id: str,
    owner_id: str = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> ReindexResponse:
    return ReindexResponse(
        document=DocumentDetailResponse.model_validate(
            document_service.reindex_document(document_id, owner_id)
        )
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    owner_id: str = Depends(get_current_user_id),
    document_service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> DashboardResponse:
    return DashboardResponse.model_validate(document_service.get_dashboard(owner_id))


@router.get("/citations/{citation_id}", response_model=SourceCitation)
def get_citation(
    citation_id: str,
    owner_id: str = Depends(get_current_user_id),
    metadata: MetadataService = Depends(get_metadata_service),  # noqa: B008
) -> SourceCitation:
    citation = metadata.get_citation(citation_id, owner_id)
    if citation is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "citation_not_found", "message": "Citation not found."},
        )
    return SourceCitation.model_validate(citation)
