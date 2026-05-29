"""Routes for SDXL garment generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import GenerateClothesRequest, GenerateClothesResponse, GenerateClothItem
from app.services.cloth_generator import ClothGenerationError, ClothGeneratorService

router = APIRouter(tags=["cloth-generation"])
cloth_service = ClothGeneratorService()


@router.post("/generate-clothes", response_model=GenerateClothesResponse)
def generate_clothes(payload: GenerateClothesRequest) -> GenerateClothesResponse:
    """Generate standalone ecommerce garment images from text prompt."""

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
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

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
