import { z } from "zod";

const publicEnvSchema = z.object({
  NEXT_PUBLIC_API_BASE_PATH: z.string().default("/api/backend"),
  NEXT_PUBLIC_APP_NAME: z.string().default("Virtual Try-On Studio")
});

export const publicEnv = publicEnvSchema.parse({
  NEXT_PUBLIC_API_BASE_PATH: process.env.NEXT_PUBLIC_API_BASE_PATH,
  NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME
});

export function getBackendApiUrl() {
  return process.env.BACKEND_API_URL || "http://localhost:8000";
}

