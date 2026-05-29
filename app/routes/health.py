"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthModelsStatus, HealthResponse
from app.services.tryon_service import FashnTryOnService
from app.services.cloth_generator import ClothGeneratorService
from app.utils.device import describe_device

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return service and model readiness information."""

    settings = get_settings()
    cloth_service = ClothGeneratorService(settings)
    tryon_service = FashnTryOnService(settings)

    return HealthResponse(
        status="ok",
        device=describe_device(settings.device),
        models=HealthModelsStatus(
            cloth_generator="available" if cloth_service.is_model_available() else "missing",
            tryon_model="available" if tryon_service.is_model_available() else "missing",
        ),
    )
