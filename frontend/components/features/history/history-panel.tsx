"use client";

import { useMemo } from "react";
import { Trash2, Clock3, GalleryVerticalEnd, Download, ExternalLink } from "lucide-react";

import { useLocalHistory } from "@/hooks/use-local-history";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/layout/empty-state";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/layout/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { clearHistory } from "@/lib/local-history";
import { toDownloadUrl, toPreviewUrl } from "@/lib/file-url";

export function HistoryPanel() {
  const { history, setHistory, ready } = useLocalHistory();

  const sorted = useMemo(() => [...history].sort((a, b) => b.createdAt.localeCompare(a.createdAt)), [history]);

  if (!ready) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="font-display text-2xl">Loading history</CardTitle>
          <CardDescription>Reading saved jobs from the browser.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (sorted.length === 0) {
    return (
      <EmptyState
        icon={<GalleryVerticalEnd className="h-5 w-5" />}
        title="No local history yet"
        description="Generated garments and try-on outputs will appear here after successful requests."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold">Recent jobs</h2>
          <p className="text-sm leading-6 text-muted-foreground">Stored locally in the browser for quick access.</p>
        </div>
        <ConfirmDialog
          trigger={
            <Button variant="outline">
              <Trash2 className="h-4 w-4" />
              Clear history
            </Button>
          }
          title="Clear local history?"
          description="This removes the browser-only job history. It does not delete files from the backend."
          confirmLabel="Clear history"
          onConfirm={() => {
            clearHistory();
            setHistory([]);
          }}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {sorted.map((entry) => (
          <Card key={entry.id}>
            <div className="grid gap-0 md:grid-cols-[0.9fr_1.1fr]">
              <div className="relative min-h-[240px] bg-slate-100">
                {entry.previewPaths[0] ? (
                  <img src={toPreviewUrl(entry.previewPaths[0])} alt={entry.title} className="h-full w-full object-cover" />
                ) : null}
              </div>
              <div className="flex flex-col">
                <CardHeader>
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle className="text-xl">{entry.title}</CardTitle>
                    <Badge variant="outline">{entry.type}</Badge>
                  </div>
                  <CardDescription className="flex items-center gap-2">
                    <Clock3 className="h-4 w-4" />
                    {new Date(entry.createdAt).toLocaleString()}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="rounded-2xl border border-border bg-background/70 p-4 text-sm">
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Preview path</p>
                    <p className="mt-2 break-all">{entry.previewPaths[0] ?? "n/a"}</p>
                  </div>
                  <details className="rounded-2xl border border-border bg-background/70 p-4">
                    <summary className="cursor-pointer text-sm font-semibold">Details</summary>
                    <pre className="mt-3 overflow-auto text-xs leading-6 text-muted-foreground">
                      {JSON.stringify(entry.details, null, 2)}
                    </pre>
                  </details>
                  {entry.previewPaths[0] ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Button asChild variant="secondary">
                        <a href={toPreviewUrl(entry.previewPaths[0])} target="_blank" rel="noreferrer">
                          <ExternalLink className="h-4 w-4" />
                          Open preview
                        </a>
                      </Button>
                      <Button asChild>
                        <a href={toDownloadUrl(entry.previewPaths[0])} download>
                          <Download className="h-4 w-4" />
                          Download image
                        </a>
                      </Button>
                    </div>
                  ) : null}
                </CardContent>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
