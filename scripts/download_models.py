"""Download and prepare lightweight cloth + try-on assets for local MVP usage."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import hf_hub_download, login, snapshot_download
from huggingface_hub.errors import GatedRepoError, HfHubHTTPError, RepositoryNotFoundError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.utils.logging_utils import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

CLOTH_ALLOW_PATTERNS = [
    "model_index.json",
    "scheduler/*",
    "tokenizer/*",
    "tokenizer_2/*",
    "text_encoder/*",
    "text_encoder_2/*",
    "unet/*",
    "vae/*",
    "feature_extractor/*",
    "safety_checker/*",
]

CLOTH_IGNORE_PATTERNS = [
    "*/model.onnx",
    "*/model.onnx_data",
    "*/openvino_model.bin",
    "*/openvino_model.xml",
    "*/diffusion_flax_model.msgpack",
]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Download cloth generation and virtual try-on assets.")
    parser.add_argument(
        "--full-clothes-download",
        action="store_true",
        help="Download full cloth model repository including non-Diffusers artifacts.",
    )
    parser.add_argument(
        "--only-clothes",
        action="store_true",
        help="Download cloth model only.",
    )
    parser.add_argument(
        "--only-sdxl",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--only-tryon",
        action="store_true",
        help="Download try-on (FASHN VTON) repo + weights only.",
    )
    parser.add_argument(
        "--skip-parser-warmup",
        action="store_true",
        help="Skip optional warmup download of FASHN human parser cache.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Parallel download workers for Hugging Face snapshot downloads.",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=20,
        help="Heartbeat interval (seconds) for local cache growth logs.",
    )
    parser.add_argument(
        "--show-httpx",
        action="store_true",
        help="Show low-level httpx/httpcore logs.",
    )
    return parser.parse_args()


def configure_http_logs(show_httpx: bool) -> None:
    """Control verbosity of httpx/httpcore logs."""

    level = logging.INFO if show_httpx else logging.WARNING
    logging.getLogger("httpx").setLevel(level)
    logging.getLogger("httpcore").setLevel(level)


def format_bytes(num_bytes: int) -> str:
    """Return human-readable byte size."""

    size = float(num_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f}{unit}"
        size /= 1024
    return f"{num_bytes}B"


def directory_size_bytes(path: Path) -> int:
    """Compute recursive directory size in bytes."""

    if not path.exists():
        return 0

    total = 0
    for file_path in path.rglob("*"):
        if file_path.is_file():
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total


def start_progress_logger(cache_dir: Path, stop_event: threading.Event, interval_seconds: int) -> threading.Thread:
    """Spawn background logger that emits periodic cache growth updates."""

    def _runner() -> None:
        previous_size = directory_size_bytes(cache_dir)
        logger.info("Download heartbeat: initial cache size=%s", format_bytes(previous_size))
        while not stop_event.wait(interval_seconds):
            current_size = directory_size_bytes(cache_dir)
            delta = current_size - previous_size
            delta_str = "0.00B" if delta == 0 else f"{'+' if delta > 0 else '-'}{format_bytes(abs(delta))}"
            logger.info(
                "Download heartbeat: cache size=%s (%s since last update)",
                format_bytes(current_size),
                delta_str,
            )
            previous_size = current_size

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    return thread


def validate_cloth_snapshot(snapshot_path: Path) -> None:
    """Validate minimum required files for diffusers text-to-image inference."""

    must_exist = [
        snapshot_path / "model_index.json",
        snapshot_path / "scheduler",
        snapshot_path / "tokenizer",
        snapshot_path / "unet" / "config.json",
    ]
    missing = [path for path in must_exist if not path.exists()]
    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise RuntimeError(
            "Cloth model download completed but required files are missing:\n"
            f"{joined}\n"
            "Retry `python scripts/download_models.py --only-clothes` to resume/repair cache."
        )

    unet_candidates = [
        snapshot_path / "unet" / "diffusion_pytorch_model.fp16.safetensors",
        snapshot_path / "unet" / "diffusion_pytorch_model.safetensors",
    ]
    if not any(path.exists() for path in unet_candidates):
        raise RuntimeError(
            "Could not find UNet weights in cloth model snapshot. "
            f"Expected one of: {[str(path) for path in unet_candidates]}"
        )


def validate_tryon_assets(fashn_repo_dir: Path, fashn_weights_dir: Path) -> None:
    """Validate that required FASHN repo files and weights are present."""

    required_repo_files = [
        fashn_repo_dir / "examples" / "basic_inference.py",
        fashn_repo_dir / "src" / "fashn_vton" / "__init__.py",
    ]
    required_weight_files = [
        fashn_weights_dir / "model.safetensors",
        fashn_weights_dir / "dwpose" / "yolox_l.onnx",
        fashn_weights_dir / "dwpose" / "dw-ll_ucoco_384.onnx",
    ]

    missing = [path for path in [*required_repo_files, *required_weight_files] if not path.exists()]
    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise RuntimeError(
            "Try-on assets validation failed; missing files:\n"
            f"{joined}\n"
            "Rerun `python scripts/download_models.py --only-tryon`."
        )


def normalize_hf_token(hf_token: str | None) -> str | None:
    """Normalize HF token by trimming whitespace and mapping blank values to None."""

    if hf_token is None:
        return None
    stripped = hf_token.strip()
    return stripped or None


def hf_token_for_hub(hf_token: str | None) -> str | bool:
    """Return token argument for huggingface_hub calls.

    Notes:
    - `token=False` explicitly disables auth headers.
    - `token=None` allows implicit token discovery from env/cache.
      We avoid that here because an empty HF_TOKEN env var can produce `Bearer `.
    """

    normalized = normalize_hf_token(hf_token)
    if normalized:
        return normalized
    return False


def download_cloth_model(
    model_id: str,
    cache_dir: Path,
    hf_token: str | bool,
    full_download: bool,
    max_workers: int,
    progress_interval: int,
) -> Path:
    """Download lightweight cloth model to cache."""

    local_model_dir = Path(model_id)
    if local_model_dir.exists():
        model_index = local_model_dir / "model_index.json"
        if not model_index.exists():
            raise RuntimeError(
                f"CLOTH_MODEL_ID points to local path but `model_index.json` is missing: {model_index}"
            )
        validate_cloth_snapshot(local_model_dir)
        logger.info("Using existing local cloth model directory: %s", local_model_dir.resolve())
        return local_model_dir.resolve()

    logger.info("Cloth model ID: %s", model_id)
    logger.info("Cloth model cache: %s", cache_dir.resolve())
    logger.info("Resume behavior: partial files are reused automatically.")

    stop_event = threading.Event()
    thread = start_progress_logger(cache_dir=cache_dir, stop_event=stop_event, interval_seconds=max(5, progress_interval))
    started_at = time.time()

    try:
        snapshot_path = snapshot_download(
            repo_id=model_id,
            cache_dir=str(cache_dir),
            token=hf_token,
            allow_patterns=None if full_download else CLOTH_ALLOW_PATTERNS,
            ignore_patterns=None if full_download else CLOTH_IGNORE_PATTERNS,
            max_workers=max_workers,
        )
    except GatedRepoError as error:
        raise RuntimeError(
            "Access denied to gated Hugging Face model. Accept model terms and set HF_TOKEN.\n"
            f"Model: {model_id}\nOriginal error: {error}"
        ) from error
    except RepositoryNotFoundError as error:
        raise RuntimeError(
            f"Model repository not found: {model_id}. Check CLOTH_MODEL_ID in .env."
        ) from error
    except HfHubHTTPError as error:
        status_code = getattr(error.response, "status_code", "unknown")
        raise RuntimeError(
            "Hugging Face HTTP error while downloading cloth model.\n"
            f"Model: {model_id}\nHTTP status: {status_code}\nOriginal error: {error}"
        ) from error
    finally:
        stop_event.set()
        thread.join(timeout=1.0)

    elapsed = time.time() - started_at
    resolved = Path(snapshot_path)
    validate_cloth_snapshot(resolved)
    logger.info("Cloth snapshot validated at: %s", resolved)
    logger.info("Cloth download elapsed: %.1f seconds", elapsed)
    logger.info("Final cache size: %s", format_bytes(directory_size_bytes(cache_dir)))
    return resolved


def clone_repo(repo_url: str, destination: Path) -> None:
    """Clone a git repository if missing."""

    if destination.exists() and (destination / ".git").exists():
        logger.info("Repository already present: %s", destination)
        return

    if destination.exists() and not (destination / ".git").exists():
        contents = list(destination.iterdir())
        if contents:
            raise RuntimeError(
                "Target repository directory exists and is not a git repo:\n"
                f"{destination}\n"
                "Delete or rename it, then rerun download."
            )
        destination.rmdir()

    destination.parent.mkdir(parents=True, exist_ok=True)
    if not shutil.which("git"):
        raise RuntimeError("`git` is not installed. Install git and retry.")

    logger.info("Cloning repository %s -> %s", repo_url, destination)
    subprocess.run(["git", "clone", repo_url, str(destination)], check=True, cwd=destination.parent)


def download_fashn_weights(weights_dir: Path, hf_token: str | bool) -> None:
    """Download required FASHN VTON try-on weights."""

    weights_dir.mkdir(parents=True, exist_ok=True)
    dwpose_dir = weights_dir / "dwpose"
    dwpose_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading FASHN TryOn model weights to %s", weights_dir)
    hf_hub_download(
        repo_id="fashn-ai/fashn-vton-1.5",
        filename="model.safetensors",
        local_dir=str(weights_dir),
        token=hf_token,
    )

    for filename in ["yolox_l.onnx", "dw-ll_ucoco_384.onnx"]:
        logger.info("Downloading DWPose file: %s", filename)
        hf_hub_download(
            repo_id="fashn-ai/DWPose",
            filename=filename,
            local_dir=str(dwpose_dir),
            token=hf_token,
        )

    logger.info("FASHN weights downloaded successfully.")


def warmup_fashn_parser_cache(skip_warmup: bool) -> None:
    """Optionally trigger first-time human parser cache download on CPU."""

    if skip_warmup:
        logger.info("Skipping FASHN human parser warmup (--skip-parser-warmup).")
        return

    try:
        from fashn_human_parser import FashnHumanParser

        logger.info("Warming up FASHN human parser cache (one-time download).")
        _ = FashnHumanParser(device="cpu")
        logger.info("FASHN human parser cache ready.")
    except ImportError:
        logger.warning(
            "fashn-human-parser is not installed yet. Install requirements then rerun for warmup."
        )
    except Exception as error:
        logger.warning("FASHN parser warmup failed (non-blocking): %s", error)


def main() -> int:
    """Entry point for model setup script."""

    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()
    if args.only_sdxl:
        args.only_clothes = True
    configure_http_logs(show_httpx=args.show_httpx)
    settings = get_settings()

    logger.info(
        "Download options: full_clothes=%s only_clothes=%s only_tryon=%s max_workers=%d interval=%ss",
        args.full_clothes_download,
        args.only_clothes,
        args.only_tryon,
        args.max_workers,
        args.progress_interval,
    )

    raw_hf_token = normalize_hf_token(settings.hf_token)
    hub_token = hf_token_for_hub(raw_hf_token)

    if raw_hf_token:
        logger.info("Logging into Hugging Face with HF_TOKEN.")
        try:
            login(token=raw_hf_token)
        except Exception as error:
            raise RuntimeError(
                "Failed to authenticate with Hugging Face using HF_TOKEN. "
                "Verify token validity and permissions."
            ) from error
    else:
        logger.warning("HF_TOKEN is not set. Anonymous download will be attempted.")
        logger.info("Hugging Face auth mode: anonymous (token=False).")

    run_clothes = not args.only_tryon
    run_tryon = not args.only_clothes

    if not run_clothes and not run_tryon:
        raise RuntimeError("No download target selected. Remove conflicting flags and retry.")

    if run_clothes:
        download_cloth_model(
            model_id=settings.cloth_model_id,
            cache_dir=settings.model_cache_dir,
            hf_token=hub_token,
            full_download=args.full_clothes_download,
            max_workers=args.max_workers,
            progress_interval=args.progress_interval,
        )

    if run_tryon:
        clone_repo(settings.fashn_repo_url, settings.fashn_model_dir)
        download_fashn_weights(settings.fashn_weights_dir, hf_token=hub_token)
        warmup_fashn_parser_cache(skip_warmup=args.skip_parser_warmup)
        validate_tryon_assets(settings.fashn_model_dir, settings.fashn_weights_dir)
        logger.info(
            "Try-on assets validated: repo=%s weights=%s",
            settings.fashn_model_dir,
            settings.fashn_weights_dir,
        )

    print("\nSetup completed successfully. Next steps:")
    print("1. Install dependencies if needed:")
    print("   pip install -r requirements.txt")
    print("2. Run API:")
    print("   uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("3. Test health endpoint:")
    print("   curl http://localhost:8000/health")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logger.exception("Model setup failed: %s", error)
        raise SystemExit(1)
