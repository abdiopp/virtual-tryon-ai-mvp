# virtual-tryon-ai-mvp

A local two-stage virtual try-on backend optimized for non-NVIDIA machines:

1. Cloth generation: `stabilityai/sd-turbo` (few-step fast diffusion)
2. Virtual try-on: `FASHN VTON v1.5` backend wrapper (CPU/iGPU-friendly fallback)

This setup is designed for local Intel integrated graphics and Apple Silicon development.

## Why This Version

- Removes hard CUDA dependency from core workflow.
- Uses fast defaults so requests finish in practical time on CPU/MPS.
- Keeps modular FastAPI architecture for future backend integration.

## Architecture

- `app/routes/*`: API endpoints
- `app/services/cloth_generator.py`: Diffusers cloth generation service
- `app/services/tryon_service.py`: FASHN VTON try-on backend wrapper
- `scripts/download_models.py`: downloads cloth model + FASHN repo/weights

## Frontend

A new Next.js App Router frontend lives in [`frontend/`](frontend/README.md). It preserves the existing backend contract, adds a premium dashboard UI, and safely previews generated local files through the browser.

## Colab Demo

If you want to run the backend in Google Colab for a demo, use [COLAB_DEMO_SETUP.md](COLAB_DEMO_SETUP.md).

## Requirements

- Python 3.10+
- Git
- 16GB+ RAM recommended for smooth local runs

## Installation

PowerShell:

```bash
cd <path-to-repo>
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Command Prompt:

```bat
cd <path-to-repo>
py -3.10 -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process RemoteSigned` and try again.

## Environment Variables

Main keys from `.env.example`:

- `CLOTH_MODEL_ID=stabilityai/sd-turbo`
- `TRYON_BACKEND=fashn_vton`
- `FASHN_MODEL_DIR=models/fashn_vton`
- `FASHN_WEIGHTS_DIR=models/fashn_weights`
- `DEVICE=cpu` for Intel iGPU machines
- `DEVICE=mps` for Apple Silicon
- `NON_CUDA_FORCE_FAST_LIMITS=true` to auto-cap heavy requests

Backward compatibility aliases are supported:

- `SDXL_MODEL_ID` -> `CLOTH_MODEL_ID`
- `SDXL_LORA_PATH` -> `CLOTH_LORA_PATH`

## Download Models

Download both cloth + try-on assets:

```bash
python scripts/download_models.py
```

Download only cloth model:

```bash
python scripts/download_models.py --only-clothes
```

Download only try-on assets:

```bash
python scripts/download_models.py --only-tryon
```

## Run API

Use without reload for inference stability/performance:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Health Check

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "ok",
  "device": "cpu",
  "models": {
    "cloth_generator": "available",
    "tryon_model": "available"
  }
}
```

## Generate Clothes

Fast default request:

```bash
curl -X POST http://localhost:8000/generate-clothes \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "oversized black hoodie with minimal logo",
    "category": "hoodie",
    "count": 1,
    "width": 512,
    "height": 768,
    "guidance_scale": 0.0,
    "num_inference_steps": 4,
    "seed": 123
  }'
```

## Virtual Try-On

```bash
curl -X POST http://localhost:8000/virtual-tryon-from-path \
  -H "Content-Type: application/json" \
  -d '{
    "person_image_path": "uploads/persons/person.png",
    "garment_image_path": "outputs/generated_clothes/cloth.png",
    "category": "upper_body"
  }'
```

## CLI

Generate clothes:

```bash
python scripts/generate_clothes_cli.py \
  --prompt "black oversized hoodie streetwear" \
  --count 1 \
  --width 512 \
  --height 768 \
  --num-inference-steps 4 \
  --guidance-scale 0.0
```

Try-on:

```bash
python scripts/virtual_tryon_cli.py \
  --person uploads/persons/test.png \
  --garment outputs/generated_clothes/cloth_001.png \
  --category upper_body
```

## Performance Guidance

- Intel integrated graphics: set `DEVICE=cpu`.
- Apple Silicon: set `DEVICE=mps`.
- Keep `count=1`, `num_inference_steps=2..6`, and `<=512x768` while iterating.
- Non-CUDA fast caps are auto-applied when `NON_CUDA_FORCE_FAST_LIMITS=true`.

## Notes

- This local MVP is optimized for non-CUDA environments.
- The API logs request start/end, progress, elapsed time, and ETA-style heartbeats for both cloth generation and virtual try-on so long-running calls are easier to monitor.
