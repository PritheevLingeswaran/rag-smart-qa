from __future__ import annotations

from secrets import compare_digest
from typing import cast

from fastapi import HTTPException

from monitoring.query_metrics import record_auth_failure
from utils.settings import Settings


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve_user_id(self, header_value: str | None) -> str:
        if not self.settings.auth.enabled:
            return cast(str, self.settings.auth.demo_user_id)
        if self.settings.auth.provider == "api_key":
            return cast(str, header_value or self.settings.auth.demo_user_id)
        if header_value:
            return header_value
        if self.settings.auth.provider == "header":
            record_auth_failure("missing_user_header")
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "missing_identity",
                    "message": "Missing authenticated user header.",
                },
            )
        return cast(str, self.settings.auth.demo_user_id)

    def authenticate_api_key(self, api_key: str | None) -> None:
        if not self.settings.auth.enabled or self.settings.auth.provider != "api_key":
            return
        configured_keys = [key for key in self.settings.auth.api_keys if key]
        if not configured_keys:
            record_auth_failure("misconfigured_api_key_auth")
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "auth_not_configured",
                    "message": "API authentication is enabled but no API keys are configured.",
                },
            )
        if api_key and any(compare_digest(api_key, configured) for configured in configured_keys):
            return
        record_auth_failure("invalid_api_key")
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_api_key", "message": "Missing or invalid API key."},
        )


def user_id_header_alias(settings: Settings) -> str:
    return cast(str, settings.auth.header_user_id)
