import { PageHeader } from "@/components/layout/page-header";
import { HistoryPanel } from "@/components/features/history/history-panel";

export default function HistoryPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Library"
        title="Local history"
        description="A browser-side history of successful generations and try-on outputs for quick review."
      />
      <HistoryPanel />
    </div>
  );
}

