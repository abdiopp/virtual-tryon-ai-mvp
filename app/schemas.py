"""Pydantic request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthModelsStatus(BaseModel):
    """Model availability state for health endpoint."""

    cloth_generator: str
    tryon_model: str


class HealthResponse(BaseModel):
    """Health response schema."""

    status: str
    device: str
    requested_device: str
    cuda_available: bool
    mps_available: bool
    models: HealthModelsStatus


class GenerateClothesRequest(BaseModel):
    """Request payload for clothing generation."""

    prompt: str = Field(..., min_length=3)
    category: str | None = None
    negative_prompt: str | None = None
    count: int = Field(default=1, ge=1, le=8)
    width: int = Field(default=1024, ge=256, le=1536)
    height: int = Field(default=1024, ge=256, le=1536)
    guidance_scale: float = Field(default=0.0, ge=0.0, le=20.0)
    num_inference_steps: int = Field(default=4, ge=1, le=100)
    seed: int | None = None


class GenerateClothItem(BaseModel):
    """Single generated cloth item."""

    id: str
    path: str
    prompt: str
    seed: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateClothesResponse(BaseModel):
    """Response for clothing generation."""

    success: bool
    items: list[GenerateClothItem]


class GenerateClothesJobCreateResponse(BaseModel):
    """Response payload for async clothes generation job creation."""

    success: bool
    job_id: str
    status: str


class GenerateClothesJobStatusResponse(BaseModel):
    """Response payload for async clothes generation job status polling."""

    success: bool
    job_id: str
    status: str
    items: list[GenerateClothItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class VirtualTryOnPathRequest(BaseModel):
    """Request payload for try-on using local file paths."""

    person_image_path: str
    garment_image_path: str
    category: str = "upper_body"


class VirtualTryOnResponse(BaseModel):
    """Response payload for try-on endpoints."""

    success: bool
    result_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class VirtualTryOnJobCreateResponse(BaseModel):
    """Response payload for async try-on job creation."""

    success: bool
    job_id: str
    status: str


class VirtualTryOnJobStatusResponse(BaseModel):
    """Response payload for async try-on job status polling."""

    success: bool
    job_id: str
    status: str
    result_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
