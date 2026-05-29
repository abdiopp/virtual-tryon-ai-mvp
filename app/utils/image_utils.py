"""Image helpers used by API services and scripts."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def ensure_image_exists(image_path: Path | str) -> Path:
    """Validate that an image path exists on disk."""

    path = Path(image_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    return path


def load_rgb_image(image_path: Path | str) -> Image.Image:
    """Open image and convert to RGB."""

    path = ensure_image_exists(image_path)
    return Image.open(path).convert("RGB")


def resize_and_center_crop(image: Image.Image, width: int, height: int) -> Image.Image:
    """Resize while preserving aspect ratio, then center-crop to target size."""

    target_ratio = width / height
    img_ratio = image.width / image.height

    if img_ratio > target_ratio:
        new_height = height
        new_width = int(height * img_ratio)
    else:
        new_width = width
        new_height = int(width / img_ratio)

    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = max((new_width - width) // 2, 0)
    top = max((new_height - height) // 2, 0)
    right = left + width
    bottom = top + height
    return resized.crop((left, top, right, bottom))


def resize_with_padding(
    image: Image.Image,
    width: int,
    height: int,
    background_color: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Resize to fit inside target size while preserving aspect ratio and add padding."""

    image_copy = image.copy()
    image_copy.thumbnail((width, height), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (width, height), background_color)
    offset_x = (width - image_copy.width) // 2
    offset_y = (height - image_copy.height) // 2
    canvas.paste(image_copy, (offset_x, offset_y))
    return canvas


def save_image(image: Image.Image, output_path: Path | str, image_format: str = "PNG") -> Path:
    """Save image to disk and ensure parent directory exists."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format=image_format)
    return path


def create_full_white_mask(output_path: Path | str, width: int, height: int) -> Path:
    """Create a full-white grayscale mask utility for try-on preprocessing workflows."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mask = Image.new("L", (width, height), 255)
    mask.save(path, format="PNG")
    return path
