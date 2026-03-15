from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

from api import deps
from api.app import create_app


class FakeDocumentService:
    settings: Any

    def __init__(self, settings: Any) -> None:
        self.settings = settings

    def list_documents(
        self,
        owner_id: str,
        *,
        search: str | None,
        sort: str,
        order: str,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "doc-1",
                "filename": "guide.txt",
                "stored_path": "/tmp/doc-1.txt",
                "file_type": "txt",
                "size_bytes": 12,
                "pages": 1,
                "chunks_created": 1,
                "upload_time": "2026-03-13T00:00:00Z",
                "indexing_status": "ready",
                "summary_status": "ready",
                "collection_name": None,
                "error_message": None,
                "metadata": {},
            }
        ]


def _write_config(
    tmp_path: Path,
    monkeypatch: Any,
    *,
    auth_provider: str,
    auth_enabled: bool = True,
    api_keys: list[str] | None = None,
    rate_limit_per_minute: int = 20,
    burst: int = 0,
) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    base_config = {
        "app": {"name": "rag-smart-qa", "environment": "test"},
        "api": {
            "cors": {"allow_origins": ["http://localhost:3000"]},
            "request_timeout_s": 60,
            "retrieval_timeout_s": 1,
            "generation_timeout_s": 1,
        },
        "auth": {
            "enabled": auth_enabled,
            "provider": auth_provider,
            "header_user_id": "x-user-id",
            "api_key_header": "x-api-key",
            "api_keys": api_keys or [],
            "demo_user_id": "local-user",
        },
        "monitoring": {
            "prometheus": {"enabled": True, "endpoint": "/metrics"},
            "rate_limit": {
                "enabled": True,
                "requests_per_minute": rate_limit_per_minute,
                "burst": burst,
                "key_strategy": "user_or_ip",
            },
        },
    }
    (config_dir / "base.yaml").write_text(yaml.safe_dump(base_config), encoding="utf-8")
    (config_dir / "dev.yaml").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("RAG_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("RAG_ENV", "dev")
    monkeypatch.setenv("RAG_SKIP_STARTUP_VALIDATION", "1")


def test_api_key_auth_rejects_missing_key(tmp_path: Path, monkeypatch: Any) -> None:
    _write_config(tmp_path, monkeypatch, auth_provider="api_key", api_keys=["secret-key"])
    app = create_app()
    app.dependency_overrides[deps.get_document_service] = lambda: FakeDocumentService(
        deps.get_settings()
    )
    client = TestClient(app)

    response = client.get("/api/v1/documents")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


def test_api_key_auth_accepts_configured_key(tmp_path: Path, monkeypatch: Any) -> None:
    _write_config(tmp_path, monkeypatch, auth_provider="api_key", api_keys=["secret-key"])
    app = create_app()
    app.dependency_overrides[deps.get_document_service] = lambda: FakeDocumentService(
        deps.get_settings()
    )
    client = TestClient(app)

    response = client.get("/api/v1/documents", headers={"x-api-key": "secret-key"})
    assert response.status_code == 200
    assert response.json()["documents"][0]["id"] == "doc-1"


def test_header_auth_requires_user_identity(tmp_path: Path, monkeypatch: Any) -> None:
    _write_config(tmp_path, monkeypatch, auth_provider="header")
    app = create_app()
    app.dependency_overrides[deps.get_document_service] = lambda: FakeDocumentService(
        deps.get_settings()
    )
    client = TestClient(app)

    response = client.get("/api/v1/documents")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_identity"


def test_rate_limiter_rejects_excess_requests(tmp_path: Path, monkeypatch: Any) -> None:
    _write_config(
        tmp_path,
        monkeypatch,
        auth_provider="api_key",
        api_keys=["secret-key"],
        rate_limit_per_minute=1,
        burst=0,
    )
    app = create_app()
    app.dependency_overrides[deps.get_document_service] = lambda: FakeDocumentService(
        deps.get_settings()
    )
    client = TestClient(app)
    headers = {"x-api-key": "secret-key"}

    first = client.get("/api/v1/documents", headers=headers)
    second = client.get("/api/v1/documents", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
    assert second.headers["retry-after"]


def test_health_endpoint_is_exempt_from_auth(tmp_path: Path, monkeypatch: Any) -> None:
    _write_config(tmp_path, monkeypatch, auth_provider="api_key", api_keys=["secret-key"])
    client = TestClient(create_app())

    response = client.get("/healthz")
    assert response.status_code == 200
