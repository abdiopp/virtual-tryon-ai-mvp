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
        default="black-forest-labs/FLUX.1-schnell",
        validation_alias=AliasChoices("CLOTH_MODEL_ID", "SDXL_MODEL_ID"),
    )
    cloth_inference_provider: str = Field(default="nscale", alias="CLOTH_INFERENCE_PROVIDER")
    cloth_max_generation_attempts: int = Field(default=3, alias="CLOTH_MAX_GENERATION_ATTEMPTS")
    cloth_min_border_margin_ratio: float = Field(default=0.08, alias="CLOTH_MIN_BORDER_MARGIN_RATIO")

    tryon_backend: str = Field(default="huggingface_space", alias="TRYON_BACKEND")
    tryon_space_id: str = Field(default="yisol/IDM-VTON", alias="TRYON_SPACE_ID")
    tryon_space_api_name: str = Field(default="/tryon", alias="TRYON_SPACE_API_NAME")
    tryon_space_denoise_steps: int = Field(default=30, alias="TRYON_SPACE_DENOISE_STEPS")
    tryon_space_seed: int = Field(default=42, alias="TRYON_SPACE_SEED")
    tryon_space_auto_mask: bool = Field(default=True, alias="TRYON_SPACE_AUTO_MASK")
    tryon_space_auto_crop: bool = Field(default=False, alias="TRYON_SPACE_AUTO_CROP")
    leffa_repo_url: str = Field(
        default="https://github.com/franciszzj/Leffa.git",
        alias="LEFFA_REPO_URL",
    )
    leffa_model_dir: Path = Field(default=Path("models/leffa"), alias="LEFFA_MODEL_DIR")
    leffa_checkpoint_dir: Path = Field(default=Path("models/leffa_ckpts"), alias="LEFFA_CHECKPOINT_DIR")
    leffa_hf_repo_id: str = Field(default="franciszzj/Leffa", alias="LEFFA_HF_REPO_ID")
    leffa_num_inference_steps: int = Field(default=30, alias="LEFFA_NUM_INFERENCE_STEPS")
    leffa_guidance_scale: float = Field(default=2.5, alias="LEFFA_GUIDANCE_SCALE")
    leffa_seed: int = Field(default=42, alias="LEFFA_SEED")
    leffa_model_type: str = Field(default="auto", alias="LEFFA_MODEL_TYPE")
    leffa_ref_acceleration: bool = Field(default=False, alias="LEFFA_REF_ACCELERATION")
    leffa_repaint: bool = Field(default=False, alias="LEFFA_REPAINT")
    leffa_preprocess_garment: bool = Field(default=False, alias="LEFFA_PREPROCESS_GARMENT")
    leffa_require_cuda: bool = Field(default=True, alias="LEFFA_REQUIRE_CUDA")
    leffa_memory_efficient_load: bool = Field(default=True, alias="LEFFA_MEMORY_EFFICIENT_LOAD")

    fashn_repo_url: str = Field(
        default="https://github.com/fashn-AI/fashn-vton-1.5.git",
        alias="FASHN_REPO_URL",
    )
    fashn_model_dir: Path = Field(default=Path("models/fashn_vton"), alias="FASHN_MODEL_DIR")
    fashn_weights_dir: Path = Field(default=Path("models/fashn_weights"), alias="FASHN_WEIGHTS_DIR")
    fashn_num_timesteps: int = Field(default=30, alias="FASHN_NUM_TIMESTEPS")
    fashn_guidance_scale: float = Field(default=1.5, alias="FASHN_GUIDANCE_SCALE")
    fashn_num_samples: int = Field(default=1, alias="FASHN_NUM_SAMPLES")
    fashn_segmentation_free: bool = Field(default=True, alias="FASHN_SEGMENTATION_FREE")
    fashn_garment_photo_type: str = Field(default="flat-lay", alias="FASHN_GARMENT_PHOTO_TYPE")
    fashn_fallback_to_cpu_on_oom: bool = Field(default=True, alias="FASHN_FALLBACK_TO_CPU_ON_OOM")

    output_dir: Path = Field(default=Path("outputs"), alias="OUTPUT_DIR")
    upload_dir: Path = Field(default=Path("uploads"), alias="UPLOAD_DIR")

    device: str = Field(default="auto", alias="DEVICE")
    mps_use_fp16: bool = Field(default=False, alias="MPS_USE_FP16")

    default_image_width: int = Field(default=1024, alias="DEFAULT_IMAGE_WIDTH")
    default_image_height: int = Field(default=1024, alias="DEFAULT_IMAGE_HEIGHT")

    non_cuda_force_fast_limits: bool = Field(default=True, alias="NON_CUDA_FORCE_FAST_LIMITS")
    non_cuda_max_count: int = Field(default=2, alias="NON_CUDA_MAX_COUNT")
    non_cuda_max_steps: int = Field(default=6, alias="NON_CUDA_MAX_STEPS")
    non_cuda_max_pixels: int = Field(default=1048576, alias="NON_CUDA_MAX_PIXELS")

    prompt_enhancement_enabled: bool = Field(default=True, alias="PROMPT_ENHANCEMENT_ENABLED")
    prompt_enhancement_template: str = Field(
        default=(
            "clean ecommerce catalog image of one complete {prompt}, {category}, entire garment fully visible "
            "from top to bottom with both sleeves, cuffs, hem, collar, hood, and all edges fully inside the frame, "
            "centered with generous white margin on every side, zoomed-out product photo, sleeves hanging naturally "
            "downward close to the body, plain white background, realistic fabric texture, balanced lighting, no person, "
            "no mannequin, no hanger, no body parts, not cropped, no close-up, no edge touching the image border"
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

        self.output_dir = self._resolve_project_path(self.output_dir)
        self.upload_dir = self._resolve_project_path(self.upload_dir)
        self.leffa_model_dir = self._resolve_project_path(self.leffa_model_dir)
        self.leffa_checkpoint_dir = self._resolve_project_path(self.leffa_checkpoint_dir)
        self.fashn_model_dir = self._resolve_project_path(self.fashn_model_dir)
        self.fashn_weights_dir = self._resolve_project_path(self.fashn_weights_dir)

        generated_dir = self.output_dir / "generated_clothes"
        tryon_dir = self.output_dir / "tryon_results"
        persons_dir = self.upload_dir / "persons"
        garments_dir = self.upload_dir / "garments"

        for directory in [
            self.output_dir,
            self.upload_dir,
            generated_dir,
            tryon_dir,
            persons_dir,
            garments_dir,
            self.leffa_model_dir.parent,
            self.leffa_checkpoint_dir,
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
