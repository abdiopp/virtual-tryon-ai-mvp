"use client";

import { useEffect, useState } from "react";
import { readHistory, type LocalHistoryEntry } from "@/lib/local-history";

export function useLocalHistory() {
  const [history, setHistory] = useState<LocalHistoryEntry[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setHistory(readHistory());
    setReady(true);

    const onStorage = () => setHistory(readHistory());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return { history, setHistory, ready };
}

