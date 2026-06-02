"""Routes for SDXL garment generation."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from app.schemas import GenerateClothesRequest, GenerateClothesResponse, GenerateClothItem
from app.services.cloth_generator import ClothGenerationError, ClothGeneratorService
from app.utils.logging_utils import get_logger

router = APIRouter(tags=["cloth-generation"])
cloth_service = ClothGeneratorService()
logger = get_logger(__name__)


@router.post("/generate-clothes", response_model=GenerateClothesResponse)
def generate_clothes(payload: GenerateClothesRequest) -> GenerateClothesResponse:
    """Generate standalone ecommerce garment images from text prompt."""

    started_at = time.monotonic()
    logger.info(
        "Generate-clothes request started prompt=%r category=%s count=%d size=%dx%d steps=%d guidance=%.2f",
        payload.prompt,
        payload.category or "default",
        payload.count,
        payload.width,
        payload.height,
        payload.num_inference_steps,
        payload.guidance_scale,
    )

    try:
        items = cloth_service.generate_clothes(
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
    except ClothGenerationError as error:
        logger.warning(
            "Generate-clothes request failed after %.1fs: %s",
            time.monotonic() - started_at,
            error,
        )
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RuntimeError as error:
        logger.exception(
            "Generate-clothes request crashed after %.1fs",
            time.monotonic() - started_at,
        )
        raise HTTPException(status_code=500, detail=str(error)) from error

    logger.info(
        "Generate-clothes request finished in %.1fs with %d item(s)",
        time.monotonic() - started_at,
        len(items),
    )

    return GenerateClothesResponse(
        success=True,
        items=[
            GenerateClothItem(
                id=item.id,
                path=item.path,
                prompt=item.prompt,
                seed=item.seed,
                metadata=item.metadata,
            )
            for item in items
        ],
    )
