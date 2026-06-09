"""CLI for local virtual try-on backend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tryon_service import TryOnSetupError, get_tryon_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run virtual try-on for a single person/garment pair.")
    parser.add_argument("--person", required=True, help="Path to person image")
    parser.add_argument("--garment", required=True, help="Path to garment image")
    parser.add_argument("--category", default="upper_body", help="upper_body | lower_body | dress")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = get_tryon_service()

    try:
        result = service.run_tryon(
            person_image_path=args.person,
            garment_image_path=args.garment,
            category=args.category,
        )
    except (FileNotFoundError, ValueError, TryOnSetupError) as error:
        print(f"Virtual try-on failed: {error}")
        return 1

    print(
        json.dumps(
            {
                "success": True,
                "result_path": result.result_path,
                "metadata": result.metadata,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
