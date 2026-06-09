# Colab Demo Setup

This guide shows how to run the backend from this repo in Google Colab for a demo, so your local machine only acts as a client.

It is optimized for:

- Fast setup
- Colab GPU demo quality
- A small number of requests, not production traffic

## What This Runs

- FastAPI backend from `app/main.py`
- Cloth generation endpoint
- Virtual try-on endpoint

For a demo, keep the backend only in Colab first. Add the Next.js frontend later if you want a polished UI.

## Recommended Demo Path

1. Use Colab
2. Run the backend in the notebook
3. Expose it with a tunnel
4. Point your browser or frontend to that public URL

## Before You Start

- You need a Google account
- If the model repo is gated, you may need a Hugging Face token
- In Colab, choose a GPU runtime before installing dependencies
- Keep one request active at a time so SDXL and try-on do not compete for VRAM

Suggested Colab GPU settings:

- `DEVICE=auto`
- `NON_CUDA_FORCE_FAST_LIMITS=true`
- `count=1`
- `width=768`
- `height=1024`
- `num_inference_steps=30`
- `FASHN_NUM_TIMESTEPS=30`
- `FASHN_GUIDANCE_SCALE=1.5`

## Colab Notebook Cells

### 1) Clone the repo

```bash
!git clone https://github.com/<your-username>/virtual-tryon-ai-mvp.git
%cd virtual-tryon-ai-mvp
```

If the repo is private, upload a zip or use your auth method of choice.

### 2) Install dependencies

```bash
!pip install -r requirements.txt
```

If Colab asks for more packages during the try-on stage, install them there rather than changing the repo first.

### 3) Set environment variables

```bash
%env DEVICE=auto
%env NON_CUDA_FORCE_FAST_LIMITS=true
%env CLOTH_MODEL_ID=stabilityai/stable-diffusion-xl-base-1.0
%env TRYON_BACKEND=fashn_vton
%env FASHN_NUM_TIMESTEPS=30
%env FASHN_GUIDANCE_SCALE=1.5
%env CLOTH_UNLOAD_AFTER_REQUEST=true
%env MODEL_CACHE_DIR=models/huggingface
%env OUTPUT_DIR=outputs
%env UPLOAD_DIR=uploads
```

If Colab reports CUDA out-of-memory during cloth generation, add:

```bash
%env CLOTH_ENABLE_MODEL_CPU_OFFLOAD=true
```

If needed:

```bash
%env HF_TOKEN=your_hugging_face_token
```

### 4) Download model assets

```bash
!python scripts/download_models.py
```

If you want to split setup into two phases:

```bash
!python scripts/download_models.py --only-clothes
!python scripts/download_models.py --only-tryon
```

### 5) Start the backend

```bash
!uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Colab will keep this running in the cell output. In a new cell, you can test the API.

### 6) Check health

```bash
!curl http://127.0.0.1:8000/health
```

For Colab GPU quality, the health response should include `"device":"cuda"` and `"cuda_available":true`.
If it reports `"device":"cpu"`, switch the notebook runtime to a GPU runtime and restart from the install cell.

### 7) Try garment generation

Use the async job endpoint when calling through a public tunnel. It avoids the 120-second proxy timeout while SDXL is still working.

```bash
!curl -X POST http://127.0.0.1:8000/generate-clothes-jobs \
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

Copy the returned `job_id`, then poll:

```bash
!curl http://127.0.0.1:8000/generate-clothes-jobs/YOUR_JOB_ID
```

The old `/generate-clothes` endpoint still works for local requests, but tunnels can time it out before the model finishes.

### 8) Try virtual try-on from local paths

First upload a person image and use a generated garment image:

```bash
!curl -X POST http://127.0.0.1:8000/virtual-tryon-from-path \
  -H "Content-Type: application/json" \
  -d '{
    "person_image_path": "uploads/persons/person.png",
    "garment_image_path": "outputs/generated_clothes/cloth.png",
    "category": "upper_body"
  }'
```

## If You Want a Public Demo URL

Colab runs locally inside the notebook VM, so your browser cannot reach port 8000 directly from the outside. You need a tunnel.

Choose one:

- `cloudflared`
- `ngrok`
- `localtunnel`

### Quick tunnel idea with cloudflared

```bash
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!dpkg -i cloudflared-linux-amd64.deb
!cloudflared tunnel --url http://127.0.0.1:8000
```

Use the printed public URL in your browser or frontend.

## If You Want the Frontend Too

The frontend lives in `frontend/`.

Once you have a public backend URL:

1. Set `BACKEND_API_URL` to that public URL
2. Run `npm install`
3. Run `npm run dev`
4. Open the frontend in your browser

See [frontend/README.md](frontend/README.md).

## Kaggle Notes

Kaggle can also work for notebooks, and it has no-cost compute, but it is usually less convenient for running a long-lived API plus tunnel.

For this project:

- Use Kaggle for notebook-only demos
- Use Colab if you want the easiest path to a live API demo

## Good Demo Limits

- Keep `count=1`
- Keep cloth generation near `768x1024` with 30 steps on Colab GPU
- Keep FASHN try-on at 30 steps for balanced quality, or 50 steps if you have enough time and VRAM
- Prefer one request at a time

For CPU fallback, use `DEVICE=cpu`, `width=512`, `height=768`, and `num_inference_steps=14`.

## Common Failure Fixes

- If the model cache is incomplete, rerun `python scripts/download_models.py`
- If try-on fails, rerun `python scripts/download_models.py --only-tryon`
- If a public tunnel shows a 120-second proxy timeout, use `/generate-clothes-jobs` and poll the returned job id instead of calling `/generate-clothes`.
- If generation logs `resolution downscaled from 768x1024`, `/health` is probably reporting CPU; enable a Colab GPU runtime or set `NON_CUDA_FORCE_FAST_LIMITS=false` only if you accept slow CPU generation.
- If Colab disconnects, restart the notebook cell sequence from the top
- If responses are slow, lower steps or use smaller images
