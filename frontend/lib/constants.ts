export const garmentCategories = [
  { value: "upper_body", label: "Upper body" },
  { value: "lower_body", label: "Lower body" },
  { value: "dress", label: "Dress" }
] as const;

export const defaultGenerationForm = {
  prompt: "oversized black hoodie with minimal logo",
  category: "hoodie",
  negative_prompt:
    "low quality, blurry, distorted, cropped garment, close-up fabric, partial clothing, cut off edges, watermark, text, logo artifacts",
  count: 1,
  width: 1024,
  height: 1024,
  guidance_scale: 0,
  num_inference_steps: 4,
  seed: undefined
};

export const supportedFileExtensions = [".png", ".jpg", ".jpeg", ".webp", ".gif"];
