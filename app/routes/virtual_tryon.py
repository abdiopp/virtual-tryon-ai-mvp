"""Routes for virtual try-on."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas import VirtualTryOnPathRequest, VirtualTryOnResponse
from app.services.tryon_service import FashnTryOnService, TryOnSetupError
from app.services.storage_service import StorageService

router = APIRouter(tags=["virtual-tryon"])
storage = StorageService()
tryon_service = FashnTryOnService()


@router.post("/virtual-tryon", response_model=VirtualTryOnResponse)
def virtual_tryon_upload(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
    category: str = Form(default="upper_body"),
) -> VirtualTryOnResponse:
    """Run virtual try-on using uploaded person and garment images."""

    try:
        person_path = storage.save_upload_file(person_image, subfolder="persons", prefix="person")
        garment_path = storage.save_upload_file(garment_image, subfolder="garments", prefix="garment")
        result = tryon_service.run_tryon(
            person_image_path=person_path,
            garment_image_path=garment_path,
            category=category,
        )
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except TryOnSetupError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return VirtualTryOnResponse(success=True, result_path=result.result_path, metadata=result.metadata)


@router.post("/virtual-tryon-from-path", response_model=VirtualTryOnResponse)
def virtual_tryon_from_path(payload: VirtualTryOnPathRequest) -> VirtualTryOnResponse:
    """Run virtual try-on using local filesystem paths."""

    try:
        result = tryon_service.run_tryon(
            person_image_path=payload.person_image_path,
            garment_image_path=payload.garment_image_path,
            category=payload.category,
        )
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except TryOnSetupError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return VirtualTryOnResponse(success=True, result_path=result.result_path, metadata=result.metadata)
