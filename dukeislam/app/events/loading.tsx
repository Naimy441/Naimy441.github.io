import { Skeleton } from "@/components/ui/skeleton";

export default function EventsLoading() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-10">
      <Skeleton className="mb-2 h-9 w-64" />
      <Skeleton className="mb-8 h-4 w-full max-w-md" />
      <Skeleton className="mb-4 h-11 w-full rounded-full" />
      <Skeleton className="mb-5 h-10 w-56 rounded-lg" />
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
