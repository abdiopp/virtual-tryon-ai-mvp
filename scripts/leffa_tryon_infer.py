"""Single-image Leffa virtual try-on inference runner.

This script is intentionally isolated from the FastAPI process because Leffa
loads several heavy preprocessing and diffusion modules. Keeping it in a
subprocess lets the API release GPU memory between requests on Colab.
"""

from __future__ import annotations

import argparse
import contextlib
import inspect
import os
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image


LEFFA_CATEGORY_MAP = {
    "upper_body": "upper_body",
    "upper": "upper_body",
    "top": "upper_body",
    "tops": "upper_body",
    "lower_body": "lower_body",
    "lower": "lower_body",
    "bottom": "lower_body",
    "bottoms": "lower_body",
    "dress": "dresses",
    "dresses": "dresses",
    "one-pieces": "dresses",
    "overall": "dresses",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Run Leffa virtual try-on for one image pair.")
    parser.add_argument("--repo-dir", required=True, help="Path to cloned Leffa repository")
    parser.add_argument("--checkpoint-dir", required=True, help="Path to downloaded Leffa checkpoints")
    parser.add_argument("--person-image", required=True, help="Path to person image")
    parser.add_argument("--garment-image", required=True, help="Path to garment image")
    parser.add_argument("--category", default="upper_body", help="upper_body | lower_body | dress")
    parser.add_argument("--output-path", required=True, help="Where to write the generated try-on PNG")
    parser.add_argument("--num-inference-steps", type=int, default=30)
    parser.add_argument("--guidance-scale", type=float, default=2.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-type", default="auto", choices=["auto", "viton_hd", "dress_code"])
    parser.add_argument("--ref-acceleration", action="store_true")
    parser.add_argument("--repaint", action="store_true")
    parser.add_argument("--preprocess-garment", action="store_true")
    parser.add_argument("--require-cuda", action="store_true")
    parser.add_argument("--memory-efficient-load", action="store_true")
    return parser.parse_args()


def normalize_category(category: str) -> str:
    """Return Leffa's category name."""

    normalized = category.strip().lower()
    if normalized not in LEFFA_CATEGORY_MAP:
        raise ValueError("Invalid category. Use one of: upper_body, lower_body, dress.")
    return LEFFA_CATEGORY_MAP[normalized]


def resolve_model_type(model_type: str, category: str) -> str:
    """Choose the Leffa checkpoint family for the requested garment type."""

    if model_type != "auto":
        return model_type
    return "viton_hd" if category == "upper_body" else "dress_code"


def load_repo_modules(repo_dir: Path) -> None:
    """Make Leffa repository modules importable."""

    resolved_repo = repo_dir.resolve()
    if str(resolved_repo) not in sys.path:
        sys.path.insert(0, str(resolved_repo))
    os.chdir(resolved_repo)


def report_memory(label: str) -> None:
    """Print lightweight memory diagnostics when the optional deps are present."""

    details: list[str] = []
    try:
        import psutil

        rss_gb = psutil.Process(os.getpid()).memory_info().rss / (1024**3)
        details.append(f"rss={rss_gb:.2f}GB")
    except Exception:
        pass

    if torch.cuda.is_available():
        allocated_gb = torch.cuda.memory_allocated() / (1024**3)
        reserved_gb = torch.cuda.memory_reserved() / (1024**3)
        details.append(f"cuda_allocated={allocated_gb:.2f}GB")
        details.append(f"cuda_reserved={reserved_gb:.2f}GB")

    suffix = f" ({', '.join(details)})" if details else ""
    print(f"Leffa memory {label}{suffix}", flush=True)


@contextlib.contextmanager
def memory_efficient_torch_load(enabled: bool):
    """Use lower-memory torch.load options when the installed PyTorch supports them."""

    if not enabled:
        yield
        return

    original_load = torch.load
    supported_parameters = inspect.signature(torch.load).parameters

    def patched_load(f, *args, **kwargs):
        if "weights_only" in supported_parameters:
            kwargs.setdefault("weights_only", True)
        if "mmap" in supported_parameters and isinstance(f, (str, os.PathLike)):
            kwargs.setdefault("mmap", True)
        try:
            return original_load(f, *args, **kwargs)
        except TypeError:
            kwargs.pop("weights_only", None)
            kwargs.pop("mmap", None)
            return original_load(f, *args, **kwargs)

    torch.load = patched_load
    try:
        yield
    finally:
        torch.load = original_load


def main() -> int:
    """Run Leffa inference and write the generated image."""

    args = parse_args()
    repo_dir = Path(args.repo_dir)
    checkpoint_dir = Path(args.checkpoint_dir)
    person_path = Path(args.person_image)
    garment_path = Path(args.garment_image)
    output_path = Path(args.output_path)

    category = normalize_category(args.category)
    model_type = resolve_model_type(args.model_type, category)
    checkpoint_name = "virtual_tryon.pth" if model_type == "viton_hd" else "virtual_tryon_dc.pth"

    if args.require_cuda and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available, but Leffa was started with --require-cuda. "
            "In Colab, choose Runtime > Change runtime type > GPU and restart the runtime."
        )

    report_memory("startup")
    load_repo_modules(repo_dir)

    print("Leffa importing modules", flush=True)
    from leffa.inference import LeffaInference
    from leffa.model import LeffaModel
    from leffa.transform import LeffaTransform
    from leffa_utils.densepose_predictor import DensePosePredictor
    from leffa_utils.utils import (
        get_agnostic_mask_dc,
        get_agnostic_mask_hd,
        preprocess_garment_image,
        resize_and_center,
    )
    from preprocess.humanparsing.run_parsing import Parsing
    from preprocess.openpose.run_openpose import OpenPose
    report_memory("after imports")

    torch.backends.cuda.matmul.allow_tf32 = torch.cuda.is_available()
    torch.backends.cudnn.allow_tf32 = torch.cuda.is_available()

    print(f"Leffa loading checkpoints from {checkpoint_dir}", flush=True)
    dtype = "float16" if torch.cuda.is_available() else "float32"

    with memory_efficient_torch_load(args.memory_efficient_load):
        print(
            "Leffa building diffusion model "
            f"checkpoint={checkpoint_name} dtype={dtype} memory_efficient_load={args.memory_efficient_load}",
            flush=True,
        )
        model = LeffaModel(
            pretrained_model_name_or_path=str((checkpoint_dir / "stable-diffusion-inpainting").resolve()),
            pretrained_model=str((checkpoint_dir / checkpoint_name).resolve()),
            dtype=dtype,
        )
    report_memory("after diffusion model load")

    print("Leffa moving diffusion model to runtime device", flush=True)
    inference = LeffaInference(model=model)
    report_memory("after diffusion model device move")

    print("Leffa loading preprocessing models", flush=True)
    parsing = Parsing(
        atr_path=str((checkpoint_dir / "humanparsing" / "parsing_atr.onnx").resolve()),
        lip_path=str((checkpoint_dir / "humanparsing" / "parsing_lip.onnx").resolve()),
    )
    openpose = OpenPose(
        body_model_path=str((checkpoint_dir / "openpose" / "body_pose_model.pth").resolve()),
    )
    densepose_predictor = DensePosePredictor(
        config_path=str((checkpoint_dir / "densepose" / "densepose_rcnn_R_50_FPN_s1x.yaml").resolve()),
        weights_path=str((checkpoint_dir / "densepose" / "model_final_162be9.pkl").resolve()),
    )
    report_memory("after preprocessing models load")

    print(f"Leffa preprocessing person={person_path} garment={garment_path}", flush=True)
    src_image = Image.open(person_path).convert("RGB")
    src_image = resize_and_center(src_image, 768, 1024)

    if args.preprocess_garment:
        if garment_path.suffix.lower() != ".png":
            raise ValueError("Leffa garment preprocessing expects a PNG garment image.")
        ref_image = preprocess_garment_image(str(garment_path))
    else:
        ref_image = Image.open(garment_path).convert("RGB")
        ref_image = resize_and_center(ref_image, 768, 1024)

    src_image_array = np.array(src_image)

    print(f"Leffa building mask category={category} model_type={model_type}", flush=True)
    model_parse, _ = parsing(src_image.resize((384, 512)))
    keypoints = openpose(src_image.resize((384, 512)))
    if model_type == "viton_hd":
        mask = get_agnostic_mask_hd(model_parse, keypoints, category)
        src_image_seg_array = densepose_predictor.predict_seg(src_image_array)[:, :, ::-1]
        densepose = Image.fromarray(src_image_seg_array)
    else:
        mask = get_agnostic_mask_dc(model_parse, keypoints, category)
        src_image_iuv_array = densepose_predictor.predict_iuv(src_image_array)
        src_image_seg_array = src_image_iuv_array[:, :, 0:1]
        src_image_seg_array = np.concatenate([src_image_seg_array] * 3, axis=-1)
        densepose = Image.fromarray(src_image_seg_array)
    mask = mask.resize((768, 1024))

    data = {
        "src_image": [src_image],
        "ref_image": [ref_image],
        "mask": [mask],
        "densepose": [densepose],
    }
    data = LeffaTransform()(data)

    print(
        "Leffa running diffusion "
        f"steps={args.num_inference_steps} guidance={args.guidance_scale} seed={args.seed}",
        flush=True,
    )
    output = inference(
        data,
        ref_acceleration=args.ref_acceleration,
        num_inference_steps=args.num_inference_steps,
        guidance_scale=args.guidance_scale,
        seed=args.seed,
        repaint=args.repaint,
    )
    generated_image = output["generated_image"][0]
    if not isinstance(generated_image, Image.Image):
        generated_image = Image.fromarray(np.asarray(generated_image))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_image.save(output_path)
    print(f"Leffa output saved to {output_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
