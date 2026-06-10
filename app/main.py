"""FastAPI entrypoint for virtual-tryon-ai-mvp."""

from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings
from app.routes.files import router as files_router
from app.routes.generate_clothes import router as generate_clothes_router
from app.routes.generate_clothes_jobs import router as generate_clothes_jobs_router
from app.routes.health import router as health_router
from app.routes.virtual_tryon import router as virtual_tryon_router
from app.routes.virtual_tryon_jobs import router as virtual_tryon_jobs_router
from app.utils.logging_utils import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

settings = get_settings()

app = FastAPI(
    title="virtual-tryon-ai-mvp",
    description="Two-stage AI virtual try-on MVP (Flux cloth generation + Hugging Face Space try-on backend)",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(files_router)
app.include_router(generate_clothes_router)
app.include_router(generate_clothes_jobs_router)
app.include_router(virtual_tryon_router)
app.include_router(virtual_tryon_jobs_router)


@app.on_event("startup")
def startup_event() -> None:
    """Initialize filesystem directories."""

    settings.ensure_directories()
    logger.info("Application startup complete.")


@app.get("/")
def root() -> dict[str, str]:
    """Basic API metadata endpoint."""

    return {
        "name": "virtual-tryon-ai-mvp",
        "status": "running",
        "docs": "/docs",
    }
