"use client";

import { RefreshCw, Server, ShieldAlert } from "lucide-react";

import { useHealthQuery } from "@/hooks/use-health";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/layout/error-state";
import { Separator } from "@/components/ui/separator";
import { publicEnv } from "@/lib/env";

export function SettingsPanel() {
  const healthQuery = useHealthQuery();

  if (healthQuery.isError) {
    return <ErrorState description={healthQuery.error.message} onRetry={() => healthQuery.refetch()} />;
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <Card>
        <CardHeader>
          <Badge variant="outline" className="w-fit">
            Runtime settings
          </Badge>
          <CardTitle className="font-display text-2xl">Frontend environment</CardTitle>
          <CardDescription>These values drive the proxy and the app shell.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="rounded-2xl border border-border bg-background/70 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">App name</p>
            <p className="mt-2 font-medium">{publicEnv.NEXT_PUBLIC_APP_NAME}</p>
          </div>
          <div className="rounded-2xl border border-border bg-background/70 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Public API base path</p>
            <p className="mt-2 font-medium">{publicEnv.NEXT_PUBLIC_API_BASE_PATH}</p>
          </div>
          <div className="rounded-2xl border border-border bg-background/70 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Backend API URL</p>
            <p className="mt-2 break-all font-medium">Server-only ({publicEnv.NEXT_PUBLIC_API_BASE_PATH} proxy)</p>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="font-display text-2xl">Connection status</CardTitle>
            <CardDescription>Health information comes from the existing backend `/health` endpoint.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-border bg-background/70 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Device</p>
                <p className="mt-2 font-semibold">{healthQuery.data?.device ?? "loading..."}</p>
              </div>
              <div className="rounded-2xl border border-border bg-background/70 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Backend status</p>
                <p className="mt-2 font-semibold">{healthQuery.data?.status ?? "loading..."}</p>
              </div>
            </div>
            <Separator />
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-border bg-background/70 p-4">
                <p className="text-sm font-medium">Cloth generation model</p>
                <p className="mt-2 text-sm text-muted-foreground">{healthQuery.data?.models.cloth_generator ?? "loading..."}</p>
              </div>
              <div className="rounded-2xl border border-border bg-background/70 p-4">
                <p className="text-sm font-medium">Try-on model</p>
                <p className="mt-2 text-sm text-muted-foreground">{healthQuery.data?.models.tryon_model ?? "loading..."}</p>
              </div>
            </div>
            <Button variant="outline" onClick={() => healthQuery.refetch()}>
              <RefreshCw className="h-4 w-4" />
              Refresh health
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="font-display text-2xl">Compatibility notes</CardTitle>
            <CardDescription>What the frontend knows about the backend contract.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm leading-6 text-muted-foreground">
            <div className="flex items-start gap-3">
              <Server className="mt-0.5 h-4 w-4 text-emerald-600" />
              <p>
                Requests proxy through Next route handlers, so the browser never has to call the backend directly.
              </p>
            </div>
            <div className="flex items-start gap-3">
              <ShieldAlert className="mt-0.5 h-4 w-4 text-amber-600" />
              <p>
                The backend currently exposes no authentication or authorization endpoints, so the app runs in
                public mode with no route gating.
              </p>
            </div>
            <div className="flex items-start gap-3">
              <Server className="mt-0.5 h-4 w-4 text-emerald-600" />
              <p>
                Generated results are previewed using the local workspace file route, which safely serves assets from
                `outputs/` and `uploads/`.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
