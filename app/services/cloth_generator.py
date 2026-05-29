"""Lightweight cloth generation service using Diffusers text-to-image pipelines."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from pathlib import Path

import torch
from diffusers import AutoPipelineForText2Image, DiffusionPipeline
from huggingface_hub import snapshot_download

from app.config import Settings, get_settings
from app.services.storage_service import StorageService
from app.utils.device import require_cuda_if_requested, resolve_device
from app.utils.image_utils import save_image
from app.utils.logging_utils import get_logger

DEFAULT_NEGATIVE_PROMPT = (
    "low quality, blurry, distorted, deformed clothing, bad fabric texture, "
    "watermark, text, logo artifacts, human body, mannequin, duplicate sleeves, broken zipper"
)


class ClothGenerationError(RuntimeError):
    """Raised when cloth generation cannot proceed."""


@dataclass
class ClothGenerationResultItem:
    """Generated cloth output metadata."""

    id: str
    path: str
    prompt: str
    seed: int | None
    metadata: dict[str, str | int | float]


class ClothGeneratorService:
    """Service responsible for fast garment product image generation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.device = resolve_device(self.settings.device)
        self.storage = StorageService(self.settings)
        self.logger = get_logger(__name__)
        self.pipeline: DiffusionPipeline | None = None

    def is_model_available(self) -> bool:
        """Check whether cloth generation model exists locally."""

        model_path = Path(self.settings.cloth_model_id)
        if model_path.exists() and (model_path / "model_index.json").exists():
            return True

        try:
            snapshot_download(
                repo_id=self.settings.cloth_model_id,
                cache_dir=str(self.settings.model_cache_dir),
                allow_patterns=["model_index.json"],
                local_files_only=True,
                token=self.settings.hf_token,
            )
            return True
        except Exception:
            return False

    def _enhance_prompt(self, prompt: str, category: str | None = None) -> str:
        """Optionally transform user prompt into product-style garment prompt."""

        clean_prompt = prompt.strip()
        if not self.settings.prompt_enhancement_enabled:
            return clean_prompt

        template = self.settings.prompt_enhancement_template
        category_value = (category or "garment").strip()
        return template.format(prompt=clean_prompt, category=category_value)

    def _resolve_model_source(self) -> str:
        """Resolve local model source path when local-only mode is enabled."""

        model_path = Path(self.settings.cloth_model_id)
        if model_path.exists() and (model_path / "model_index.json").exists():
            return str(model_path)

        if self.settings.cloth_local_files_only:
            try:
                local_snapshot = snapshot_download(
                    repo_id=self.settings.cloth_model_id,
                    cache_dir=str(self.settings.model_cache_dir),
                    allow_patterns=["model_index.json"],
                    local_files_only=True,
                    token=self.settings.hf_token,
                )
                return local_snapshot
            except Exception as error:
                raise ClothGenerationError(
                    "CLOTH_LOCAL_FILES_ONLY is enabled but model is not fully cached. "
                    "Run `python scripts/download_models.py --only-clothes` first, or set "
                    "CLOTH_LOCAL_FILES_ONLY=false."
                ) from error

        return self.settings.cloth_model_id

    def _is_turbo_model(self, model_id: str) -> bool:
        return "turbo" in model_id.lower()

    def _is_sdxl_base_model(self, model_id: str) -> bool:
        model_id_lower = model_id.lower()
        return "sdxl" in model_id_lower or "stable-diffusion-xl" in model_id_lower

    def _resolve_dtype(self) -> torch.dtype:
        if self.device == "cuda":
            return torch.float16
        if self.device == "mps" and self.settings.mps_use_fp16:
            return torch.float16
        return torch.float32

    def _load_pipeline(self) -> DiffusionPipeline:
        """Lazy-load text-to-image pipeline."""

        if self.pipeline is not None:
            return self.pipeline

        require_cuda_if_requested(self.settings.device)

        dtype = self._resolve_dtype()
        model_source = self._resolve_model_source()
        load_kwargs: dict[str, object] = {
            "torch_dtype": dtype,
            "cache_dir": str(self.settings.model_cache_dir),
            "use_safetensors": True,
            "local_files_only": self.settings.cloth_local_files_only,
        }
        if self.device == "cuda":
            load_kwargs["variant"] = "fp16"

        try:
            pipeline = AutoPipelineForText2Image.from_pretrained(model_source, **load_kwargs)
        except Exception as first_error:
            if "variant" in load_kwargs:
                load_kwargs.pop("variant")
                try:
                    pipeline = AutoPipelineForText2Image.from_pretrained(model_source, **load_kwargs)
                except Exception as second_error:
                    raise ClothGenerationError(
                        "Failed to load cloth generation model. "
                        "Run `python scripts/download_models.py --only-clothes` and retry."
                    ) from second_error
            else:
                raise ClothGenerationError(
                    "Failed to load cloth generation model. "
                    "Run `python scripts/download_models.py --only-clothes` and retry."
                ) from first_error

        if self.settings.cloth_lora_path:
            lora_path = Path(self.settings.cloth_lora_path)
            if not lora_path.exists():
                raise ClothGenerationError(f"Configured CLOTH_LORA_PATH does not exist: {lora_path}")
            try:
                pipeline.load_lora_weights(str(lora_path))
                self.logger.info("Loaded LoRA weights from %s", lora_path)
            except Exception as error:
                raise ClothGenerationError(
                    f"Unable to load LoRA weights from {lora_path}: {error}"
                ) from error

        pipeline = pipeline.to(self.device)
        pipeline.set_progress_bar_config(disable=True)
        pipeline.enable_vae_slicing()
        if self.device != "cuda":
            pipeline.enable_attention_slicing()

        self.pipeline = pipeline
        self.logger.info(
            "Cloth pipeline loaded on device=%s | dtype=%s | source=%s",
            self.device,
            dtype,
            model_source,
        )
        return self.pipeline

    def _fit_to_non_cuda_pixel_budget(self, width: int, height: int) -> tuple[int, int]:
        """Downscale dimensions to respect configured non-CUDA pixel budget."""

        max_pixels = self.settings.non_cuda_max_pixels
        pixels = width * height
        if pixels <= max_pixels:
            return width, height

        scale = math.sqrt(max_pixels / pixels)
        resized_w = max(256, int((width * scale) // 64) * 64)
        resized_h = max(256, int((height * scale) // 64) * 64)
        return resized_w, resized_h

    def _enforce_sdxl_quality_guardrails(
        self,
        width: int,
        height: int,
        guidance_scale: float,
        num_inference_steps: int,
        notes: list[str],
    ) -> tuple[int, int, float, int]:
        """Prevent low-step SDXL settings that commonly produce distorted outputs."""

        tuned_width = width
        tuned_height = height
        tuned_guidance = guidance_scale
        tuned_steps = num_inference_steps

        if tuned_width < 512 or tuned_height < 512:
            tuned_width = max(512, int(math.ceil(tuned_width / 64) * 64))
            tuned_height = max(512, int(math.ceil(tuned_height / 64) * 64))
            notes.append(
                f"resolution upscaled for SDXL quality from {width}x{height} to {tuned_width}x{tuned_height}"
            )

        minimum_steps = 18 if self.device == "cuda" else 14
        if tuned_steps < minimum_steps:
            notes.append(
                f"num_inference_steps raised from {tuned_steps} to {minimum_steps} for SDXL quality guardrails"
            )
            tuned_steps = minimum_steps

        minimum_guidance = 5.5
        if tuned_guidance < minimum_guidance:
            notes.append(
                f"guidance_scale raised from {tuned_guidance} to {minimum_guidance} for SDXL quality guardrails"
            )
            tuned_guidance = minimum_guidance

        return tuned_width, tuned_height, tuned_guidance, tuned_steps

    def _tune_request_for_performance(
        self,
        count: int,
        width: int,
        height: int,
        guidance_scale: float,
        num_inference_steps: int,
    ) -> tuple[int, int, int, float, int, list[str]]:
        """Apply speed-safe limits on non-CUDA devices."""

        notes: list[str] = []
        model_id = self.settings.cloth_model_id
        is_turbo = self._is_turbo_model(model_id)
        is_sdxl_base = self._is_sdxl_base_model(model_id)

        tuned_count = count
        tuned_width = width
        tuned_height = height
        tuned_guidance = guidance_scale
        tuned_steps = num_inference_steps

        if is_sdxl_base:
            tuned_width, tuned_height, tuned_guidance, tuned_steps = (
                self._enforce_sdxl_quality_guardrails(
                    width=tuned_width,
                    height=tuned_height,
                    guidance_scale=tuned_guidance,
                    num_inference_steps=tuned_steps,
                    notes=notes,
                )
            )

        if self.device != "cuda" and self.settings.non_cuda_force_fast_limits:
            max_count = max(1, self.settings.non_cuda_max_count)
            if tuned_count > max_count:
                notes.append(f"count capped from {tuned_count} to {max_count}")
                tuned_count = max_count

            # Keep SDXL quality guardrails intact; only cap non-SDXL models.
            if not is_sdxl_base:
                max_steps = max(1, self.settings.non_cuda_max_steps)
                if is_turbo:
                    max_steps = min(max_steps, 4)
                if tuned_steps > max_steps:
                    notes.append(f"num_inference_steps capped from {tuned_steps} to {max_steps}")
                    tuned_steps = max_steps

            adjusted_w, adjusted_h = self._fit_to_non_cuda_pixel_budget(tuned_width, tuned_height)
            if adjusted_w != tuned_width or adjusted_h != tuned_height:
                notes.append(
                    f"resolution downscaled from {tuned_width}x{tuned_height} to {adjusted_w}x{adjusted_h}"
                )
                tuned_width, tuned_height = adjusted_w, adjusted_h

        if is_turbo and tuned_guidance != 0.0:
            notes.append(
                "guidance_scale auto-set to 0.0 for turbo model best speed/quality behavior"
            )
            tuned_guidance = 0.0

        return tuned_count, tuned_width, tuned_height, tuned_guidance, tuned_steps, notes

    def _build_generator(self, seed: int) -> torch.Generator:
        """Create deterministic generator compatible with current backend."""

        if self.device == "cuda":
            return torch.Generator(device="cuda").manual_seed(seed)

        # MPS historically does not support torch.Generator("mps") reliably.
        return torch.Generator(device="cpu").manual_seed(seed)

    def _run_pipeline_with_progress(
        self,
        pipeline: DiffusionPipeline,
        pipe_kwargs: dict[str, object],
        image_index: int,
        total_images: int,
        total_steps: int,
    ):
        """Run pipeline and emit periodic step progress logs."""

        log_interval = max(1, total_steps // 4)
        started_at = time.time()

        def _log_step(step_number: int) -> None:
            if step_number == 1 or step_number == total_steps or step_number % log_interval == 0:
                elapsed = time.time() - started_at
                percent = (step_number / total_steps) * 100
                self.logger.info(
                    "Cloth generation progress image %d/%d step %d/%d (%.0f%%) elapsed=%.1fs",
                    image_index,
                    total_images,
                    step_number,
                    total_steps,
                    percent,
                    elapsed,
                )

        def _step_end_callback(_pipe, step_index, _timestep, callback_kwargs):
            _log_step(step_index + 1)
            return callback_kwargs

        try:
            return pipeline(
                **pipe_kwargs,
                callback_on_step_end=_step_end_callback,
                callback_on_step_end_tensor_inputs=[],
            )
        except TypeError:
            self.logger.info(
                "Falling back to legacy diffusers callback API for progress logging."
            )

            def _legacy_callback(step_index, _timestep, _latents):
                _log_step(step_index + 1)

            return pipeline(
                **pipe_kwargs,
                callback=_legacy_callback,
                callback_steps=max(1, log_interval),
            )

    def generate_clothes(
        self,
        prompt: str,
        category: str | None = None,
        negative_prompt: str | None = None,
        count: int = 1,
        width: int = 512,
        height: int = 768,
        guidance_scale: float = 0.0,
        num_inference_steps: int = 4,
        seed: int | None = None,
    ) -> list[ClothGenerationResultItem]:
        """Generate standalone garment product images with fast defaults."""

        pipeline = self._load_pipeline()

        tuned = self._tune_request_for_performance(
            count=count,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
        )
        tuned_count, tuned_width, tuned_height, tuned_guidance, tuned_steps, notes = tuned

        if notes:
            self.logger.warning("Performance tuning applied: %s", "; ".join(notes))

        enhanced_prompt = self._enhance_prompt(prompt, category=category)
        active_negative_prompt = negative_prompt or DEFAULT_NEGATIVE_PROMPT

        results: list[ClothGenerationResultItem] = []
        base_seed = seed if seed is not None else random.randint(1, 2_000_000_000)
        request_started_at = time.time()
        self.logger.info(
            "Starting cloth generation: model=%s device=%s count=%d size=%dx%d steps=%d guidance=%.2f",
            self.settings.cloth_model_id,
            self.device,
            tuned_count,
            tuned_width,
            tuned_height,
            tuned_steps,
            tuned_guidance,
        )

        for idx in range(tuned_count):
            item_seed = base_seed + idx if seed is not None else random.randint(1, 2_000_000_000)
            generator = self._build_generator(item_seed)
            image_started_at = time.time()
            self.logger.info(
                "Generating image %d/%d with seed=%d",
                idx + 1,
                tuned_count,
                item_seed,
            )

            pipe_kwargs: dict[str, object] = {
                "prompt": enhanced_prompt,
                "width": tuned_width,
                "height": tuned_height,
                "guidance_scale": tuned_guidance,
                "num_inference_steps": tuned_steps,
                "generator": generator,
            }
            if tuned_guidance > 0.0:
                pipe_kwargs["negative_prompt"] = active_negative_prompt

            image = self._run_pipeline_with_progress(
                pipeline=pipeline,
                pipe_kwargs=pipe_kwargs,
                image_index=idx + 1,
                total_images=tuned_count,
                total_steps=tuned_steps,
            ).images[0]

            output_path = self.storage.build_output_path(
                subfolder="generated_clothes",
                prefix="cloth",
                extension=".png",
            )
            save_image(image, output_path)
            self.logger.info(
                "Completed image %d/%d in %.1fs -> %s",
                idx + 1,
                tuned_count,
                time.time() - image_started_at,
                output_path,
            )

            results.append(
                ClothGenerationResultItem(
                    id=output_path.stem,
                    path=str(output_path),
                    prompt=enhanced_prompt,
                    seed=item_seed,
                    metadata={
                        "category": category or "unknown",
                        "width": tuned_width,
                        "height": tuned_height,
                        "guidance_scale": tuned_guidance,
                        "num_inference_steps": tuned_steps,
                        "device": self.device,
                        "model_id": self.settings.cloth_model_id,
                        "performance_notes": " | ".join(notes) if notes else "none",
                    },
                )
            )

        self.logger.info(
            "Cloth generation request completed in %.1fs",
            time.time() - request_started_at,
        )
        return results
