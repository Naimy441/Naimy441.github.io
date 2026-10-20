"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ListFilter, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  className?: string;
}

export function FoodViewSwitcher({ className }: Props) {
  const pathname = usePathname();
  const isMap = pathname === "/food/map";

  return (
    <div
      role="tablist"
      aria-label="Food view mode"
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-border/80 bg-muted/60 p-1 shadow-xs",
        className
      )}
    >
      <Link
        href="/food"
        role="tab"
        aria-selected={!isMap}
        className={cn(
          "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition-all active:scale-95",
          !isMap
            ? "bg-background text-foreground shadow-xs"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <ListFilter className="size-3.5" />
        <span>List View</span>
      </Link>

      <Link
        href="/food/map"
        role="tab"
        aria-selected={isMap}
        className={cn(
          "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition-all active:scale-95",
          isMap
            ? "bg-primary text-primary-foreground shadow-xs"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        <MapPin className="size-3.5" />
        <span>Campus Map</span>
      </Link>
    </div>
  );
}
