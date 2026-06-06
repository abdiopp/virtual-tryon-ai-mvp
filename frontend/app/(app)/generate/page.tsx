import { PageHeader } from "@/components/layout/page-header";
import { GenerateForm } from "@/components/features/generate/generate-form";

export default function GeneratePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Workflow 01"
        title="Garment generation"
        description="Configure prompts, dimensions, and performance settings with inline validation and polished result cards."
      />
      <GenerateForm />
    </div>
  );
}

