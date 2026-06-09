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
  width: 768,
  height: 1024,
  guidance_scale: 7,
  num_inference_steps: 30,
  seed: undefined
};

export const supportedFileExtensions = [".png", ".jpg", ".jpeg", ".webp", ".gif"];
