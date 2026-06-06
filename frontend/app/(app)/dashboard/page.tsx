import { DashboardScreen } from "@/components/features/dashboard/dashboard-screen";
import { PageHeader } from "@/components/layout/page-header";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Overview"
        title="Command center"
        description="Monitor backend readiness, jump into the key workflows, and keep the real API contract front and center."
      />
      <DashboardScreen />
    </div>
  );
}

