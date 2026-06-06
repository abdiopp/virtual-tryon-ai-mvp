"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { virtualTryOnFromPath, virtualTryOnFromUpload } from "@/lib/api/endpoints";
import type { VirtualTryOnPathRequest } from "@/lib/schemas";
import { appendHistoryEntry } from "@/lib/local-history";

export function useTryOnUploadMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: FormData) => virtualTryOnFromUpload(payload),
    onSuccess: (data) => {
      toast.success("Virtual try-on completed.");
      appendHistoryEntry({
        id: `tryon-${Date.now()}`,
        type: "tryon" as const,
        title: "Virtual try-on result",
        createdAt: new Date().toISOString(),
        previewPaths: [data.result_path],
        details: data.metadata
      });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    },
    onError: (error) => {
      toast.error(error.message || "Try-on failed.");
    }
  });
}

export function useTryOnPathMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: VirtualTryOnPathRequest) => virtualTryOnFromPath(payload),
    onSuccess: (data) => {
      toast.success("Virtual try-on completed.");
      appendHistoryEntry({
        id: `tryon-${Date.now()}`,
        type: "tryon" as const,
        title: "Virtual try-on result",
        createdAt: new Date().toISOString(),
        previewPaths: [data.result_path],
        details: data.metadata
      });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    },
    onError: (error) => {
      toast.error(error.message || "Try-on failed.");
    }
  });
}
