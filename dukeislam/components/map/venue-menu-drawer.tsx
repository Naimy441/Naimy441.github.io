"use client";

import { useState } from "react";
import {
  Clock,
  ExternalLink,
  MapPin,
  Navigation,
  ShieldCheck,
  Sparkles,
  UtensilsCrossed,
  X,
  ChevronRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useMediaQuery } from "@/hooks/use-media-query";
import { cn } from "@/lib/utils";
import type { EnrichedDiningVenue, MenuItem, NutritionInfo } from "@/lib/types";
import { ItemDetail } from "@/components/food/item-detail";

interface Props {
  venue: EnrichedDiningVenue | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  nutrition: Record<string, NutritionInfo>;
}

export function VenueMenuDrawer({ venue, open, onOpenChange, nutrition }: Props) {
  const isDesktop = useMediaQuery("(min-width: 768px)");
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);

  if (!venue) return null;

  const restaurant = venue.liveRestaurant;
  const categories = restaurant?.categories ?? [];
  const hasHalalMenu = categories.length > 0 && categories.some((c) => c.items.length > 0);

  const content = (
    <div className="flex flex-col gap-5 pb-8">
      {/* Venue Overview Header Info */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          {venue.isHalalCertified && (
            <span className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-2 py-0.5 text-[11px] font-semibold tracking-wider text-white uppercase shadow-xs">
              Halal Verified
            </span>
          )}

          {venue.isOpen !== null && (
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium px-2 py-0.5",
                venue.isOpen
                  ? venue.isClosingSoon
                    ? "border-amber-400 bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                    : "border-emerald-300 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                  : "border-border bg-muted text-muted-foreground"
              )}
            >
              {venue.isOpen
                ? venue.isClosingSoon
                  ? "Closing Soon"
                  : "Open Now"
                : "Closed"}
            </Badge>
          )}

          <Badge variant="secondary" className="text-xs font-normal">
            {venue.campus} Campus
          </Badge>
        </div>

        <div className="space-y-1 text-xs text-muted-foreground pt-1">
          <p className="flex items-center gap-1.5 font-medium text-foreground">
            <MapPin className="size-3.5 text-primary shrink-0" />
            <span>{venue.building}</span>
            {venue.floor && (
              <span className="font-normal text-muted-foreground">· {venue.floor}</span>
            )}
          </p>
          <p className="flex items-center gap-1.5">
            <Clock className="size-3.5 shrink-0" />
            <span>{venue.hoursString}</span>
          </p>
        </div>
      </div>

      {/* Halal Guarantee Banner */}
      {venue.isHalalCertified ? (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs">
          <div className="flex items-start gap-2.5">
            <ShieldCheck className="size-4 text-emerald-700 dark:text-emerald-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <p className="font-semibold text-emerald-950 dark:text-emerald-200">
                Halal Food Guarantee
              </p>
              <p className="leading-relaxed text-emerald-900/85 dark:text-emerald-300/90">
                {venue.halalNotes ||
                  "Verified halal protein options served daily. Always verify preparation station and sauces with dining staff."}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
          <p className="leading-relaxed">
            {venue.halalNotes ||
              "Campus dining venue. Vegetarian and seafood options may be available; meats are not certified halal."}
          </p>
        </div>
      )}

      {/* Action Buttons: 2-Column Directions & DukeMaps */}
      <div className="grid grid-cols-2 gap-2">
        <a
          href={venue.googleMapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-1.5 rounded-lg border border-border bg-background px-3 py-2.5 text-xs font-semibold text-foreground shadow-xs transition-colors hover:bg-accent whitespace-nowrap"
        >
          <Navigation className="size-3.5 text-primary shrink-0" />
          <span>Directions</span>
          <ExternalLink className="size-3 text-muted-foreground ml-1 shrink-0" />
        </a>

        <a
          href={venue.dukeMapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-1.5 rounded-lg border border-border bg-background px-3 py-2.5 text-xs font-semibold text-foreground shadow-xs transition-colors hover:bg-accent whitespace-nowrap"
        >
          <MapPin className="size-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
          <span>DukeMaps View</span>
          <ExternalLink className="size-3 text-muted-foreground ml-1 shrink-0" />
        </a>
      </div>

      {/* Menu Section */}
      <div className="space-y-3 pt-1">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div className="flex items-center gap-1.5">
            <UtensilsCrossed className="size-4 text-primary" />
            <h3 className="font-semibold text-sm">
              {venue.isHalalCertified ? "Today's Halal Items" : "Cuisine & Specialties"}
            </h3>
          </div>
          {venue.isHalalCertified && (
            <span className="text-xs text-muted-foreground">
              {venue.halalItemCount} {venue.halalItemCount === 1 ? "dish" : "dishes"}
            </span>
          )}
        </div>

        {hasHalalMenu ? (
          <div className="space-y-4">
            {categories.map((category) => (
              <div key={category.name} className="space-y-1.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {category.name}
                </p>
                <div className="divide-y divide-border/60 overflow-hidden rounded-xl border border-border bg-card">
                  {category.items.map((item, idx) => {
                    const info = item.nutritionKey ? nutrition[item.nutritionKey] : null;
                    return (
                      <button
                        key={`${item.name}-${idx}`}
                        type="button"
                        onClick={() => setSelectedItem(item)}
                        className="group flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left transition-colors hover:bg-accent/60 active:bg-accent"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium leading-snug group-hover:text-primary transition-colors">
                            {item.name}
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            Nutrition facts & ingredients
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                          {info?.calories && (
                            <span className="rounded-md bg-muted px-2 py-0.5 font-mono text-[11px] font-semibold text-foreground">
                              {info.calories} cal
                            </span>
                          )}
                          <ChevronRight className="size-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        ) : venue.isHalalCertified ? (
          <div className="rounded-xl border border-dashed border-border p-6 text-center">
            <Sparkles className="mx-auto size-5 text-muted-foreground/60 mb-2" />
            <p className="font-medium text-sm">Halal Options Available Daily</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
              {venue.halalNotes ||
                "This spot serves verified halal chicken and beef options during normal dining hours."}
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-border p-5 text-center text-xs text-muted-foreground">
            <p className="font-medium text-foreground text-sm mb-1">{venue.cuisine}</p>
            <p>Visit in person or check the Duke Mobile Order app for full allergen info.</p>
          </div>
        )}
      </div>

      {/* Nutrition Modal for Selected Item */}
      <ItemDetail
        open={selectedItem !== null}
        onOpenChange={(v) => !v && setSelectedItem(null)}
        info={
          selectedItem?.nutritionKey
            ? nutrition[selectedItem.nutritionKey] ?? null
            : null
        }
        itemName={selectedItem?.name ?? ""}
        restaurant={venue.name}
      />
    </div>
  );

  if (isDesktop) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange} modal={false}>
        <SheetContent
          side="right"
          hideOverlay={true}
          className="w-full sm:max-w-md p-0 flex flex-col h-full max-h-screen overflow-hidden z-50 shadow-2xl border-l gap-0 bg-background"
        >
          <SheetHeader className="shrink-0 border-b px-6 py-4 text-left flex flex-row items-center gap-3.5 pr-12">
            {venue.iconUrl && (
              <img
                src={venue.iconUrl}
                alt=""
                className="size-11 rounded-xl object-contain bg-white p-1 border shadow-xs shrink-0"
              />
            )}
            <div className="min-w-0 flex-1">
              <SheetTitle className="text-xl font-bold tracking-tight truncate">
                {venue.name}
              </SheetTitle>
              <SheetDescription className="text-xs truncate">
                {venue.cuisine}
              </SheetDescription>
            </div>
          </SheetHeader>
          <div className="flex-1 min-h-0 overflow-y-auto px-6 pt-5 [overscroll-behavior:contain]">
            {content}
          </div>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent
        overlayClassName="bg-transparent backdrop-blur-none"
        className="max-h-[88dvh] z-50 flex flex-col gap-0 border-t shadow-2xl bg-background"
      >
        <DrawerHeader className="shrink-0 border-b pb-3 text-left px-5 flex flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            {venue.iconUrl && (
              <img
                src={venue.iconUrl}
                alt=""
                className="size-9 rounded-lg object-contain bg-white p-0.5 border shadow-xs shrink-0"
              />
            )}
            <div className="min-w-0 flex-1">
              <DrawerTitle className="text-lg font-bold truncate">{venue.name}</DrawerTitle>
              <DrawerDescription className="text-xs truncate">{venue.cuisine}</DrawerDescription>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground active:scale-95 shrink-0"
            aria-label="Close drawer"
          >
            <X className="size-5" />
          </button>
        </DrawerHeader>
        <div className="flex-1 min-h-0 overflow-y-auto px-5 pt-4 [overscroll-behavior:contain]">
          {content}
        </div>
      </DrawerContent>
    </Drawer>
  );
}
