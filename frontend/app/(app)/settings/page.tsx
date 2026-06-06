import { PageHeader } from "@/components/layout/page-header";
import { SettingsPanel } from "@/components/features/settings/settings-panel";

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="System"
        title="Settings and compatibility"
        description="Review the proxy configuration, health state, and the backend contract details that shaped the frontend."
      />
      <SettingsPanel />
    </div>
  );
}

