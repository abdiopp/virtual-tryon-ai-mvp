import { ReactNode } from "react";

export function EmptyState({
  icon,
  title,
  description,
  action
}: {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-dashed border-border/70 bg-white/60 p-10 text-center shadow-soft">
      <div className="mx-auto flex max-w-md flex-col items-center gap-4">
        {icon ? <div className="rounded-2xl bg-primary/10 p-3 text-primary">{icon}</div> : null}
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          <p className="text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
        {action}
      </div>
    </div>
  );
}
