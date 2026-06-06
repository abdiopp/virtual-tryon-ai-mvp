export const garmentCategories = [
  { value: "upper_body", label: "Upper body" },
  { value: "lower_body", label: "Lower body" },
  { value: "dress", label: "Dress" }
] as const;

export const defaultGenerationForm = {
  prompt: "premium oversized black hoodie with minimal logo, studio product photography",
  category: "hoodie",
  negative_prompt:
    "low quality, blurry, distorted, deformed clothing, watermark, text, logo artifacts",
  count: 1,
  width: 512,
  height: 768,
  guidance_scale: 0,
  num_inference_steps: 4,
  seed: undefined
};

export const supportedFileExtensions = [".png", ".jpg", ".jpeg", ".webp", ".gif"];
