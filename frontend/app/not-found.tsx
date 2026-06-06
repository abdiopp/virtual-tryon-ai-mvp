import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f7f3ea_0%,#eef2f7_100%)] px-4">
      <div className="max-w-lg rounded-3xl border border-white/70 bg-white/80 p-8 text-center shadow-glow backdrop-blur">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">404</p>
        <h1 className="mt-3 font-display text-3xl font-semibold">Page not found</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          The route you requested does not exist in the new frontend.
        </p>
        <Link href="/dashboard" className="mt-6 inline-flex">
          <Button>Back to dashboard</Button>
        </Link>
      </div>
    </div>
  );
}

