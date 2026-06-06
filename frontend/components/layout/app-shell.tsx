"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Menu, Sparkles } from "lucide-react";

import { navigationItems } from "@/components/layout/navigation";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { publicEnv } from "@/lib/env";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(15,23,42,0.08),_transparent_25%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.08),_transparent_22%),linear-gradient(180deg,_#f7f3ea_0%,_#f4f7fb_45%,_#eef2f7_100%)] text-foreground">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-white/60 bg-slate-950/95 px-6 py-8 text-slate-100 shadow-glow backdrop-blur xl:block">
          <div className="flex h-full flex-col">
            <Link href="/dashboard" className="flex items-center gap-3">
              <div className="rounded-2xl bg-white/10 p-2 text-emerald-300">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="font-display text-lg font-semibold tracking-tight">{publicEnv.NEXT_PUBLIC_APP_NAME}</p>
                <p className="text-xs text-slate-300">Premium try-on workbench</p>
              </div>
            </Link>

            <nav className="mt-10 space-y-2">
              {navigationItems.map((item) => {
                const active = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition",
                      active
                        ? "bg-white text-slate-950 shadow-soft"
                        : "text-slate-300 hover:bg-white/10 hover:text-white"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="mt-auto rounded-3xl border border-white/10 bg-white/5 p-4">
              <p className="text-sm font-medium text-white">Backend compatibility</p>
              <p className="mt-1 text-xs leading-5 text-slate-300">
                Uses the existing FastAPI endpoints through a local Next proxy, with file previews served safely
                from the workspace.
              </p>
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 border-b border-white/60 bg-white/70 px-4 py-4 backdrop-blur md:px-6 xl:px-8">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 xl:hidden">
                <Sheet>
                  <SheetTrigger asChild>
                    <Button variant="outline" size="icon" className="rounded-2xl">
                      <Menu className="h-4 w-4" />
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="left" className="w-[320px] bg-slate-950 text-slate-100">
                    <SheetHeader>
                      <SheetTitle className="text-left font-display text-xl text-white">
                        {publicEnv.NEXT_PUBLIC_APP_NAME}
                      </SheetTitle>
                    </SheetHeader>
                    <Separator className="my-4 bg-white/10" />
                    <nav className="space-y-2">
                      {navigationItems.map((item) => {
                        const active = pathname === item.href;
                        const Icon = item.icon;
                        return (
                          <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                              "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition",
                              active
                                ? "bg-white text-slate-950"
                                : "text-slate-300 hover:bg-white/10 hover:text-white"
                            )}
                          >
                            <Icon className="h-4 w-4" />
                            {item.label}
                          </Link>
                        );
                      })}
                    </nav>
                  </SheetContent>
                </Sheet>
                <Link href="/dashboard">
                  <p className="font-display text-lg font-semibold tracking-tight">{publicEnv.NEXT_PUBLIC_APP_NAME}</p>
                </Link>
              </div>

              <div className="hidden md:block">
                <p className="text-sm font-medium text-slate-500">Connected to the virtual try-on backend</p>
                <p className="text-xs text-slate-400">Proxy base: {publicEnv.NEXT_PUBLIC_API_BASE_PATH}</p>
              </div>

              <div className="ml-auto flex items-center gap-2">
                <Link href="/generate" className="hidden sm:block">
                  <Button variant="glass">New generation</Button>
                </Link>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-6 md:px-6 md:py-8 xl:px-8">
            <div className="animate-fade-in-up">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
