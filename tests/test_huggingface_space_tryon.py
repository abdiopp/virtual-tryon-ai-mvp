"""Tests for Hugging Face Space virtual try-on backend."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.services.tryon_service import (
    HuggingFaceSpaceTryOnService,
    get_tryon_service,
    normalize_tryon_backend,
)


def _settings(tmp_path: Path) -> Settings:
    settings = Settings(
        HF_TOKEN="",
        TRYON_BACKEND="huggingface_space",
        OUTPUT_DIR=tmp_path / "outputs",
        UPLOAD_DIR=tmp_path / "uploads",
    )
    settings.ensure_directories()
    return settings


def test_huggingface_aliases_normalize_to_space_backend() -> None:
    assert normalize_tryon_backend("hf") == "huggingface_space"
    assert normalize_tryon_backend("huggingface") == "huggingface_space"
    assert normalize_tryon_backend("idm-vton") == "huggingface_space"


def test_get_tryon_service_uses_huggingface_space_backend(tmp_path: Path) -> None:
    service = get_tryon_service(_settings(tmp_path))

    assert isinstance(service, HuggingFaceSpaceTryOnService)
    assert service.is_model_available() is True


def test_huggingface_space_tryon_copies_remote_output(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    person_path = tmp_path / "person.png"
    garment_path = tmp_path / "garment.png"
    remote_output_path = tmp_path / "remote_output.png"
    person_path.write_bytes(b"person")
    garment_path.write_bytes(b"garment")
    remote_output_path.write_bytes(b"remote-output")

    calls: dict[str, object] = {}

    class FakeClient:
        def __init__(self, src: str, token: str | None, verbose: bool, download_files: Path) -> None:
            calls["client"] = {
                "src": src,
                "token": token,
                "verbose": verbose,
                "download_files": download_files,
            }

        def predict(self, **kwargs: object) -> tuple[str, str]:
            calls["predict"] = kwargs
            return (str(remote_output_path), str(tmp_path / "mask.png"))

    def fake_file(path: str) -> str:
        return f"file:{path}"

    monkeypatch.setitem(
        sys.modules,
        "gradio_client",
        SimpleNamespace(Client=FakeClient, file=fake_file),
    )

    service = HuggingFaceSpaceTryOnService(settings)
    result = service.run_tryon(person_path, garment_path, category="upper_body")

    result_path = Path(result.result_path)
    assert result_path.read_bytes() == b"remote-output"
    assert result.metadata["tryon_backend"] == "huggingface_space"
    assert result.metadata["runtime_device"] == "huggingface"
    assert result.metadata["space_id"] == "yisol/IDM-VTON"
    assert calls["client"] == {
        "src": "yisol/IDM-VTON",
        "token": None,
        "verbose": False,
        "download_files": result_path.parent,
    }
    assert calls["predict"] == {
        "dict": {
            "background": f"file:{person_path}",
            "layers": [],
            "composite": None,
        },
        "garm_img": f"file:{garment_path}",
        "garment_des": "upper body garment",
        "is_checked": True,
        "is_checked_crop": False,
        "denoise_steps": 30,
        "seed": 42,
        "api_name": "/tryon",
    }
