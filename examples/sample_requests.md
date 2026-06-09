# Sample API Requests

## Generate Clothes JSON

```json
{
  "prompt": "oversized black hoodie with minimal logo",
  "category": "hoodie",
  "count": 1,
  "width": 768,
  "height": 1024,
  "guidance_scale": 7.0,
  "num_inference_steps": 30,
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
