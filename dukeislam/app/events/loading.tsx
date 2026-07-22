import { Skeleton } from "@/components/ui/skeleton";

export default function EventsLoading() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-12">
      <Skeleton className="mb-3 h-9 w-72" />
      <Skeleton className="mb-8 h-4 w-full max-w-xl" />
      <Skeleton className="mb-6 h-9 w-48 rounded-lg" />
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
