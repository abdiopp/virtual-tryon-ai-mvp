# virtual-tryon-ai-mvp

A two-stage virtual try-on backend that runs both generated garment images and virtual try-on on Hugging Face by default:

1. Cloth generation: `black-forest-labs/FLUX.1-schnell` through Hugging Face Inference Providers (`nscale`)
2. Virtual try-on: `yisol/IDM-VTON` through the Hugging Face Space Gradio API

Both model workloads run on Hugging Face, not your device or Google Colab.

## Why This Version

- Uses the public IDM-VTON Hugging Face Space for try-on inference.
- Uses hosted Flux Schnell generation for complete garment catalog images.
- Keeps modular FastAPI architecture for future backend integration.

## Architecture

- `app/routes/*`: API endpoints
- `app/services/cloth_generator.py`: Hugging Face Inference Provider cloth generation service
- `app/services/tryon_service.py`: Hugging Face Space, Leffa, and FASHN try-on backend wrappers
- `scripts/download_models.py`: downloads optional local try-on backend assets

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

- `CLOTH_MODEL_ID=black-forest-labs/FLUX.1-schnell`
- `CLOTH_INFERENCE_PROVIDER=nscale`
- `TRYON_BACKEND=huggingface_space`
- `TRYON_SPACE_ID=yisol/IDM-VTON`
- `TRYON_SPACE_API_NAME=/tryon`
- `TRYON_SPACE_DENOISE_STEPS=30`
- `TRYON_SPACE_SEED=42`
- `TRYON_SPACE_AUTO_MASK=true`
- `TRYON_SPACE_AUTO_CROP=false`
- `TRYON_SPACE_TIMEOUT_SECONDS=180`
- `TRYON_SPACE_MAX_RETRIES=2`
- `TRYON_SPACE_RETRY_BACKOFF_SECONDS=2.0`
- `TRYON_MAX_QUEUED_JOBS=8`
- `LEFFA_MODEL_DIR=models/leffa`
- `LEFFA_CHECKPOINT_DIR=models/leffa_ckpts`
- `LEFFA_NUM_INFERENCE_STEPS=30`
- `LEFFA_GUIDANCE_SCALE=2.5`
- `LEFFA_MODEL_TYPE=auto`
- `LEFFA_REPAINT=false`
- `LEFFA_REQUIRE_CUDA=true`
- `LEFFA_MEMORY_EFFICIENT_LOAD=true`
- `FASHN_MODEL_DIR=models/fashn_vton`
- `FASHN_WEIGHTS_DIR=models/fashn_weights`
- `FASHN_NUM_TIMESTEPS=30`
- `FASHN_GUIDANCE_SCALE=1.5`
- `HF_TOKEN=<your token>` is required for hosted cloth generation

Backward compatibility alias supported:

- `SDXL_MODEL_ID` -> `CLOTH_MODEL_ID`

## Download Models

The default setup does not need local cloth or try-on model downloads. Set `HF_TOKEN` so the backend can call the Hugging Face Inference Provider. Flux model access may require signing in to Hugging Face and accepting the model conditions for `black-forest-labs/FLUX.1-schnell`.

Download optional local Leffa try-on assets only if you set `TRYON_BACKEND=leffa`:

```bash
python scripts/download_models.py --only-tryon --tryon-backend leffa
```

Download optional local FASHN assets only if you set `TRYON_BACKEND=fashn_vton`:

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
    "width": 1024,
    "height": 1024,
    "guidance_scale": 0.0,
    "num_inference_steps": 4,
    "seed": 123
  }'
```

For public tunnels or slow image generation runs, prefer the async job endpoint so the proxy does not time out:

```bash
curl -X POST http://localhost:8000/generate-clothes-jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt":"oversized black hoodie with minimal logo","category":"hoodie","count":1,"width":1024,"height":1024,"guidance_scale":0.0,"num_inference_steps":4}'

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
  --width 1024 \
  --height 1024 \
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

- Cloth generation runs on Hugging Face Inference Providers, so local CUDA is not required for `/generate-clothes`.
- Try-on inference runs on the configured Hugging Face Space, so local CUDA is not required for `/virtual-tryon`.
- For Flux Schnell, keep `1024x1024`, 4 inference steps, and `guidance_scale=0.0`.

## Notes

- This MVP is optimized to keep model inference off your machine by using Hugging Face-hosted services.
- The API logs request start/end and elapsed time so long-running remote calls are easier to monitor.
