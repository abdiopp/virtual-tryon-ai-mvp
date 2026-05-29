"""Local filesystem storage helpers."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings, get_settings


class StorageService:
    """Service responsible for local file storage operations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def save_upload_file(self, upload_file: UploadFile, subfolder: str, prefix: str) -> Path:
        """Persist an uploaded file into configured upload directory."""

        ext = Path(upload_file.filename or "").suffix.lower() or ".png"
        destination = self.settings.upload_dir / subfolder / f"{prefix}_{uuid4().hex[:10]}{ext}"
        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        upload_file.file.close()
        return destination

    def copy_to(self, source: Path, destination: Path) -> Path:
        """Copy a file to destination path and return destination."""

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def build_output_path(self, subfolder: str, prefix: str, extension: str = ".png") -> Path:
        """Generate unique output path under output directory."""

        extension = extension if extension.startswith(".") else f".{extension}"
        output_path = self.settings.output_dir / subfolder / f"{prefix}_{uuid4().hex[:12]}{extension}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
