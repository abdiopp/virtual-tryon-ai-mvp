"""Device selection helpers."""

from __future__ import annotations

import torch


def resolve_device(preferred: str = "auto") -> str:
    """Resolve runtime device from preference and hardware availability."""

    normalized = preferred.lower().strip()
    if normalized == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    if normalized == "cuda" and torch.cuda.is_available():
        return "cuda"
    if normalized == "mps" and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def require_cuda_if_requested(preferred: str = "auto") -> None:
    """Raise a clear error when CUDA is requested but unavailable."""

    if preferred.lower().strip() == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is required by current configuration (DEVICE=cuda), but no CUDA GPU "
            "is available. Switch DEVICE=cpu for development or run on a CUDA-enabled machine."
        )


def describe_device(preferred: str = "auto") -> str:
    """Human-readable runtime device string."""

    return resolve_device(preferred)
