"use client";

import { Copy, ExternalLink, Download, Image as ImageIcon, FileText } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { toDownloadUrl, toPreviewUrl } from "@/lib/file-url";

function copyText(value: string) {
  void navigator.clipboard.writeText(value);
  toast.success("Copied to clipboard.");
}

export function ResultGallery({
  title,
  description,
  items
}: {
  title: string;
  description: string;
  items: Array<{
    id: string;
    path: string;
    prompt?: string;
    seed?: number | null;
    metadata?: Record<string, unknown>;
  }>;
}) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold">{title}</h2>
          <p className="text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {items.map((item, index) => (
          <Card key={item.id} className="overflow-hidden">
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-xl">Result {index + 1}</CardTitle>
                <Badge variant="outline">#{item.id}</Badge>
              </div>
              <CardDescription className="line-clamp-2">{item.prompt ?? item.path}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Tabs defaultValue="preview" className="space-y-4">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="preview">
                    <ImageIcon className="h-4 w-4" />
                    Preview
                  </TabsTrigger>
                  <TabsTrigger value="details">
                    <FileText className="h-4 w-4" />
                    Details
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="preview" className="mt-0 space-y-4">
                  <div className="overflow-hidden rounded-3xl border border-border bg-slate-100 shadow-soft">
                    <img
                      src={toPreviewUrl(item.path)}
                      alt={item.prompt ? item.prompt : `Generated asset ${index + 1}`}
                      className="aspect-[4/5] w-full object-contain bg-white p-3"
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Button variant="outline" onClick={() => copyText(item.path)}>
                      <Copy className="h-4 w-4" />
                      Copy file path
                    </Button>
                    <Button asChild variant="secondary" className="w-full">
                      <a href={toPreviewUrl(item.path)} target="_blank" rel="noreferrer">
                        <ExternalLink className="h-4 w-4" />
                        Open preview
                      </a>
                    </Button>
                    <Button asChild className="sm:col-span-2 w-full">
                      <a href={toDownloadUrl(item.path)} download>
                        <Download className="h-4 w-4" />
                        Download image
                      </a>
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent value="details" className="mt-0 space-y-4">
                  <div className="rounded-2xl border border-border bg-background/70 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Path</p>
                    <p className="mt-2 break-all text-sm leading-6">{item.path}</p>
                  </div>
                  <Separator />
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Seed</p>
                      <p className="mt-1 font-medium">{item.seed ?? "n/a"}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Status</p>
                      <p className="mt-1 font-medium text-emerald-700">Preview ready</p>
                    </div>
                  </div>
                  {item.metadata ? (
                    <details className="rounded-2xl border border-border bg-background/70 p-4">
                      <summary className="cursor-pointer text-sm font-semibold">Metadata</summary>
                      <pre className="mt-3 overflow-auto text-xs leading-6 text-muted-foreground">
                        {JSON.stringify(item.metadata, null, 2)}
                      </pre>
                    </details>
                  ) : null}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
