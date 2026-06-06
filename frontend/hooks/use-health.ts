"use client";

import { useQuery } from "@tanstack/react-query";
import { getHealth } from "@/lib/api/endpoints";

export function useHealthQuery() {
  return useQuery({
    queryKey: ["health"],
    queryFn: getHealth
  });
}

