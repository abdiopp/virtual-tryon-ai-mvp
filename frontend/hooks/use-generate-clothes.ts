"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { createGenerateClothesJob, getGenerateClothesJob } from "@/lib/api/endpoints";
import type { GenerateClothesRequest, GenerateClothesResponse } from "@/lib/schemas";
import { appendHistoryEntry } from "@/lib/local-history";

async function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForGenerateResult(jobId: string): Promise<GenerateClothesResponse> {
  for (;;) {
    const job = await getGenerateClothesJob(jobId);
    if (job.status === "completed") {
      return {
        success: true,
        items: job.items
      };
    }
    if (job.status === "failed") {
      throw new Error(job.error || "Generation failed.");
    }
    await sleep(3000);
  }
}

export function useGenerateClothesMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: GenerateClothesRequest) => {
      const job = await createGenerateClothesJob(payload);
      return waitForGenerateResult(job.job_id);
    },
    onSuccess: (data, variables) => {
      toast.success(`Generated ${data.items.length} garment${data.items.length > 1 ? "s" : ""}.`);
      appendHistoryEntry({
        id: `generate-${Date.now()}`,
        type: "generate" as const,
        title: variables.prompt,
        createdAt: new Date().toISOString(),
        previewPaths: data.items.map((item) => item.path),
        details: {
          count: data.items.length,
          category: variables.category || "default",
          width: variables.width,
          height: variables.height,
          guidance_scale: variables.guidance_scale,
          num_inference_steps: variables.num_inference_steps,
          seed: variables.seed ?? null,
          items: data.items
        }
      });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    },
    onError: (error) => {
      toast.error(error.message || "Failed to generate garments.");
    }
  });
}
