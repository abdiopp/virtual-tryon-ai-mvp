import { z } from "zod";
import { garmentCategories } from "@/lib/constants";

export const healthModelsStatusSchema = z.object({
  cloth_generator: z.enum(["available", "missing"]),
  tryon_model: z.enum(["available", "missing"])
});

export const healthResponseSchema = z.object({
  status: z.string(),
  device: z.string(),
  requested_device: z.string(),
  cuda_available: z.boolean(),
  mps_available: z.boolean(),
  models: healthModelsStatusSchema
});

export const generateClothesRequestSchema = z.object({
  prompt: z.string().min(3, "Prompt must be at least 3 characters long"),
  category: z.string().trim().optional().or(z.literal("")).transform((value) => value || undefined),
  negative_prompt: z
    .string()
    .trim()
    .optional()
    .or(z.literal(""))
    .transform((value) => value || undefined),
  count: z.coerce.number().int().min(1).max(8),
  width: z.coerce.number().int().min(256).max(1536),
  height: z.coerce.number().int().min(256).max(1536),
  guidance_scale: z.coerce.number().min(0).max(20),
  num_inference_steps: z.coerce.number().int().min(1).max(100),
  seed: z.preprocess((value) => {
    if (value === "" || value === null || value === undefined) {
      return undefined;
    }
    return value;
  }, z.coerce.number().int().optional())
});

export const generateClothItemSchema = z.object({
  id: z.string(),
  path: z.string(),
  prompt: z.string(),
  seed: z.number().int().nullable().optional(),
  metadata: z.record(z.unknown())
});

export const generateClothesResponseSchema = z.object({
  success: z.boolean(),
  items: z.array(generateClothItemSchema)
});

export const generateClothesJobCreateResponseSchema = z.object({
  success: z.boolean(),
  job_id: z.string(),
  status: z.string()
});

export const generateClothesJobStatusResponseSchema = z.object({
  success: z.boolean(),
  job_id: z.string(),
  status: z.string(),
  items: z.array(generateClothItemSchema),
  metadata: z.record(z.unknown()),
  error: z.string().nullable().optional()
});

export const virtualTryOnPathRequestSchema = z.object({
  person_image_path: z.string().min(1),
  garment_image_path: z.string().min(1),
  category: z.enum(["upper_body", "lower_body", "dress"])
});

export const virtualTryOnResponseSchema = z.object({
  success: z.boolean(),
  result_path: z.string(),
  metadata: z.record(z.unknown())
});

export const virtualTryOnJobCreateResponseSchema = z.object({
  success: z.boolean(),
  job_id: z.string(),
  status: z.string()
});

export const virtualTryOnJobStatusResponseSchema = z.object({
  success: z.boolean(),
  job_id: z.string(),
  status: z.string(),
  result_path: z.string().nullable().optional(),
  metadata: z.record(z.unknown()),
  error: z.string().nullable().optional()
});

export const tryOnCategoryOptions = garmentCategories;

export type HealthResponse = z.infer<typeof healthResponseSchema>;
export type GenerateClothesRequest = z.infer<typeof generateClothesRequestSchema>;
export type GenerateClothItem = z.infer<typeof generateClothItemSchema>;
export type GenerateClothesResponse = z.infer<typeof generateClothesResponseSchema>;
export type GenerateClothesJobCreateResponse = z.infer<typeof generateClothesJobCreateResponseSchema>;
export type GenerateClothesJobStatusResponse = z.infer<typeof generateClothesJobStatusResponseSchema>;
export type VirtualTryOnPathRequest = z.infer<typeof virtualTryOnPathRequestSchema>;
export type VirtualTryOnResponse = z.infer<typeof virtualTryOnResponseSchema>;
export type VirtualTryOnJobCreateResponse = z.infer<typeof virtualTryOnJobCreateResponseSchema>;
export type VirtualTryOnJobStatusResponse = z.infer<typeof virtualTryOnJobStatusResponseSchema>;
