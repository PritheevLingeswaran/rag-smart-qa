from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from utils.settings import Settings


class StorageService(ABC):
    @abstractmethod
    def save_upload(self, upload: UploadFile, *, owner_id: str) -> tuple[Path, int]:
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, path: str) -> None:
        raise NotImplementedError


class LocalStorageService(StorageService):
    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.paths.uploads_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_upload(self, upload: UploadFile, *, owner_id: str) -> tuple[Path, int]:
        safe_name = Path(upload.filename or "upload.bin").name
        dest_dir = self.root / owner_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{uuid4()}-{safe_name}"
        size = 0
        with dest_path.open("wb") as handle:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                size += len(chunk)
        upload.file.seek(0)
        return dest_path, size

    def delete_file(self, path: str) -> None:
        target = Path(path)
        if target.exists():
            target.unlink()
