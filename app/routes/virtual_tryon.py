"""Routes for virtual try-on."""

from __future__ import annotations

import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas import VirtualTryOnPathRequest, VirtualTryOnResponse
from app.services.tryon_service import TryOnCloudLimitError, TryOnSetupError, get_tryon_service
from app.services.storage_service import StorageService
from app.utils.logging_utils import get_logger

router = APIRouter(tags=["virtual-tryon"])
storage = StorageService()
tryon_service = get_tryon_service()
logger = get_logger(__name__)


@router.post("/virtual-tryon", response_model=VirtualTryOnResponse)
def virtual_tryon_upload(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
    category: str = Form(default="upper_body"),
) -> VirtualTryOnResponse:
    """Run virtual try-on using uploaded person and garment images."""

    started_at = time.monotonic()
    logger.info(
        "Virtual-tryon upload request started category=%s person_file=%s garment_file=%s",
        category,
        person_image.filename,
        garment_image.filename,
    )

    try:
        person_path = storage.save_upload_file(person_image, subfolder="persons", prefix="person")
        garment_path = storage.save_upload_file(garment_image, subfolder="garments", prefix="garment")
        result = tryon_service.run_tryon(
            person_image_path=person_path,
            garment_image_path=garment_path,
            category=category,
        )
    except (FileNotFoundError, ValueError) as error:
        logger.warning(
            "Virtual-tryon upload request failed after %.1fs: %s",
            time.monotonic() - started_at,
            error,
        )
        raise HTTPException(status_code=400, detail=str(error)) from error
    except TryOnCloudLimitError as error:
        logger.warning(
            "Virtual-tryon upload request hit cloud limit after %.1fs: %s",
            time.monotonic() - started_at,
            error,
        )
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    except TryOnSetupError as error:
        logger.warning(
            "Virtual-tryon upload request failed after %.1fs: %s",
            time.monotonic() - started_at,
            error,
        )
        raise HTTPException(status_code=503, detail=str(error)) from error

    logger.info(
        "Virtual-tryon upload request finished in %.1fs -> %s",
        time.monotonic() - started_at,
        result.result_path,
    )

    return VirtualTryOnResponse(success=True, result_path=result.result_path, metadata=result.metadata)


@router.post("/virtual-tryon-from-path", response_model=VirtualTryOnResponse)
def virtual_tryon_from_path(payload: VirtualTryOnPathRequest) -> VirtualTryOnResponse:
    """Run virtual try-on using local filesystem paths."""

    started_at = time.monotonic()
    logger.info(
        "Virtual-tryon path request started category=%s person=%s garment=%s",
        payload.category,
        payload.person_image_path,
        payload.garment_image_path,
    )

    try:
        result = tryon_service.run_tryon(
            person_image_path=payload.person_image_path,
            garment_image_path=payload.garment_image_path,
            category=payload.category,
        )
    except (FileNotFoundError, ValueError) as error:
        logger.warning(
            "Virtual-tryon path request failed after %.1fs: %s",
            time.monotonic() - started_at,
            error,
        )
        raise HTTPException(status_code=400, detail=str(error)) from error
    except TryOnCloudLimitError as error:
        logger.warning(
            "Virtual-tryon path request hit cloud limit after %.1fs: %s",
            time.monotonic() - started_at,
            error,
        )
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    except TryOnSetupError as error:
        logger.warning(
            "Virtual-tryon path request failed after %.1fs: %s",
            time.monotonic() - started_at,
            error,
        )
        raise HTTPException(status_code=503, detail=str(error)) from error

    logger.info(
        "Virtual-tryon path request finished in %.1fs -> %s",
        time.monotonic() - started_at,
        result.result_path,
    )

    return VirtualTryOnResponse(success=True, result_path=result.result_path, metadata=result.metadata)
