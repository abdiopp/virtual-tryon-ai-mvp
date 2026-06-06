import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppProviders } from "@/components/providers/app-providers";
import { cn } from "@/lib/utils";
import "@/app/globals.css";
import "@fontsource/manrope/index.css";
import "@fontsource/space-grotesk/index.css";

export const metadata: Metadata = {
  title: "Virtual Try-On Studio",
  description: "Premium Next.js frontend for the virtual try-on backend."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={cn("font-sans")}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
