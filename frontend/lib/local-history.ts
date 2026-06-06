export type LocalHistoryEntry =
  | {
      id: string;
      type: "generate";
      title: string;
      createdAt: string;
      previewPaths: string[];
      details: Record<string, unknown>;
    }
  | {
      id: string;
      type: "tryon";
      title: string;
      createdAt: string;
      previewPaths: string[];
      details: Record<string, unknown>;
    };

const storageKey = "vton.local-history";

export function readHistory(): LocalHistoryEntry[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw) as LocalHistoryEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeHistory(entries: LocalHistoryEntry[]) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(storageKey, JSON.stringify(entries));
}

export function clearHistory() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(storageKey);
}

export function appendHistoryEntry(entry: LocalHistoryEntry) {
  const current = readHistory();
  writeHistory([entry, ...current]);
}
