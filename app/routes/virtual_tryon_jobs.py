"""Async virtual try-on job endpoints for long-running demo requests."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas import (
    VirtualTryOnJobCreateResponse,
    VirtualTryOnJobStatusResponse,
    VirtualTryOnPathRequest,
)
from app.config import get_settings
from app.services.storage_service import StorageService
from app.services.tryon_service import TryOnCloudLimitError, TryOnSetupError, get_tryon_service

router = APIRouter(tags=["virtual-tryon-jobs"])
settings = get_settings()
storage = StorageService()
tryon_service = get_tryon_service()
executor = ThreadPoolExecutor(max_workers=1)
job_lock = threading.Lock()


@dataclass
class TryOnJob:
    """In-memory state for a running try-on job."""

    job_id: str
    status: str
    created_at: float
    updated_at: float
    result_path: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    error: str | None = None


JOBS: dict[str, TryOnJob] = {}


def _set_job(job_id: str, **changes: object) -> TryOnJob:
    with job_lock:
        job = JOBS[job_id]
        for key, value in changes.items():
            setattr(job, key, value)
        job.updated_at = time.time()
        return job


def _create_job() -> TryOnJob:
    job_id = uuid4().hex
    job = TryOnJob(job_id=job_id, status="queued", created_at=time.time(), updated_at=time.time())
    with job_lock:
        active_jobs = sum(1 for existing in JOBS.values() if existing.status in {"queued", "running"})
        if active_jobs >= settings.tryon_max_queued_jobs:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many try-on jobs are already queued or running. "
                    f"Limit: {settings.tryon_max_queued_jobs}."
                ),
            )
        JOBS[job_id] = job
    return job


def _run_job(job_id: str, *, person_path: Path, garment_path: Path, category: str) -> None:
    try:
        _set_job(job_id, status="running")
        result = tryon_service.run_tryon(
            person_image_path=person_path,
            garment_image_path=garment_path,
            category=category,
        )
        _set_job(
            job_id,
            status="completed",
            result_path=result.result_path,
            metadata=result.metadata,
            error=None,
        )
    except TryOnCloudLimitError as error:
        _set_job(job_id, status="failed", error=str(error), metadata={"status_code": error.status_code})
    except (FileNotFoundError, ValueError, TryOnSetupError) as error:
        _set_job(job_id, status="failed", error=str(error))
    except Exception as error:  # pragma: no cover - unexpected runtime failure
        _set_job(job_id, status="failed", error=str(error))


def _submit_job(*, person_path: Path, garment_path: Path, category: str) -> TryOnJob:
    job = _create_job()
    executor.submit(_run_job, job.job_id, person_path=person_path, garment_path=garment_path, category=category)
    return job


@router.post("/virtual-tryon-jobs/from-path", response_model=VirtualTryOnJobCreateResponse)
def create_tryon_job_from_path(payload: VirtualTryOnPathRequest) -> VirtualTryOnJobCreateResponse:
    """Queue a try-on job using local filesystem paths."""

    job = _submit_job(
        person_path=Path(payload.person_image_path),
        garment_path=Path(payload.garment_image_path),
        category=payload.category,
    )
    return VirtualTryOnJobCreateResponse(success=True, job_id=job.job_id, status=job.status)


@router.post("/virtual-tryon-jobs/upload", response_model=VirtualTryOnJobCreateResponse)
def create_tryon_job_from_upload(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
    category: str = Form(default="upper_body"),
) -> VirtualTryOnJobCreateResponse:
    """Queue a try-on job using uploaded files."""

    person_path = storage.save_upload_file(person_image, subfolder="persons", prefix="person")
    garment_path = storage.save_upload_file(garment_image, subfolder="garments", prefix="garment")
    job = _submit_job(person_path=person_path, garment_path=garment_path, category=category)
    return VirtualTryOnJobCreateResponse(success=True, job_id=job.job_id, status=job.status)


@router.get("/virtual-tryon-jobs/{job_id}", response_model=VirtualTryOnJobStatusResponse)
def get_tryon_job(job_id: str) -> VirtualTryOnJobStatusResponse:
    """Return the current state of a queued or running try-on job."""

    with job_lock:
        job = JOBS.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return VirtualTryOnJobStatusResponse(
        success=True,
        job_id=job.job_id,
        status=job.status,
        result_path=job.result_path,
        metadata=job.metadata,
        error=job.error,
    )
