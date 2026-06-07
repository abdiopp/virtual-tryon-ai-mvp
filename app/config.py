"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    hf_token: str | None = Field(default=None, alias="HF_TOKEN")

    cloth_model_id: str = Field(
        default="stabilityai/sd-turbo",
        validation_alias=AliasChoices("CLOTH_MODEL_ID", "SDXL_MODEL_ID"),
    )
    cloth_lora_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CLOTH_LORA_PATH", "SDXL_LORA_PATH"),
    )
    cloth_local_files_only: bool = Field(
        default=True,
        validation_alias=AliasChoices("CLOTH_LOCAL_FILES_ONLY", "SDXL_LOCAL_FILES_ONLY"),
    )

    tryon_backend: str = Field(default="fashn_vton", alias="TRYON_BACKEND")
    fashn_repo_url: str = Field(
        default="https://github.com/fashn-AI/fashn-vton-1.5.git",
        alias="FASHN_REPO_URL",
    )
    fashn_model_dir: Path = Field(default=Path("models/fashn_vton"), alias="FASHN_MODEL_DIR")
    fashn_weights_dir: Path = Field(default=Path("models/fashn_weights"), alias="FASHN_WEIGHTS_DIR")
    fashn_num_timesteps: int = Field(default=8, alias="FASHN_NUM_TIMESTEPS")
    fashn_guidance_scale: float = Field(default=1.2, alias="FASHN_GUIDANCE_SCALE")
    fashn_num_samples: int = Field(default=1, alias="FASHN_NUM_SAMPLES")
    fashn_segmentation_free: bool = Field(default=True, alias="FASHN_SEGMENTATION_FREE")
    fashn_garment_photo_type: str = Field(default="flat-lay", alias="FASHN_GARMENT_PHOTO_TYPE")
    fashn_fallback_to_cpu_on_oom: bool = Field(default=True, alias="FASHN_FALLBACK_TO_CPU_ON_OOM")

    model_cache_dir: Path = Field(default=Path("models/huggingface"), alias="MODEL_CACHE_DIR")
    output_dir: Path = Field(default=Path("outputs"), alias="OUTPUT_DIR")
    upload_dir: Path = Field(default=Path("uploads"), alias="UPLOAD_DIR")

    device: str = Field(default="cpu", alias="DEVICE")
    mps_use_fp16: bool = Field(default=False, alias="MPS_USE_FP16")

    default_image_width: int = Field(default=512, alias="DEFAULT_IMAGE_WIDTH")
    default_image_height: int = Field(default=768, alias="DEFAULT_IMAGE_HEIGHT")

    non_cuda_force_fast_limits: bool = Field(default=True, alias="NON_CUDA_FORCE_FAST_LIMITS")
    non_cuda_max_count: int = Field(default=2, alias="NON_CUDA_MAX_COUNT")
    non_cuda_max_steps: int = Field(default=6, alias="NON_CUDA_MAX_STEPS")
    non_cuda_max_pixels: int = Field(default=393216, alias="NON_CUDA_MAX_PIXELS")

    prompt_enhancement_enabled: bool = Field(default=True, alias="PROMPT_ENHANCEMENT_ENABLED")
    prompt_enhancement_template: str = Field(
        default=(
            "front view ecommerce product photo of a {prompt}, isolated garment, "
            "clean white background, realistic cotton fabric texture, symmetrical design, "
            "high detail, no person, no mannequin"
        ),
        alias="PROMPT_ENHANCEMENT_TEMPLATE",
    )

    @field_validator("hf_token", mode="before")
    @classmethod
    def normalize_hf_token(cls, value: object) -> str | None:
        """Treat blank/whitespace HF_TOKEN values as None."""

        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    def _resolve_project_path(self, value: Path) -> Path:
        """Resolve relative paths against project root for stable behavior."""

        if value.is_absolute():
            return value
        return (PROJECT_ROOT / value).resolve()

    def ensure_directories(self) -> None:
        """Ensure required local directories exist."""

        self.model_cache_dir = self._resolve_project_path(self.model_cache_dir)
        self.output_dir = self._resolve_project_path(self.output_dir)
        self.upload_dir = self._resolve_project_path(self.upload_dir)
        self.fashn_model_dir = self._resolve_project_path(self.fashn_model_dir)
        self.fashn_weights_dir = self._resolve_project_path(self.fashn_weights_dir)

        generated_dir = self.output_dir / "generated_clothes"
        tryon_dir = self.output_dir / "tryon_results"
        persons_dir = self.upload_dir / "persons"
        garments_dir = self.upload_dir / "garments"

        for directory in [
            self.output_dir,
            self.upload_dir,
            self.model_cache_dir,
            generated_dir,
            tryon_dir,
            persons_dir,
            garments_dir,
            self.fashn_model_dir.parent,
            self.fashn_weights_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    settings = Settings()
    settings.ensure_directories()
    return settings
