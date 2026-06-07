"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { VirtualTryOnResponse } from "@/lib/schemas";

import { createVirtualTryOnPathJob, createVirtualTryOnUploadJob, getVirtualTryOnJob } from "@/lib/api/endpoints";
import type { VirtualTryOnPathRequest } from "@/lib/schemas";
import { appendHistoryEntry } from "@/lib/local-history";

async function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForTryOnResult(jobId: string): Promise<VirtualTryOnResponse> {
  for (;;) {
    const job = await getVirtualTryOnJob(jobId);
    if (job.status === "completed" && job.result_path) {
      return {
        success: true,
        result_path: job.result_path,
        metadata: job.metadata
      };
    }
    if (job.status === "failed") {
      throw new Error(job.error || "Try-on failed.");
    }
    await sleep(3000);
  }
}

export function useTryOnUploadMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: FormData) => {
      const job = await createVirtualTryOnUploadJob(payload);
      return waitForTryOnResult(job.job_id);
    },
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
    mutationFn: async (payload: VirtualTryOnPathRequest) => {
      const job = await createVirtualTryOnPathJob(payload);
      return waitForTryOnResult(job.job_id);
    },
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
