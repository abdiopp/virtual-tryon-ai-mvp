"""Subprocess wrappers for virtual try-on backends."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import Settings, get_settings
from app.services.storage_service import StorageService
from app.utils.device import resolve_device
from app.utils.image_utils import ensure_image_exists
from app.utils.logging_utils import get_logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEFFA_RUNNER_PATH = PROJECT_ROOT / "scripts" / "leffa_tryon_infer.py"

CATEGORY_MAP = {
    "upper_body": "tops",
    "lower_body": "bottoms",
    "dress": "one-pieces",
    "dresses": "one-pieces",
    "upper": "tops",
    "lower": "bottoms",
    "overall": "one-pieces",
    "tops": "tops",
    "bottoms": "bottoms",
    "one-pieces": "one-pieces",
}

LEFFA_CATEGORY_MAP = {
    "upper_body": "upper_body",
    "lower_body": "lower_body",
    "dress": "dresses",
    "dresses": "dresses",
    "upper": "upper_body",
    "lower": "lower_body",
    "overall": "dresses",
    "tops": "upper_body",
    "bottoms": "lower_body",
    "one-pieces": "dresses",
}

SUPPORTED_TRYON_BACKENDS = {
    "fashn": "fashn_vton",
    "fashn_vton": "fashn_vton",
    "leffa": "leffa",
}


def normalize_tryon_backend(backend: str) -> str:
    """Normalize supported try-on backend aliases."""

    normalized = backend.strip().lower().replace("-", "_")
    if normalized not in SUPPORTED_TRYON_BACKENDS:
        choices = ", ".join(sorted(SUPPORTED_TRYON_BACKENDS))
        raise TryOnSetupError(f"Unsupported TRYON_BACKEND={backend!r}. Use one of: {choices}.")
    return SUPPORTED_TRYON_BACKENDS[normalized]


def _extract_progress_from_line(line: str) -> float | None:
    """Pull a progress percentage from subprocess output if it is present."""

    percent_match = re.search(r"(?P<percent>\d{1,3}(?:\.\d+)?)%", line)
    if percent_match:
        percent = float(percent_match.group("percent"))
        if 0.0 <= percent <= 100.0:
            return percent

    fraction_match = re.search(r"(?P<current>\d+)\s*/\s*(?P<total>\d+)", line)
    if fraction_match:
        current = float(fraction_match.group("current"))
        total = float(fraction_match.group("total"))
        if total > 0:
            return min(100.0, (current / total) * 100.0)

    return None


def _log_progress_update(
    logger,
    *,
    progress_percent: float | None,
    started_at: float,
    message: str,
) -> None:
    """Emit a normalized progress line with elapsed and ETA when possible."""

    elapsed = time.monotonic() - started_at
    if progress_percent is None:
        logger.info("%s | elapsed=%.1fs eta=unknown", message, elapsed)
        return

    progress_ratio = max(0.0, min(progress_percent / 100.0, 1.0))
    eta_seconds = None
    if progress_ratio > 0.0:
        total_estimate = elapsed / progress_ratio
        eta_seconds = max(0.0, total_estimate - elapsed)

    eta_text = f"{eta_seconds:.1f}s" if eta_seconds is not None else "unknown"
    logger.info(
        "%s | progress=%.0f%% elapsed=%.1fs eta=%s",
        message,
        progress_percent,
        elapsed,
        eta_text,
    )


def _run_subprocess_with_live_logs(
    *,
    logger,
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    log_prefix: str,
    failure_message: str,
    heartbeat_seconds: int = 15,
) -> list[str]:
    """Run subprocess with streaming logs and periodic heartbeat."""

    captured_lines: list[str] = []
    started_at = time.monotonic()
    last_heartbeat = started_at
    last_progress_percent: float | None = None

    with subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    ) as process:
        if process.stdout is None:
            raise TryOnSetupError("Failed to capture try-on subprocess output stream.")

        output_queue: queue.Queue[str] = queue.Queue()
        reader_done = threading.Event()

        def _drain_stdout() -> None:
            try:
                for line in process.stdout:
                    output_queue.put(line.rstrip())
            finally:
                reader_done.set()

        reader_thread = threading.Thread(target=_drain_stdout, daemon=True)
        reader_thread.start()

        while True:
            try:
                cleaned = output_queue.get(timeout=1.0)
            except queue.Empty:
                cleaned = None

            if cleaned is not None:
                captured_lines.append(cleaned)
                logger.info("[%s] %s", log_prefix, cleaned)
                progress_percent = _extract_progress_from_line(cleaned)
                if progress_percent is not None and (
                    last_progress_percent is None or progress_percent > last_progress_percent
                ):
                    last_progress_percent = progress_percent
                    _log_progress_update(
                        logger,
                        progress_percent=progress_percent,
                        started_at=started_at,
                        message="Try-on progress update",
                    )
            elif reader_done.is_set() and process.poll() is not None and output_queue.empty():
                break

            now = time.monotonic()
            if now - last_heartbeat >= heartbeat_seconds:
                if last_progress_percent is None:
                    logger.info(
                        "Try-on heartbeat: still running | elapsed=%.1fs eta=unknown",
                        now - started_at,
                    )
                else:
                    _log_progress_update(
                        logger,
                        progress_percent=last_progress_percent,
                        started_at=started_at,
                        message="Try-on heartbeat",
                    )
                last_heartbeat = now

        reader_thread.join(timeout=1.0)
        return_code = process.wait()
        if return_code != 0:
            joined_output = "\n".join(captured_lines)
            raise TryOnSetupError(
                f"{failure_message}\n"
                "Command:\n"
                f"{' '.join(command)}\n"
                f"OUTPUT:\n{joined_output}"
            )

    return captured_lines


class TryOnSetupError(RuntimeError):
    """Raised when try-on setup is incomplete or incompatible."""


@dataclass
class VirtualTryOnResult:
    """Result payload returned by try-on service."""

    result_path: str
    metadata: dict[str, str | int | float]


class LeffaTryOnService:
    """Service that calls Leffa inference through a subprocess."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = StorageService(self.settings)
        self.logger = get_logger(__name__)
        requested_device = resolve_device(self.settings.device)
        self.runtime_device = "cuda" if requested_device == "cuda" else "cpu"

    def is_model_available(self) -> bool:
        """Check if Leffa repo and required checkpoint files are present."""

        repo_dir = self.settings.leffa_model_dir
        checkpoint_dir = self.settings.leffa_checkpoint_dir
        required_files = [
            LEFFA_RUNNER_PATH,
            repo_dir / "leffa" / "model.py",
            repo_dir / "leffa" / "inference.py",
            repo_dir / "preprocess" / "humanparsing" / "run_parsing.py",
            repo_dir / "preprocess" / "openpose" / "run_openpose.py",
            checkpoint_dir / "virtual_tryon.pth",
            checkpoint_dir / "virtual_tryon_dc.pth",
            checkpoint_dir / "stable-diffusion-inpainting" / "model_index.json",
            checkpoint_dir / "densepose" / "densepose_rcnn_R_50_FPN_s1x.yaml",
            checkpoint_dir / "densepose" / "model_final_162be9.pkl",
            checkpoint_dir / "humanparsing" / "parsing_atr.onnx",
            checkpoint_dir / "humanparsing" / "parsing_lip.onnx",
            checkpoint_dir / "openpose" / "body_pose_model.pth",
        ]
        return all(path.exists() for path in required_files)

    def _normalize_category(self, category: str) -> str:
        normalized = category.strip().lower()
        if normalized not in LEFFA_CATEGORY_MAP:
            raise ValueError("Invalid category. Use one of: upper_body, lower_body, dress.")
        return LEFFA_CATEGORY_MAP[normalized]

    def _validate_setup(self) -> None:
        repo_dir = self.settings.leffa_model_dir
        checkpoint_dir = self.settings.leffa_checkpoint_dir
        required_files = [
            LEFFA_RUNNER_PATH,
            repo_dir / "leffa" / "model.py",
            repo_dir / "leffa" / "inference.py",
            repo_dir / "preprocess" / "humanparsing" / "run_parsing.py",
            repo_dir / "preprocess" / "openpose" / "run_openpose.py",
            checkpoint_dir / "virtual_tryon.pth",
            checkpoint_dir / "virtual_tryon_dc.pth",
            checkpoint_dir / "stable-diffusion-inpainting" / "model_index.json",
            checkpoint_dir / "densepose" / "densepose_rcnn_R_50_FPN_s1x.yaml",
            checkpoint_dir / "densepose" / "model_final_162be9.pkl",
            checkpoint_dir / "humanparsing" / "parsing_atr.onnx",
            checkpoint_dir / "humanparsing" / "parsing_lip.onnx",
            checkpoint_dir / "openpose" / "body_pose_model.pth",
        ]
        missing = [path for path in required_files if not path.exists()]
        if missing:
            joined = "\n".join(f"- {path}" for path in missing)
            raise TryOnSetupError(
                "Leffa try-on assets are missing:\n"
                f"{joined}\n"
                "Run `python scripts/download_models.py --only-tryon` and retry."
            )

    def _build_inference_command(
        self,
        *,
        person_path: Path,
        garment_path: Path,
        normalized_category: str,
        target_output_path: Path,
    ) -> list[str]:
        """Build the Leffa inference command with Colab-quality defaults."""

        command = [
            sys.executable,
            "-u",
            str(LEFFA_RUNNER_PATH),
            "--repo-dir",
            str(self.settings.leffa_model_dir.resolve()),
            "--checkpoint-dir",
            str(self.settings.leffa_checkpoint_dir.resolve()),
            "--person-image",
            str(person_path.resolve()),
            "--garment-image",
            str(garment_path.resolve()),
            "--category",
            normalized_category,
            "--output-path",
            str(target_output_path.resolve()),
            "--num-inference-steps",
            str(self.settings.leffa_num_inference_steps),
            "--guidance-scale",
            str(self.settings.leffa_guidance_scale),
            "--seed",
            str(self.settings.leffa_seed),
            "--model-type",
            self.settings.leffa_model_type,
        ]

        if self.settings.leffa_ref_acceleration:
            command.append("--ref-acceleration")
        if self.settings.leffa_repaint:
            command.append("--repaint")
        if self.settings.leffa_preprocess_garment:
            command.append("--preprocess-garment")

        return command

    def _build_tryon_env(self) -> dict[str, str]:
        """Prepare the subprocess environment for Leffa inference."""

        env = dict(os.environ)
        repo_path = str(self.settings.leffa_model_dir.resolve())
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{repo_path}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else repo_path
        )
        if self.runtime_device == "cuda":
            env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        return env

    def run_tryon(
        self,
        person_image_path: Path | str,
        garment_image_path: Path | str,
        category: str = "upper_body",
        output_path: Path | None = None,
    ) -> VirtualTryOnResult:
        """Run Leffa inference and return final try-on image path."""

        self._validate_setup()

        person_path = ensure_image_exists(person_image_path)
        garment_path = ensure_image_exists(garment_image_path)
        request_started_at = time.monotonic()

        normalized_category = self._normalize_category(category)
        target_output_path = output_path or self.storage.build_output_path(
            subfolder="tryon_results",
            prefix="tryon_result",
            extension=".png",
        )
        target_output_path.parent.mkdir(parents=True, exist_ok=True)

        command = self._build_inference_command(
            person_path=person_path,
            garment_path=garment_path,
            normalized_category=normalized_category,
            target_output_path=target_output_path,
        )
        env = self._build_tryon_env()

        self.logger.info(
            "Leffa try-on request: category=%s person=%s garment=%s",
            normalized_category,
            person_path,
            garment_path,
        )
        self.logger.info("Running Leffa command: %s", " ".join(command))
        self.logger.info("Try-on runtime device request=%s resolved=%s", self.settings.device, self.runtime_device)

        _run_subprocess_with_live_logs(
            logger=self.logger,
            command=command,
            cwd=self.settings.leffa_model_dir,
            env=env,
            log_prefix="leffa",
            failure_message=(
                "Leffa inference failed. Ensure Colab is using a GPU and dependencies are installed.\n"
                "Install helper:\n"
                "pip install -r requirements.txt"
            ),
        )

        if not target_output_path.exists():
            raise TryOnSetupError(
                "Leffa finished without output image. "
                f"Expected: {target_output_path}"
            )

        elapsed_seconds = time.monotonic() - request_started_at
        self.logger.info("Try-on output saved to %s in %.1fs", target_output_path, elapsed_seconds)

        return VirtualTryOnResult(
            result_path=str(target_output_path),
            metadata={
                "category": normalized_category,
                "source_person": str(person_path),
                "source_garment": str(garment_path),
                "tryon_backend": "leffa",
                "runtime_device": self.runtime_device,
                "generation_seconds": round(time.monotonic() - request_started_at, 3),
                "request_seconds": round(time.monotonic() - request_started_at, 3),
            },
        )


class FashnTryOnService:
    """Service that calls FASHN VTON inference through subprocess."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = StorageService(self.settings)
        self.logger = get_logger(__name__)
        self.runtime_device = resolve_device(self.settings.device)

    def is_model_available(self) -> bool:
        """Check if FASHN repo and required files are present."""

        repo_dir = self.settings.fashn_model_dir
        required_repo_files = [
            repo_dir / "examples" / "basic_inference.py",
            repo_dir / "src" / "fashn_vton" / "__init__.py",
        ]
        required_weights = [
            self.settings.fashn_weights_dir / "model.safetensors",
            self.settings.fashn_weights_dir / "dwpose" / "yolox_l.onnx",
            self.settings.fashn_weights_dir / "dwpose" / "dw-ll_ucoco_384.onnx",
        ]

        return all(path.exists() for path in [*required_repo_files, *required_weights])

    def _normalize_category(self, category: str) -> str:
        normalized = category.strip().lower()
        if normalized not in CATEGORY_MAP:
            raise ValueError(
                "Invalid category. Use one of: upper_body, lower_body, dress."
            )
        return CATEGORY_MAP[normalized]

    def _validate_setup(self) -> None:
        repo_dir = self.settings.fashn_model_dir
        inference_script = repo_dir / "examples" / "basic_inference.py"
        if not inference_script.exists():
            raise TryOnSetupError(
                "FASHN VTON inference script not found. Run `python scripts/download_models.py --only-tryon` "
                "to clone the repository and download required files."
            )

        missing_weights: list[Path] = []
        for path in [
            self.settings.fashn_weights_dir / "model.safetensors",
            self.settings.fashn_weights_dir / "dwpose" / "yolox_l.onnx",
            self.settings.fashn_weights_dir / "dwpose" / "dw-ll_ucoco_384.onnx",
        ]:
            if not path.exists():
                missing_weights.append(path)

        if missing_weights:
            joined = "\n".join(f"- {path}" for path in missing_weights)
            raise TryOnSetupError(
                "FASHN VTON weights are missing:\n"
                f"{joined}\n"
                "Run `python scripts/download_models.py --only-tryon` and retry."
            )

    def _extract_progress_from_line(self, line: str) -> float | None:
        """Pull a progress percentage from subprocess output if it is present."""

        percent_match = re.search(r"(?P<percent>\d{1,3}(?:\.\d+)?)%", line)
        if percent_match:
            percent = float(percent_match.group("percent"))
            if 0.0 <= percent <= 100.0:
                return percent

        fraction_match = re.search(r"(?P<current>\d+)\s*/\s*(?P<total>\d+)", line)
        if fraction_match:
            current = float(fraction_match.group("current"))
            total = float(fraction_match.group("total"))
            if total > 0:
                return min(100.0, (current / total) * 100.0)

        return None

    def _log_progress_update(
        self,
        *,
        progress_percent: float | None,
        started_at: float,
        message: str,
    ) -> None:
        """Emit a normalized progress line with elapsed and ETA when possible."""

        elapsed = time.monotonic() - started_at
        if progress_percent is None:
            self.logger.info("%s | elapsed=%.1fs eta=unknown", message, elapsed)
            return

        progress_ratio = max(0.0, min(progress_percent / 100.0, 1.0))
        eta_seconds = None
        if progress_ratio > 0.0:
            total_estimate = elapsed / progress_ratio
            eta_seconds = max(0.0, total_estimate - elapsed)

        eta_text = f"{eta_seconds:.1f}s" if eta_seconds is not None else "unknown"
        self.logger.info(
            "%s | progress=%.0f%% elapsed=%.1fs eta=%s",
            message,
            progress_percent,
            elapsed,
            eta_text,
        )

    def _build_inference_command(
        self,
        *,
        repo_dir: Path,
        temp_dir: Path,
        person_path: Path,
        garment_path: Path,
        normalized_category: str,
        device: str,
        num_timesteps: int,
    ) -> list[str]:
        """Build the FASHN inference command with the requested runtime settings."""

        command = [
            sys.executable,
            "-u",
            str(repo_dir / "examples" / "basic_inference.py"),
            "--weights-dir",
            str(self.settings.fashn_weights_dir.resolve()),
            "--person-image",
            str(person_path.resolve()),
            "--garment-image",
            str(garment_path.resolve()),
            "--category",
            normalized_category,
            "--garment-photo-type",
            self.settings.fashn_garment_photo_type,
            "--output-dir",
            str(temp_dir),
            "--num-samples",
            str(self.settings.fashn_num_samples),
            "--num-timesteps",
            str(num_timesteps),
            "--guidance-scale",
            str(self.settings.fashn_guidance_scale),
            "--seed",
            "42",
            "--device",
            device,
        ]

        if not self.settings.fashn_segmentation_free:
            command.append("--no-segmentation-free")

        return command

    def _build_tryon_env(self, repo_dir: Path) -> dict[str, str]:
        """Prepare the subprocess environment for FASHN inference."""

        env = dict(os.environ)
        src_path = str((repo_dir / "src").resolve())
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{src_path}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else src_path
        )
        return env

    def _contains_cuda_oom(self, lines: list[str]) -> bool:
        """Detect CUDA OOM messages from the captured subprocess output."""

        joined = "\n".join(lines).lower()
        return "cuda out of memory" in joined or "torch.outofmemoryerror" in joined

    def _run_tryon_attempt(
        self,
        *,
        repo_dir: Path,
        person_path: Path,
        garment_path: Path,
        normalized_category: str,
        device: str,
        num_timesteps: int,
        request_label: str,
        target_output_path: Path,
    ) -> Path:
        """Run a single try-on attempt and copy the result before cleanup."""

        with TemporaryDirectory(prefix="fashn_vton_output_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            command = self._build_inference_command(
                repo_dir=repo_dir,
                temp_dir=temp_dir,
                person_path=person_path,
                garment_path=garment_path,
                normalized_category=normalized_category,
                device=device,
                num_timesteps=num_timesteps,
            )

            env = self._build_tryon_env(repo_dir)

            if device == "cuda":
                env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

            self.logger.info("Running FASHN VTON command: %s", " ".join(command))
            self.logger.info(
                "%s runtime device=%s",
                request_label,
                device,
            )
            self._run_subprocess_with_live_logs(
                command=command,
                cwd=repo_dir,
                env=env,
            )

            candidates = sorted(temp_dir.glob("output_*.png"))
            if not candidates:
                raise TryOnSetupError(
                    "FASHN VTON finished without output image. "
                    f"Checked: {temp_dir}"
                )

            predicted_path = candidates[0]
            target_output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(predicted_path, target_output_path)
            return target_output_path

    def _run_subprocess_with_live_logs(
        self,
        command: list[str],
        cwd: Path,
        env: dict[str, str],
        heartbeat_seconds: int = 15,
    ) -> list[str]:
        """Run subprocess with streaming logs and periodic heartbeat."""

        captured_lines: list[str] = []
        started_at = time.monotonic()
        last_heartbeat = started_at
        last_progress_percent: float | None = None

        with subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        ) as process:
            if process.stdout is None:
                raise TryOnSetupError("Failed to capture try-on subprocess output stream.")

            output_queue: queue.Queue[str] = queue.Queue()
            reader_done = threading.Event()

            def _drain_stdout() -> None:
                try:
                    for line in process.stdout:
                        output_queue.put(line.rstrip())
                finally:
                    reader_done.set()

            reader_thread = threading.Thread(target=_drain_stdout, daemon=True)
            reader_thread.start()

            while True:
                try:
                    cleaned = output_queue.get(timeout=1.0)
                except queue.Empty:
                    cleaned = None

                if cleaned is not None:
                    captured_lines.append(cleaned)
                    self.logger.info("[tryon] %s", cleaned)
                    progress_percent = self._extract_progress_from_line(cleaned)
                    if progress_percent is not None and (
                        last_progress_percent is None or progress_percent > last_progress_percent
                    ):
                        last_progress_percent = progress_percent
                        self._log_progress_update(
                            progress_percent=progress_percent,
                            started_at=started_at,
                            message="Try-on progress update",
                        )
                elif reader_done.is_set() and process.poll() is not None and output_queue.empty():
                    break

                now = time.monotonic()
                if now - last_heartbeat >= heartbeat_seconds:
                    if last_progress_percent is None:
                        self.logger.info(
                            "Try-on heartbeat: still running | elapsed=%.1fs eta=unknown",
                            now - started_at,
                        )
                    else:
                        self._log_progress_update(
                            progress_percent=last_progress_percent,
                            started_at=started_at,
                            message="Try-on heartbeat",
                        )
                    last_heartbeat = now

            reader_thread.join(timeout=1.0)
            return_code = process.wait()
            if return_code != 0:
                joined_output = "\n".join(captured_lines)
                raise TryOnSetupError(
                    "FASHN VTON inference failed. Ensure dependencies are installed.\n"
                    "Install helper:\n"
                    "pip install einops tqdm matplotlib onnxruntime fashn-human-parser\n"
                    "Command:\n"
                    f"{' '.join(command)}\n"
                    f"OUTPUT:\n{joined_output}"
                )

        return captured_lines

    def run_tryon(
        self,
        person_image_path: Path | str,
        garment_image_path: Path | str,
        category: str = "upper_body",
        output_path: Path | None = None,
    ) -> VirtualTryOnResult:
        """Run FASHN VTON inference and return final try-on image path."""

        self._validate_setup()

        person_path = ensure_image_exists(person_image_path)
        garment_path = ensure_image_exists(garment_image_path)
        request_started_at = time.monotonic()

        normalized_category = self._normalize_category(category)
        target_output_path = output_path or self.storage.build_output_path(
            subfolder="tryon_results",
            prefix="tryon_result",
            extension=".png",
        )

        repo_dir = self.settings.fashn_model_dir
        self.logger.info(
            "Try-on request: category=%s person=%s garment=%s",
            normalized_category,
            person_path,
            garment_path,
        )

        initial_device = "cuda" if self.runtime_device == "cuda" else "cpu"
        initial_timesteps = self.settings.fashn_num_timesteps

        try:
            predicted_path = self._run_tryon_attempt(
                repo_dir=repo_dir,
                person_path=person_path,
                garment_path=garment_path,
                normalized_category=normalized_category,
                device=initial_device,
                num_timesteps=initial_timesteps,
                request_label="Try-on",
                target_output_path=target_output_path,
            )
        except TryOnSetupError as error:
            should_fallback = (
                initial_device == "cuda"
                and self.settings.fashn_fallback_to_cpu_on_oom
                and self._contains_cuda_oom(str(error).splitlines())
            )
            if not should_fallback:
                raise

            fallback_timesteps = min(4, initial_timesteps)
            self.logger.warning(
                "CUDA OOM detected for try-on; retrying on CPU with %d timestep(s).",
                fallback_timesteps,
            )
            predicted_path = self._run_tryon_attempt(
                repo_dir=repo_dir,
                person_path=person_path,
                garment_path=garment_path,
                normalized_category=normalized_category,
                device="cpu",
                num_timesteps=fallback_timesteps,
                request_label="Try-on fallback",
                target_output_path=target_output_path,
            )

        elapsed_seconds = time.monotonic() - request_started_at
        self.logger.info("Try-on output saved to %s in %.1fs", predicted_path, elapsed_seconds)

        return VirtualTryOnResult(
            result_path=str(predicted_path),
            metadata={
                "category": normalized_category,
                "source_person": str(person_path),
                "source_garment": str(garment_path),
                "tryon_backend": "fashn_vton",
                "runtime_device": self.runtime_device,
                "generation_seconds": round(time.monotonic() - request_started_at, 3),
                "request_seconds": round(time.monotonic() - request_started_at, 3),
            },
        )


def get_tryon_service(settings: Settings | None = None) -> LeffaTryOnService | FashnTryOnService:
    """Return the configured virtual try-on backend service."""

    resolved_settings = settings or get_settings()
    backend = normalize_tryon_backend(resolved_settings.tryon_backend)
    if backend == "leffa":
        return LeffaTryOnService(resolved_settings)
    if backend == "fashn_vton":
        return FashnTryOnService(resolved_settings)
    raise TryOnSetupError(f"Unsupported TRYON_BACKEND={resolved_settings.tryon_backend!r}.")
