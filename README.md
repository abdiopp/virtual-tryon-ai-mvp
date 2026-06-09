# virtual-tryon-ai-mvp

A two-stage virtual try-on backend now tuned for Google Colab GPU demos, while still keeping CPU/MPS fallback behavior for local development:

1. Cloth generation: `stabilityai/stable-diffusion-xl-base-1.0` through Diffusers
2. Virtual try-on: `Leffa` backend wrapper at quality-focused Colab settings

This setup is designed for Colab CUDA first. On local machines, `DEVICE=auto` falls back to Apple Silicon MPS or CPU when CUDA is not available.

## Why This Version

- Uses better default models and settings now that the target runtime is Colab.
- Keeps non-CUDA guardrails so local CPU/MPS requests are still bounded.
- Keeps modular FastAPI architecture for future backend integration.

## Architecture

- `app/routes/*`: API endpoints
- `app/services/cloth_generator.py`: Diffusers cloth generation service
- `app/services/tryon_service.py`: Leffa/FASHN try-on backend wrappers
- `scripts/download_models.py`: downloads cloth model + configured try-on backend assets

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

- `CLOTH_MODEL_ID=stabilityai/stable-diffusion-xl-base-1.0`
- `TRYON_BACKEND=leffa`
- `LEFFA_MODEL_DIR=models/leffa`
- `LEFFA_CHECKPOINT_DIR=models/leffa_ckpts`
- `LEFFA_NUM_INFERENCE_STEPS=30`
- `LEFFA_GUIDANCE_SCALE=2.5`
- `LEFFA_MODEL_TYPE=auto`
- `LEFFA_REPAINT=false`
- `FASHN_MODEL_DIR=models/fashn_vton`
- `FASHN_WEIGHTS_DIR=models/fashn_weights`
- `FASHN_NUM_TIMESTEPS=30`
- `FASHN_GUIDANCE_SCALE=1.5`
- `DEVICE=auto` to use CUDA, then MPS, then CPU
- `DEVICE=cpu` to force local CPU
- `DEVICE=mps` to force Apple Silicon
- `NON_CUDA_FORCE_FAST_LIMITS=true` to auto-cap heavy requests
- `CLOTH_UNLOAD_AFTER_REQUEST=true` to free SDXL GPU memory before try-on
- `CLOTH_ENABLE_MODEL_CPU_OFFLOAD=true` if Colab GPU VRAM is tight

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

Download the legacy FASHN backend instead:

```bash
python scripts/download_models.py --only-tryon --tryon-backend fashn_vton
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
    "width": 768,
    "height": 1024,
    "guidance_scale": 7.0,
    "num_inference_steps": 30,
    "seed": 123
  }'
```

For public tunnels or slow SDXL runs, prefer the async job endpoint so the proxy does not time out:

```bash
curl -X POST http://localhost:8000/generate-clothes-jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt":"oversized black hoodie with minimal logo","category":"hoodie","count":1,"width":768,"height":1024,"guidance_scale":7.0,"num_inference_steps":30}'

curl http://localhost:8000/generate-clothes-jobs/<job_id>
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
  --width 768 \
  --height 1024 \
  --num-inference-steps 30 \
  --guidance-scale 7.0
```

Try-on:

```bash
python scripts/virtual_tryon_cli.py \
  --person uploads/persons/test.png \
  --garment outputs/generated_clothes/cloth_001.png \
  --category upper_body
```

## Performance Guidance

- Colab GPU: keep `DEVICE=auto`, `count=1`, `768x1024`, and 30 inference steps for quality.
- Leffa try-on is GPU-first; use Colab CUDA for practical inference speed.
- Intel integrated graphics: set `DEVICE=cpu`.
- Apple Silicon: set `DEVICE=mps`.
- Local non-CUDA iteration: use smaller requests such as `512x768` and `num_inference_steps=14`.
- Non-CUDA fast caps are auto-applied when `NON_CUDA_FORCE_FAST_LIMITS=true`.

## Notes

- This MVP is optimized for Colab CUDA, with bounded local fallbacks for development.
- The API logs request start/end, progress, elapsed time, and ETA-style heartbeats for both cloth generation and virtual try-on so long-running calls are easier to monitor.
