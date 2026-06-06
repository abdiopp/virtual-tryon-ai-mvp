"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { generateClothes } from "@/lib/api/endpoints";
import type { GenerateClothesRequest } from "@/lib/schemas";
import { appendHistoryEntry } from "@/lib/local-history";

export function useGenerateClothesMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: GenerateClothesRequest) => generateClothes(payload),
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
