import { BarChart3, Sparkles, Shirt, Settings2, History } from "lucide-react";

export const navigationItems = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/generate", label: "Generate", icon: Sparkles },
  { href: "/tryon", label: "Try-On", icon: Shirt },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings2 }
] as const;

