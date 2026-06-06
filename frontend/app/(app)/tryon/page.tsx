import { PageHeader } from "@/components/layout/page-header";
import { TryOnForm } from "@/components/features/tryon/tryon-form";

export default function TryOnPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workflow 02"
        title="Virtual try-on"
        description="Run the backend's upload or file-path workflow and preview the returned result image inside the app."
      />
      <TryOnForm />
    </div>
  );
}

