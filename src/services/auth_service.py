from __future__ import annotations

from utils.settings import Settings


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve_user_id(self, header_value: str | None) -> str:
        if not self.settings.auth.enabled:
            return self.settings.auth.demo_user_id
        if header_value:
            return header_value
        return self.settings.auth.demo_user_id


def user_id_header_alias(settings: Settings) -> str:
    return settings.auth.header_user_id
