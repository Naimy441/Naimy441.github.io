import { Skeleton } from "@/components/ui/skeleton";

export default function FoodLoading() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-10">
      <Skeleton className="mb-2 h-9 w-56" />
      <Skeleton className="mb-8 h-4 w-full max-w-md" />
      <Skeleton className="mb-3 h-11 w-full rounded-full" />
      <div className="mb-5 flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-20 rounded-full" />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-48 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
