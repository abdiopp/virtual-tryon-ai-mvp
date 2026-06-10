"""Remote cloth generation service using Hugging Face Inference Providers."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import InferenceClient
from PIL import Image, ImageChops

from app.config import Settings, get_settings
from app.services.storage_service import StorageService
from app.utils.image_utils import save_image
from app.utils.logging_utils import get_logger

DEFAULT_NEGATIVE_PROMPT = (
    "low quality, blurry, distorted, deformed clothing, bad fabric texture, "
    "watermark, text, logo artifacts, human body, mannequin, duplicate sleeves, broken zipper, "
    "cropped garment, close-up fabric, partial clothing, cut off edges, out of frame, edge touching, "
    "sleeves cut off, cuffs cut off, hem cut off, zoomed-in product crop"
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
    """Service responsible for remote garment product image generation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = StorageService(self.settings)
        self.logger = get_logger(__name__)

    def is_model_available(self) -> bool:
        """Check whether remote cloth generation is configured."""

        return bool(
            self.settings.hf_token
            and self.settings.cloth_model_id
            and self.settings.cloth_inference_provider
        )

    def _enhance_prompt(self, prompt: str, category: str | None = None) -> str:
        """Optionally transform user prompt into product-style garment prompt."""

        clean_prompt = prompt.strip()
        if not self.settings.prompt_enhancement_enabled:
            return clean_prompt

        template = self.settings.prompt_enhancement_template
        category_value = (category or "garment").strip()
        return template.format(prompt=clean_prompt, category=category_value)

    def _is_flux_schnell_model(self, model_id: str) -> bool:
        normalized = model_id.lower()
        return "flux" in normalized and "schnell" in normalized

    def _tune_request_for_provider(
        self,
        count: int,
        width: int,
        height: int,
        guidance_scale: float,
        num_inference_steps: int,
    ) -> tuple[int, int, int, float, int, list[str]]:
        """Apply provider/model defaults without touching local hardware."""

        notes: list[str] = []
        tuned_count = count
        tuned_width = width
        tuned_height = height
        tuned_guidance = guidance_scale
        tuned_steps = num_inference_steps

        if self._is_flux_schnell_model(self.settings.cloth_model_id):
            if tuned_steps > 4:
                notes.append(f"num_inference_steps capped from {tuned_steps} to 4 for Flux Schnell")
                tuned_steps = 4
            if tuned_guidance != 0.0:
                notes.append("guidance_scale auto-set to 0.0 for Flux Schnell")
                tuned_guidance = 0.0

        return tuned_count, tuned_width, tuned_height, tuned_guidance, tuned_steps, notes

    def _build_client(self) -> InferenceClient:
        if not self.settings.hf_token:
            raise ClothGenerationError(
                "HF_TOKEN is required for remote cloth generation through Hugging Face Inference Providers."
            )

        return InferenceClient(
            provider=self.settings.cloth_inference_provider,
            api_key=self.settings.hf_token,
        )

    def _build_attempt_prompt(self, prompt: str, attempt_index: int) -> str:
        """Make retries increasingly explicit about full-garment framing."""

        if attempt_index <= 0:
            return prompt

        return (
            f"{prompt}. Critical composition: zoom out further, keep the entire garment small enough to fit "
            "comfortably inside the image, with at least 10 percent plain white empty space around the top, bottom, "
            "left, and right edges. Both sleeves and cuffs must be fully visible and must not touch or leave the frame."
        )

    def _content_bbox(self, image: Image.Image) -> tuple[int, int, int, int] | None:
        """Find non-white content bounds for catalog images on white backgrounds."""

        rgb_image = image.convert("RGB")
        white_background = Image.new("RGB", rgb_image.size, (255, 255, 255))
        difference = ImageChops.difference(rgb_image, white_background).convert("L")
        mask = difference.point(lambda value: 255 if value > 18 else 0)
        return mask.getbbox()

    def _margin_report(self, image: Image.Image) -> tuple[bool, str]:
        """Return whether generated garment content has enough border margin."""

        bbox = self._content_bbox(image)
        if bbox is None:
            return False, "no garment content detected"

        width, height = image.size
        left, top, right, bottom = bbox
        margin_ratio = max(0.0, min(self.settings.cloth_min_border_margin_ratio, 0.25))
        required_x = max(1, int(width * margin_ratio))
        required_y = max(1, int(height * margin_ratio))
        margins = {
            "left": left,
            "top": top,
            "right": width - right,
            "bottom": height - bottom,
        }
        failures = [
            side
            for side, margin in margins.items()
            if margin < (required_x if side in {"left", "right"} else required_y)
        ]
        if failures:
            margin_text = ", ".join(f"{side}={margin}" for side, margin in margins.items())
            return False, f"content too close to {', '.join(failures)} edge(s); margins: {margin_text}"

        return True, "content safely inside frame"

    def generate_clothes(
        self,
        prompt: str,
        category: str | None = None,
        negative_prompt: str | None = None,
        count: int = 1,
        width: int = 1024,
        height: int = 1024,
        guidance_scale: float = 0.0,
        num_inference_steps: int = 4,
        seed: int | None = None,
    ) -> list[ClothGenerationResultItem]:
        """Generate standalone garment product images on Hugging Face."""

        tuned = self._tune_request_for_provider(
            count=count,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
        )
        tuned_count, tuned_width, tuned_height, tuned_guidance, tuned_steps, notes = tuned

        if notes:
            self.logger.warning("Generation tuning applied: %s", "; ".join(notes))

        enhanced_prompt = self._enhance_prompt(prompt, category=category)
        active_negative_prompt = negative_prompt or DEFAULT_NEGATIVE_PROMPT
        client = self._build_client()

        results: list[ClothGenerationResultItem] = []
        base_seed = seed if seed is not None else random.randint(1, 2_000_000_000)
        request_started_at = time.monotonic()
        self.logger.info(
            "Starting remote cloth generation: model=%s provider=%s count=%d size=%dx%d steps=%d guidance=%.2f",
            self.settings.cloth_model_id,
            self.settings.cloth_inference_provider,
            tuned_count,
            tuned_width,
            tuned_height,
            tuned_steps,
            tuned_guidance,
        )

        for idx in range(tuned_count):
            item_seed = base_seed + idx if seed is not None else random.randint(1, 2_000_000_000)
            image_started_at = time.monotonic()
            self.logger.info(
                "Generating remote image %d/%d with seed=%d",
                idx + 1,
                tuned_count,
                item_seed,
            )

            attempts = max(1, self.settings.cloth_max_generation_attempts)
            image: Image.Image | None = None
            accepted_attempt = 1
            margin_report = "not checked"
            for attempt_index in range(attempts):
                attempt_seed = item_seed + attempt_index
                attempt_prompt = self._build_attempt_prompt(enhanced_prompt, attempt_index)
                try:
                    candidate = client.text_to_image(
                        attempt_prompt,
                        negative_prompt=active_negative_prompt,
                        height=tuned_height,
                        width=tuned_width,
                        num_inference_steps=tuned_steps,
                        guidance_scale=tuned_guidance,
                        model=self.settings.cloth_model_id,
                        seed=attempt_seed,
                    )
                except Exception as error:
                    raise ClothGenerationError(
                        "Hugging Face remote cloth generation failed. Confirm HF_TOKEN is valid, "
                        "the selected provider is enabled, and the model is accessible.\n"
                        f"Provider: {self.settings.cloth_inference_provider}\n"
                        f"Model: {self.settings.cloth_model_id}\n"
                        f"Original error: {error}"
                    ) from error

                image = candidate
                accepted_attempt = attempt_index + 1
                is_safe, margin_report = self._margin_report(candidate)
                if is_safe:
                    break
                self.logger.warning(
                    "Generated garment appears cropped on attempt %d/%d: %s",
                    accepted_attempt,
                    attempts,
                    margin_report,
                )

            if image is None:
                raise ClothGenerationError("Hugging Face remote cloth generation returned no image.")

            output_path = self.storage.build_output_path(
                subfolder="generated_clothes",
                prefix="cloth",
                extension=".png",
            )
            save_image(image, output_path)
            self.logger.info(
                "Completed remote image %d/%d in %.1fs -> %s",
                idx + 1,
                tuned_count,
                time.monotonic() - image_started_at,
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
                        "provider": self.settings.cloth_inference_provider,
                        "device": "huggingface",
                        "model_id": self.settings.cloth_model_id,
                        "performance_notes": " | ".join(notes) if notes else "none",
                        "crop_check": margin_report,
                        "generation_attempts": accepted_attempt,
                        "image_index": idx + 1,
                        "total_images": tuned_count,
                        "generation_seconds": round(time.monotonic() - image_started_at, 3),
                        "request_seconds": round(time.monotonic() - request_started_at, 3),
                    },
                )
            )

        self.logger.info(
            "Remote cloth generation request completed in %.1fs",
            time.monotonic() - request_started_at,
        )
        return results
