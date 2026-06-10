"""Tests for remote cloth generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.config import Settings
from app.services import cloth_generator
from app.services.cloth_generator import ClothGenerationError, ClothGeneratorService


def _make_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        HF_TOKEN="hf_test_token",
        CLOTH_MODEL_ID="black-forest-labs/FLUX.1-schnell",
        CLOTH_INFERENCE_PROVIDER="nscale",
        OUTPUT_DIR=tmp_path / "outputs",
        UPLOAD_DIR=tmp_path / "uploads",
    )
    settings.ensure_directories()
    return settings


def test_cloth_model_available_requires_remote_provider_and_token(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)

    assert ClothGeneratorService(settings).is_model_available() is True

    settings.hf_token = None
    assert ClothGeneratorService(settings).is_model_available() is False


def test_flux_tuning_uses_fast_remote_defaults(tmp_path: Path) -> None:
    service = ClothGeneratorService(_make_settings(tmp_path))

    tuned = service._tune_request_for_provider(
        count=1,
        width=1024,
        height=1024,
        guidance_scale=7.0,
        num_inference_steps=30,
    )

    assert tuned[:5] == (1, 1024, 1024, 0.0, 4)
    assert "Flux Schnell" in " ".join(tuned[5])


def test_remote_generation_calls_huggingface_inference_client(monkeypatch, tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    calls: dict[str, object] = {}

    class FakeInferenceClient:
        def __init__(self, *, provider: str, api_key: str) -> None:
            calls["client"] = {"provider": provider, "api_key": api_key}

        def text_to_image(self, prompt: str, **kwargs: object) -> Image.Image:
            calls["text_to_image"] = {"prompt": prompt, **kwargs}
            image = Image.new("RGB", (1024, 1024), "white")
            for x in range(160, 864):
                for y in range(160, 864):
                    image.putpixel((x, y), (12, 34, 56))
            return image

    monkeypatch.setattr(cloth_generator, "InferenceClient", FakeInferenceClient)

    result = ClothGeneratorService(settings).generate_clothes(
        prompt="oversized black hoodie",
        category="hoodie",
        guidance_scale=7.0,
        num_inference_steps=30,
        seed=123,
    )[0]

    output_path = Path(result.path)
    assert output_path.exists()
    assert Image.open(output_path).size == (1024, 1024)
    assert calls["client"] == {"provider": "nscale", "api_key": "hf_test_token"}
    assert calls["text_to_image"] == {
        "prompt": result.prompt,
        "negative_prompt": (
            "low quality, blurry, distorted, deformed clothing, bad fabric texture, "
            "watermark, text, logo artifacts, human body, mannequin, duplicate sleeves, broken zipper, "
            "cropped garment, close-up fabric, partial clothing, cut off edges, out of frame, edge touching, "
            "sleeves cut off, cuffs cut off, hem cut off, zoomed-in product crop"
        ),
        "height": 1024,
        "width": 1024,
        "num_inference_steps": 4,
        "guidance_scale": 0.0,
        "model": "black-forest-labs/FLUX.1-schnell",
        "seed": 123,
    }
    assert result.metadata["provider"] == "nscale"
    assert result.metadata["device"] == "huggingface"
    assert result.metadata["crop_check"] == "content safely inside frame"
    assert result.metadata["generation_attempts"] == 1


def test_remote_generation_retries_when_garment_touches_border(monkeypatch, tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    calls: list[dict[str, object]] = []

    class FakeInferenceClient:
        def __init__(self, *, provider: str, api_key: str) -> None:
            pass

        def text_to_image(self, prompt: str, **kwargs: object) -> Image.Image:
            calls.append({"prompt": prompt, **kwargs})
            image = Image.new("RGB", (1024, 1024), "white")
            if len(calls) == 1:
                box = (0, 120, 1024, 1000)
            else:
                box = (180, 160, 844, 864)
            for x in range(box[0], box[2]):
                for y in range(box[1], box[3]):
                    image.putpixel((x, y), (10, 10, 10))
            return image

    monkeypatch.setattr(cloth_generator, "InferenceClient", FakeInferenceClient)

    result = ClothGeneratorService(settings).generate_clothes(
        prompt="black hoodie",
        category="hoodie",
        seed=10,
    )[0]

    assert len(calls) == 2
    assert calls[0]["seed"] == 10
    assert calls[1]["seed"] == 11
    assert "zoom out further" in str(calls[1]["prompt"])
    assert result.metadata["generation_attempts"] == 2
    assert result.metadata["crop_check"] == "content safely inside frame"


def test_margin_report_rejects_content_touching_image_edge(tmp_path: Path) -> None:
    service = ClothGeneratorService(_make_settings(tmp_path))
    cropped = Image.new("RGB", (100, 100), "white")
    safe = Image.new("RGB", (100, 100), "white")
    for x in range(0, 90):
        for y in range(20, 80):
            cropped.putpixel((x, y), (0, 0, 0))
    for x in range(20, 80):
        for y in range(20, 80):
            safe.putpixel((x, y), (0, 0, 0))

    assert service._margin_report(cropped)[0] is False
    assert service._margin_report(safe) == (True, "content safely inside frame")


def test_remote_generation_requires_hf_token(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    settings.hf_token = None

    with pytest.raises(ClothGenerationError, match="HF_TOKEN is required"):
        ClothGeneratorService(settings).generate_clothes(prompt="black hoodie")
