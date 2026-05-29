"""Tests for image utility helpers."""

from pathlib import Path

from PIL import Image

from app.utils.image_utils import create_full_white_mask, resize_and_center_crop


def test_resize_and_center_crop_returns_expected_size() -> None:
    image = Image.new("RGB", (200, 100), (10, 20, 30))
    resized = resize_and_center_crop(image, width=64, height=64)
    assert resized.size == (64, 64)


def test_create_full_white_mask_creates_expected_image(tmp_path: Path) -> None:
    output_path = tmp_path / "mask.png"
    created = create_full_white_mask(output_path, width=32, height=48)

    assert created.exists()
    with Image.open(created) as mask:
        assert mask.mode == "L"
        assert mask.size == (32, 48)
        assert mask.getbbox() == (0, 0, 32, 48)
