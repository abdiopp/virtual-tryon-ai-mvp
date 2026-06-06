# Backend Contract Analysis

This frontend was designed against the existing Python backend in the repo root. The backend currently exposes a small, public API with no authentication layer.

## Base Behavior

- The FastAPI app is defined in `app/main.py`.
- There are three public API routes plus the root metadata endpoint.
- Generated outputs are written to local disk under `outputs/`.
- Uploaded person and garment images are written to local disk under `uploads/`.
- The backend does not serve those files over HTTP, so the frontend includes a safe file-preview route that reads the workspace files directly.

## Endpoints

| Method | Path | Purpose | Request | Response |
| --- | --- | --- | --- | --- |
| GET | `/` | API metadata | None | `{ name, status, docs }` |
| GET | `/health` | Model and device status | None | `{ status, device, models: { cloth_generator, tryon_model } }` |
| POST | `/generate-clothes` | Generate garment images from text | JSON body | `{ success, items[] }` |
| POST | `/virtual-tryon` | Run try-on with uploaded files | `multipart/form-data` | `{ success, result_path, metadata }` |
| POST | `/virtual-tryon-from-path` | Run try-on using local file paths | JSON body | `{ success, result_path, metadata }` |

## Schemas

### `GET /health`

Response:

```json
{
  "status": "ok",
  "device": "cpu",
  "models": {
    "cloth_generator": "available",
    "tryon_model": "missing"
  }
}
```

### `POST /generate-clothes`

Request:

```json
{
  "prompt": "oversized black hoodie with minimal logo",
  "category": "hoodie",
  "negative_prompt": "low quality, blurry",
  "count": 1,
  "width": 512,
  "height": 768,
  "guidance_scale": 0,
  "num_inference_steps": 4,
  "seed": 123
}
```

Response:

```json
{
  "success": true,
  "items": [
    {
      "id": "cloth_abc123",
      "path": "/abs/path/outputs/generated_clothes/cloth_abc123.png",
      "prompt": "front view ecommerce product photo ...",
      "seed": 123,
      "metadata": {
        "category": "hoodie",
        "width": 512,
        "height": 768,
        "guidance_scale": 0,
        "num_inference_steps": 4,
        "device": "cpu",
        "model_id": "stabilityai/sd-turbo",
        "performance_notes": "none",
        "image_index": 1,
        "total_images": 1,
        "generation_seconds": 4.123,
        "request_seconds": 4.456
      }
    }
  ]
}
```

### `POST /virtual-tryon`

Request:

- `person_image`: uploaded file
- `garment_image`: uploaded file
- `category`: `upper_body`, `lower_body`, or `dress`

Response:

```json
{
  "success": true,
  "result_path": "/abs/path/outputs/tryon_results/tryon_result_abc123.png",
  "metadata": {
    "category": "tops",
    "source_person": "/abs/path/uploads/persons/person_abc.png",
    "source_garment": "/abs/path/uploads/garments/garment_xyz.png",
    "tryon_backend": "fashn_vton",
    "runtime_device": "cpu",
    "generation_seconds": 12.345,
    "request_seconds": 12.345
  }
}
```

### `POST /virtual-tryon-from-path`

Request:

```json
{
  "person_image_path": "uploads/persons/person.png",
  "garment_image_path": "outputs/generated_clothes/cloth.png",
  "category": "upper_body"
}
```

Response is identical to the upload flow.

## Authentication and Authorization

- No auth endpoints exist in the backend.
- No JWT, session, OAuth, API key, or role-based access control is implemented.
- The frontend therefore runs in public mode.
- The app keeps an auth abstraction point in the structure, but there is no active login gate because the backend cannot support one today.

## Roles and Permissions

- No roles or permission model is enforced by the backend.
- Every route is currently public.

## Data Relationships

- `generate-clothes` produces one or more generated garment images.
- Each generated item includes an absolute filesystem path and metadata.
- `virtual-tryon` depends on one person image and one garment image.
- `virtual-tryon-from-path` accepts the same inputs as filesystem paths rather than uploads.
- Both workflows write files to disk and return those paths for downstream preview.

## Business Logic

### Cloth generation

- Uses a Diffusers text-to-image pipeline.
- Default model: `stabilityai/sd-turbo`.
- `count` is clamped to `1..8`.
- On non-CUDA devices, the backend may reduce count, steps, and resolution for performance.
- If the model is SDXL-like, the backend enforces extra quality guardrails for width, height, steps, and guidance.
- For turbo models, guidance is forced to `0.0`.
- A prompt enhancement template can rewrite the user prompt into a product-photo prompt.

### Try-on

- Categories are normalized to `tops`, `bottoms`, or `one-pieces`.
- The FASHN repository and required weights must exist before inference can run.
- The backend streams progress logs while the subprocess runs, but it does not expose live progress in the HTTP response.

## Frontend Integration Notes

- The Next.js app proxies all backend API calls through `/api/backend/*`.
- The Next.js app previews local result files through `/api/files?path=...`.
- Generated result cards show the returned `path` and metadata directly.
- Because the backend does not provide file URLs, previews rely on workspace access from the frontend server.

