# Sample API Requests

## Generate Clothes JSON

```json
{
  "prompt": "oversized black hoodie with minimal logo",
  "category": "hoodie",
  "count": 1,
  "width": 1024,
  "height": 1024,
  "guidance_scale": 0.0,
  "num_inference_steps": 4,
  "seed": 123
}
```

## Virtual Try-On from Path JSON

```json
{
  "person_image_path": "uploads/persons/person.png",
  "garment_image_path": "outputs/generated_clothes/cloth.png",
  "category": "upper_body"
}
```
