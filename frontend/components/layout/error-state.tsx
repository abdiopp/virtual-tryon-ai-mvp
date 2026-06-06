import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry
}: {
  title?: string;
  description: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-3xl border border-rose-200 bg-rose-50/80 p-6 text-rose-950 shadow-soft">
      <div className="flex items-start gap-4">
        <div className="rounded-2xl bg-rose-100 p-3">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1 space-y-3">
          <div>
            <h3 className="text-base font-semibold">{title}</h3>
            <p className="mt-1 text-sm leading-6 text-rose-900/80">{description}</p>
          </div>
          {onRetry ? (
            <Button type="button" variant="outline" onClick={onRetry} className="border-rose-200 bg-white/70">
              <RefreshCw className="h-4 w-4" />
              Retry
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

