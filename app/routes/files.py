"""Serve generated or uploaded files from the backend workspace."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter(tags=["files"])
settings = get_settings()

ALLOWED_ROOTS = [settings.output_dir.resolve(), settings.upload_dir.resolve()]


def _resolve_requested_path(file_path: str) -> Path:
    """Resolve a requested path and ensure it stays inside allowed workspace roots."""

    candidate = Path(file_path)
    resolved = candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
    normalized = resolved.resolve()

    for root in ALLOWED_ROOTS:
        try:
            normalized.relative_to(root)
            return normalized
        except ValueError:
            continue

    raise HTTPException(status_code=403, detail="File path is outside allowed preview roots")


def _guess_media_type(resolved_path: Path) -> str:
    """Return a basic media type for common image outputs."""

    suffix = resolved_path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    return "application/octet-stream"


@router.get("/files")
def get_file(
    path: str = Query(..., description="Absolute or relative path to a generated/output file"),
    download: bool = Query(default=False, description="Force browser download instead of preview"),
) -> FileResponse:
    """Return a file from the backend workspace for browser preview or download."""

    resolved_path = _resolve_requested_path(path)
    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=resolved_path,
        filename=resolved_path.name if download else None,
        media_type=_guess_media_type(resolved_path),
        content_disposition_type="attachment" if download else "inline",
    )
