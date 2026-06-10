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
- You need a Hugging Face token for hosted cloth generation
- Flux may require accepting the model conditions
- A GPU runtime is no longer required for the default hosted model setup

Suggested Colab GPU settings:

- `count=1`
- `width=1024`
- `height=1024`
- `num_inference_steps=4`
- `CLOTH_INFERENCE_PROVIDER=nscale`
- `TRYON_BACKEND=huggingface_space`

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
%env HF_TOKEN=your_hugging_face_token
%env CLOTH_MODEL_ID=black-forest-labs/FLUX.1-schnell
%env CLOTH_INFERENCE_PROVIDER=nscale
%env TRYON_BACKEND=huggingface_space
%env TRYON_SPACE_ID=yisol/IDM-VTON
%env TRYON_SPACE_API_NAME=/tryon
%env OUTPUT_DIR=outputs
%env UPLOAD_DIR=uploads
```

### 4) Skip local model downloads

The default cloth generation and try-on backends both run on Hugging Face-hosted services, so there are no local model weights to download.

### 5) Start the backend

```bash
!uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Colab will keep this running in the cell output. In a new cell, you can test the API.

### 6) Check health

```bash
!curl http://127.0.0.1:8000/health
```

For the default hosted setup, local device values are informational only.

### 7) Try garment generation

Use the async job endpoint when calling through a public tunnel. It avoids proxy timeouts while image generation is still working.

```bash
!curl -X POST http://127.0.0.1:8000/generate-clothes-jobs \
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
- Keep cloth generation near `1024x1024` with 4 steps
- Try-on runs on the configured Hugging Face Space
- Prefer one request at a time

## Common Failure Fixes

- If cloth generation fails, confirm `HF_TOKEN` is set and the `nscale` provider can serve `black-forest-labs/FLUX.1-schnell`
- If try-on fails, check the Hugging Face Space status and `HF_TOKEN` if you configured a private Space
- If a public tunnel shows a 120-second proxy timeout, use `/generate-clothes-jobs` and poll the returned job id instead of calling `/generate-clothes`.
- If Colab disconnects, restart the notebook cell sequence from the top
- If responses are slow, lower steps or use smaller images
