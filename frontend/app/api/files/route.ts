import path from "path";
import { promises as fs } from "fs";
import { NextRequest } from "next/server";

import { supportedFileExtensions } from "@/lib/constants";

const projectRoot = path.resolve(process.cwd(), "..");
const allowedRoots = [path.join(projectRoot, "outputs"), path.join(projectRoot, "uploads")];

function isWithinAllowedRoots(candidate: string) {
  const normalized = path.normalize(candidate);
  return allowedRoots.some((root) => normalized === root || normalized.startsWith(`${root}${path.sep}`));
}

function getContentType(filePath: string) {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case ".png":
      return "image/png";
    case ".jpg":
    case ".jpeg":
      return "image/jpeg";
    case ".webp":
      return "image/webp";
    case ".gif":
      return "image/gif";
    default:
      return supportedFileExtensions.includes(ext) ? "application/octet-stream" : "application/octet-stream";
  }
}

export async function GET(request: NextRequest) {
  const filePath = request.nextUrl.searchParams.get("path");
  const download = request.nextUrl.searchParams.get("download") === "1";
  if (!filePath) {
    return Response.json({ message: "Missing path query parameter" }, { status: 400 });
  }

  const resolvedPath = path.isAbsolute(filePath) ? filePath : path.resolve(projectRoot, filePath);
  if (!isWithinAllowedRoots(resolvedPath)) {
    return Response.json({ message: "File path is outside allowed preview roots" }, { status: 403 });
  }

  try {
    const bytes = await fs.readFile(resolvedPath);
    return new Response(bytes, {
      status: 200,
      headers: {
        "Content-Type": getContentType(resolvedPath),
        "Cache-Control": "no-store",
        ...(download
          ? {
              "Content-Disposition": `attachment; filename="${path.basename(resolvedPath)}"`
            }
          : {})
      }
    });
  } catch {
    return Response.json({ message: "File not found" }, { status: 404 });
  }
}
