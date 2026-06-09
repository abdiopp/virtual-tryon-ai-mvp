"""Health endpoint."""

from __future__ import annotations

import torch
from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthModelsStatus, HealthResponse
from app.services.tryon_service import get_tryon_service
from app.services.cloth_generator import ClothGeneratorService
from app.utils.device import describe_device

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return service and model readiness information."""

    settings = get_settings()
    cloth_service = ClothGeneratorService(settings)
    tryon_service = get_tryon_service(settings)

    return HealthResponse(
        status="ok",
        device=describe_device(settings.device),
        requested_device=settings.device,
        cuda_available=torch.cuda.is_available(),
        mps_available=torch.backends.mps.is_available(),
        models=HealthModelsStatus(
            cloth_generator="available" if cloth_service.is_model_available() else "missing",
            tryon_model="available" if tryon_service.is_model_available() else "missing",
        ),
    )
