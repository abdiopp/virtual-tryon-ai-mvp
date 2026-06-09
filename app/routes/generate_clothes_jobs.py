"""Async garment generation job endpoints for long-running tunnel-safe requests."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.schemas import (
    GenerateClothItem,
    GenerateClothesJobCreateResponse,
    GenerateClothesJobStatusResponse,
    GenerateClothesRequest,
)
from app.services.cloth_generator import ClothGenerationError, ClothGeneratorService

router = APIRouter(tags=["cloth-generation-jobs"])
cloth_service = ClothGeneratorService()
executor = ThreadPoolExecutor(max_workers=1)
job_lock = threading.Lock()


@dataclass
class GenerateClothesJob:
    """In-memory state for a running clothes generation job."""

    job_id: str
    status: str
    created_at: float
    updated_at: float
    items: list[GenerateClothItem] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    error: str | None = None


JOBS: dict[str, GenerateClothesJob] = {}


def _set_job(job_id: str, **changes: object) -> GenerateClothesJob:
    with job_lock:
        job = JOBS[job_id]
        for key, value in changes.items():
            setattr(job, key, value)
        job.updated_at = time.time()
        return job


def _create_job() -> GenerateClothesJob:
    job_id = uuid4().hex
    job = GenerateClothesJob(
        job_id=job_id,
        status="queued",
        created_at=time.time(),
        updated_at=time.time(),
    )
    with job_lock:
        JOBS[job_id] = job
    return job


def _run_job(job_id: str, payload: GenerateClothesRequest) -> None:
    try:
        _set_job(job_id, status="running")
        results = cloth_service.generate_clothes(
            prompt=payload.prompt,
            category=payload.category,
            negative_prompt=payload.negative_prompt,
            count=payload.count,
            width=payload.width,
            height=payload.height,
            guidance_scale=payload.guidance_scale,
            num_inference_steps=payload.num_inference_steps,
            seed=payload.seed,
        )
        items = [
            GenerateClothItem(
                id=item.id,
                path=item.path,
                prompt=item.prompt,
                seed=item.seed,
                metadata=item.metadata,
            )
            for item in results
        ]
        _set_job(
            job_id,
            status="completed",
            items=items,
            metadata={"count": len(items)},
            error=None,
        )
    except ClothGenerationError as error:
        _set_job(job_id, status="failed", error=str(error))
    except Exception as error:  # pragma: no cover - unexpected runtime failure
        _set_job(job_id, status="failed", error=str(error))


@router.post("/generate-clothes-jobs", response_model=GenerateClothesJobCreateResponse)
def create_generate_clothes_job(payload: GenerateClothesRequest) -> GenerateClothesJobCreateResponse:
    """Queue a clothes generation job and return immediately."""

    job = _create_job()
    executor.submit(_run_job, job.job_id, payload)
    return GenerateClothesJobCreateResponse(success=True, job_id=job.job_id, status=job.status)


@router.get("/generate-clothes-jobs/{job_id}", response_model=GenerateClothesJobStatusResponse)
def get_generate_clothes_job(job_id: str) -> GenerateClothesJobStatusResponse:
    """Return the current state of a queued or running clothes generation job."""

    with job_lock:
        job = JOBS.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return GenerateClothesJobStatusResponse(
        success=True,
        job_id=job.job_id,
        status=job.status,
        items=job.items,
        metadata=job.metadata,
        error=job.error,
    )
