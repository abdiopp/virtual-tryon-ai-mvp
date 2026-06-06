import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f7f3ea_0%,#eef2f7_100%)] p-6">
      <div className="mx-auto grid max-w-6xl gap-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-80 w-full rounded-3xl" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-60 rounded-3xl" />
          <Skeleton className="h-60 rounded-3xl" />
        </div>
      </div>
    </div>
  );
}

