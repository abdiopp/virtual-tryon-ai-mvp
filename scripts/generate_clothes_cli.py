"""CLI for standalone SDXL garment generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.cloth_generator import ClothGenerationError, ClothGeneratorService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate garment images using the configured Diffusers model.")
    parser.add_argument("--prompt", required=True, help="Garment generation prompt")
    parser.add_argument("--category", default=None, help="Optional garment category")
    parser.add_argument("--negative-prompt", default=None, help="Optional custom negative prompt")
    parser.add_argument("--count", type=int, default=1, help="Number of images to generate")
    parser.add_argument("--width", type=int, default=768, help="Output width")
    parser.add_argument("--height", type=int, default=1024, help="Output height")
    parser.add_argument("--guidance-scale", type=float, default=7.0, help="CFG guidance scale")
    parser.add_argument("--num-inference-steps", type=int, default=30, help="Diffusion steps")
    parser.add_argument("--seed", type=int, default=None, help="Optional base seed")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = ClothGeneratorService()

    try:
        results = service.generate_clothes(
            prompt=args.prompt,
            category=args.category,
            negative_prompt=args.negative_prompt,
            count=args.count,
            width=args.width,
            height=args.height,
            guidance_scale=args.guidance_scale,
            num_inference_steps=args.num_inference_steps,
            seed=args.seed,
        )
    except ClothGenerationError as error:
        print(f"Generation failed: {error}")
        return 1

    payload = {
        "success": True,
        "items": [
            {
                "id": item.id,
                "path": item.path,
                "prompt": item.prompt,
                "seed": item.seed,
                "metadata": item.metadata,
            }
            for item in results
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
