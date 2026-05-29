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
    "width": 512,
    "height": 768,
    "guidance_scale": 0.0,
    "num_inference_steps": 4,
    "seed": 123
  }'
```

## Virtual Try-On (Upload)

```bash
curl -X POST http://localhost:8000/virtual-tryon \
  -F "person_image=@uploads/persons/test_person.png" \
  -F "garment_image=@outputs/generated_clothes/cloth_001.png" \
  -F "category=upper_body"
```
