# cURL Examples

## Health

```bash
curl http://localhost:8000/health
```

## Generate Clothes

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

## Generate Clothes Job

```bash
curl -X POST http://localhost:8000/generate-clothes-jobs \
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

curl http://localhost:8000/generate-clothes-jobs/<job_id>
```

## Virtual Try-On (Upload)

```bash
curl -X POST http://localhost:8000/virtual-tryon \
  -F "person_image=@uploads/persons/test_person.png" \
  -F "garment_image=@outputs/generated_clothes/cloth_001.png" \
  -F "category=upper_body"
```
