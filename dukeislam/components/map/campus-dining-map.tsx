"use client";

import dynamic from "next/dynamic";
import { Loader2, MapPin } from "lucide-react";
import type { EnrichedDiningVenue, NutritionInfo } from "@/lib/types";

interface Props {
  venues: EnrichedDiningVenue[];
  nutrition: Record<string, NutritionInfo>;
}

const DynamicMapContainer = dynamic(
  () => import("./map-container").then((mod) => mod.MapContainer),
  {
    ssr: false,
    loading: () => <MapLoadingSkeleton />,
  }
);

export function CampusDiningMap({ venues, nutrition }: Props) {
  return <DynamicMapContainer venues={venues} nutrition={nutrition} />;
}

function MapLoadingSkeleton() {
  return (
    <div className="relative flex h-[calc(100dvh-3.5rem)] w-full items-center justify-center bg-[#EAE8E3]">
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-border/60 bg-background/90 px-6 py-5 shadow-2xl backdrop-blur-md">
        <div className="relative flex items-center justify-center">
          <div className="size-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
          <MapPin className="absolute size-5 text-primary" />
        </div>
        <div className="text-center">
          <p className="font-semibold text-sm">Loading Duke Campus Dining Map…</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Loading Brodhead Center footprints & halal menus
          </p>
        </div>
      </div>
    </div>
  );
}
