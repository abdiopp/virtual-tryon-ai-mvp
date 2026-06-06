export function toPreviewUrl(filePath: string) {
  return `/api/files?path=${encodeURIComponent(filePath)}`;
}

export function toDownloadUrl(filePath: string) {
  return `/api/files?path=${encodeURIComponent(filePath)}&download=1`;
}
