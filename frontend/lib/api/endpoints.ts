import { apiClient } from "@/lib/api/client";
import {
  generateClothesRequestSchema,
  generateClothesResponseSchema,
  healthResponseSchema,
  virtualTryOnJobCreateResponseSchema,
  virtualTryOnJobStatusResponseSchema,
  virtualTryOnPathRequestSchema,
  virtualTryOnResponseSchema,
  type GenerateClothesRequest,
  type GenerateClothesResponse,
  type HealthResponse,
  type VirtualTryOnJobCreateResponse,
  type VirtualTryOnJobStatusResponse,
  type VirtualTryOnPathRequest,
  type VirtualTryOnResponse
} from "@/lib/schemas";

export async function getHealth(): Promise<HealthResponse> {
  const data = await apiClient.get("/health");
  return healthResponseSchema.parse(data);
}

export async function generateClothes(input: GenerateClothesRequest): Promise<GenerateClothesResponse> {
  const payload = generateClothesRequestSchema.parse(input);
  const data = await apiClient.post("/generate-clothes", payload);
  return generateClothesResponseSchema.parse(data);
}

export async function virtualTryOnFromUpload(formData: FormData): Promise<VirtualTryOnResponse> {
  const data = await apiClient.post("/virtual-tryon", formData);
  return virtualTryOnResponseSchema.parse(data);
}

export async function virtualTryOnFromPath(input: VirtualTryOnPathRequest): Promise<VirtualTryOnResponse> {
  const payload = virtualTryOnPathRequestSchema.parse(input);
  const data = await apiClient.post("/virtual-tryon-from-path", payload);
  return virtualTryOnResponseSchema.parse(data);
}

export async function createVirtualTryOnUploadJob(formData: FormData): Promise<VirtualTryOnJobCreateResponse> {
  const data = await apiClient.post("/virtual-tryon-jobs/upload", formData);
  return virtualTryOnJobCreateResponseSchema.parse(data);
}

export async function createVirtualTryOnPathJob(input: VirtualTryOnPathRequest): Promise<VirtualTryOnJobCreateResponse> {
  const payload = virtualTryOnPathRequestSchema.parse(input);
  const data = await apiClient.post("/virtual-tryon-jobs/from-path", payload);
  return virtualTryOnJobCreateResponseSchema.parse(data);
}

export async function getVirtualTryOnJob(jobId: string): Promise<VirtualTryOnJobStatusResponse> {
  const data = await apiClient.get(`/virtual-tryon-jobs/${jobId}`);
  return virtualTryOnJobStatusResponseSchema.parse(data);
}
