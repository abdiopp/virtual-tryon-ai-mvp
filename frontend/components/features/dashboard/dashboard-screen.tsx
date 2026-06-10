"use client";

import Link from "next/link";
import { ArrowRight, CircleAlert, Sparkles, Shirt } from "lucide-react";

import { useHealthQuery } from "@/hooks/use-health";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DashboardSkeleton } from "@/components/layout/loading-cards";
import { ErrorState } from "@/components/layout/error-state";
import { EmptyState } from "@/components/layout/empty-state";
import { cn } from "@/lib/utils";

function StatCard({
  label,
  value,
  tone = "default",
  hint
}: {
  label: string;
  value: string;
  tone?: "default" | "success" | "warning";
  hint: string;
}) {
  const toneClasses =
    tone === "success"
      ? "border-emerald-200 bg-emerald-50/80 text-emerald-900"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50/80 text-amber-950"
        : "border-white/60 bg-white/70 text-foreground";

  return (
    <div className={cn("rounded-3xl border p-6 shadow-soft backdrop-blur", toneClasses)}>
      <p className="text-sm font-medium opacity-70">{label}</p>
      <p className="mt-3 font-display text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-sm leading-6 opacity-80">{hint}</p>
    </div>
  );
}

export function DashboardScreen() {
  const healthQuery = useHealthQuery();

  if (healthQuery.isLoading) {
    return <DashboardSkeleton />;
  }

  if (healthQuery.isError) {
    return (
      <ErrorState
        title="Unable to reach the backend"
        description={healthQuery.error?.message || "The API request failed."}
        onRetry={() => healthQuery.refetch()}
      />
    );
  }

  const health = healthQuery.data;
  const generatorAvailable = health?.models.cloth_generator === "available";
  const tryonAvailable = health?.models.tryon_model === "available";

  return (
    <div className="space-y-8">
      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
        <Card className="overflow-hidden border-white/70 bg-slate-950 text-white shadow-glow">
          <CardHeader className="relative p-8">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(16,185,129,0.18),_transparent_24%),radial-gradient(circle_at_bottom_left,_rgba(59,130,246,0.14),_transparent_24%)]" />
            <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-2xl space-y-4">
                <Badge className="w-fit bg-white/10 text-white">Production-ready workbench</Badge>
                <div className="space-y-3">
                  <CardTitle className="font-display text-3xl leading-tight md:text-5xl">
                    Premium virtual try-on, tuned for the existing backend.
                  </CardTitle>
                  <CardDescription className="max-w-2xl text-slate-300">
                    The frontend keeps the current FastAPI contract intact, while adding polished forms,
                    reliable loading states, and direct previews for generated assets.
                  </CardDescription>
                </div>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/generate">
                  <Button className="bg-white text-slate-950 hover:bg-slate-100">
                    <Sparkles className="h-4 w-4" />
                    Generate clothes
                  </Button>
                </Link>
                <Link href="/tryon">
                  <Button variant="outline" className="border-white/20 bg-white/5 text-white hover:bg-white/10">
                    <Shirt className="h-4 w-4" />
                    Try on outfit
                  </Button>
                </Link>
              </div>
            </div>
          </CardHeader>
        </Card>

        <div className="grid gap-4">
          <StatCard
            label="Backend status"
            value={health?.status ?? "unknown"}
            tone={health?.status === "ok" ? "success" : "warning"}
            hint={`Device reported: ${health?.device ?? "n/a"}`}
          />
          <StatCard
            label="Generation model"
            value={health?.models.cloth_generator ?? "missing"}
            tone={generatorAvailable ? "success" : "warning"}
            hint="Reports whether hosted cloth generation is configured."
          />
          <StatCard
            label="Try-on model"
            value={health?.models.tryon_model ?? "missing"}
            tone={tryonAvailable ? "success" : "warning"}
            hint="Reports whether the configured try-on backend is ready."
          />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="font-display text-2xl">How the backend behaves</CardTitle>
            <CardDescription>
              These are the actual business rules we surfaced from the existing codebase.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-border bg-background/80 p-4">
              <p className="text-sm font-semibold">Generation tuning</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                The backend auto-adjusts low-quality settings on non-CUDA devices and enforces a hard cap of
                8 items per request.
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-background/80 p-4">
              <p className="text-sm font-semibold">Try-on categories</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                The service normalizes category values before sending requests to the configured try-on backend.
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-background/80 p-4">
              <p className="text-sm font-semibold">Storage behavior</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Generated images and uploads are stored on local disk under `outputs/` and `uploads/`.
              </p>
            </div>
            <div className="rounded-2xl border border-border bg-background/80 p-4">
              <p className="text-sm font-semibold">Auth flow</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                No authentication endpoints exist in the current backend, so the frontend operates in public
                access mode.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="font-display text-2xl">Quick links</CardTitle>
            <CardDescription>Jump straight into the core workflows.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link href="/generate" className="block">
              <Button variant="outline" className="w-full justify-between rounded-2xl">
                Open generation studio
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/tryon" className="block">
              <Button variant="outline" className="w-full justify-between rounded-2xl">
                Start virtual try-on
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/history" className="block">
              <Button variant="outline" className="w-full justify-between rounded-2xl">
                Review local history
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {generatorAvailable && tryonAvailable ? (
        <EmptyState
          icon={<CircleAlert className="h-5 w-5" />}
          title="Ready for production use"
          description="The backend reports both models as available. You can start generating garments or running try-ons right away."
          action={
            <Link href="/generate">
              <Button>
                <Sparkles className="h-4 w-4" />
                Start generating
              </Button>
            </Link>
          }
        />
      ) : null}
    </div>
  );
}
