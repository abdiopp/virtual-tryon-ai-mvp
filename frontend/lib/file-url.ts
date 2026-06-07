import { publicEnv } from "@/lib/env";

function buildFileUrl(filePath: string, download = false) {
  const basePath = publicEnv.NEXT_PUBLIC_API_BASE_PATH.replace(/\/$/, "");
  const params = new URLSearchParams({
    path: filePath
  });
  if (download) {
    params.set("download", "1");
  }
  return `${basePath}/files?${params.toString()}`;
}

export function toPreviewUrl(filePath: string) {
  return buildFileUrl(filePath);
}

export function toDownloadUrl(filePath: string) {
  return buildFileUrl(filePath, true);
}
