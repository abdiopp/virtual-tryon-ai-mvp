"""Tests for async virtual try-on job queue limits."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes import virtual_tryon_jobs
from app.routes.virtual_tryon_jobs import TryOnJob


def test_create_job_rejects_when_queue_limit_is_reached(monkeypatch) -> None:
    monkeypatch.setattr(virtual_tryon_jobs, "settings", SimpleNamespace(tryon_max_queued_jobs=1))
    virtual_tryon_jobs.JOBS.clear()
    virtual_tryon_jobs.JOBS["existing"] = TryOnJob(
        job_id="existing",
        status="running",
        created_at=time.time(),
        updated_at=time.time(),
    )

    with pytest.raises(HTTPException) as exc_info:
        virtual_tryon_jobs._create_job()

    assert exc_info.value.status_code == 429
    assert "Too many try-on jobs" in exc_info.value.detail

    virtual_tryon_jobs.JOBS.clear()
