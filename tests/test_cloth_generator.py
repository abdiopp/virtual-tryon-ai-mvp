"""Tests for cloth model availability checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.services.cloth_generator import ClothGenerationError, ClothGeneratorService


def _make_settings() -> Settings:
    settings = Settings()
    settings.cloth_model_id = "stabilityai/stable-diffusion-xl-base-1.0"
    settings.model_cache_dir = Path("models/huggingface")
    settings.cloth_local_files_only = True
    return settings


def _create_cloth_snapshot(root: Path) -> Path:
    (root / "scheduler").mkdir(parents=True, exist_ok=True)
    (root / "tokenizer").mkdir(parents=True, exist_ok=True)
    (root / "unet").mkdir(parents=True, exist_ok=True)
    (root / "model_index.json").write_text("{}", encoding="utf-8")
    (root / "unet" / "config.json").write_text("{}", encoding="utf-8")
    (root / "unet" / "diffusion_pytorch_model.safetensors").write_bytes(b"fake-weights")
    return root


def test_cloth_model_available_for_complete_local_snapshot(tmp_path: Path) -> None:
    model_dir = _create_cloth_snapshot(tmp_path / "sdxl")

    settings = _make_settings()
    settings.cloth_model_id = str(model_dir)

    service = ClothGeneratorService(settings)

    assert service.is_model_available() is True


def test_cloth_model_available_rejects_incomplete_local_snapshot(tmp_path: Path) -> None:
    model_dir = tmp_path / "sdxl"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "model_index.json").write_text("{}", encoding="utf-8")

    settings = _make_settings()
    settings.cloth_model_id = str(model_dir)

    service = ClothGeneratorService(settings)

    assert service.is_model_available() is False


def test_resolve_model_source_rejects_incomplete_local_snapshot(tmp_path: Path) -> None:
    model_dir = tmp_path / "sdxl"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "model_index.json").write_text("{}", encoding="utf-8")

    settings = _make_settings()
    settings.cloth_model_id = str(model_dir)

    service = ClothGeneratorService(settings)

    with pytest.raises(ClothGenerationError, match="cache is incomplete"):
        service._resolve_model_source()
