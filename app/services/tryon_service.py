"""FASHN VTON subprocess wrapper service for virtual try-on."""

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


class TryOnSetupError(RuntimeError):
    """Raised when try-on setup is incomplete or incompatible."""


@dataclass
class VirtualTryOnResult:
    """Result payload returned by try-on service."""

    result_path: str
    metadata: dict[str, str | int | float]


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
    ) -> Path:
        """Run a single try-on attempt and return the predicted output image path."""

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

            return candidates[0]

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
            )

        target_output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(predicted_path, target_output_path)
        elapsed_seconds = time.monotonic() - request_started_at
        self.logger.info("Try-on output saved to %s in %.1fs", target_output_path, elapsed_seconds)

        return VirtualTryOnResult(
            result_path=str(target_output_path),
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
