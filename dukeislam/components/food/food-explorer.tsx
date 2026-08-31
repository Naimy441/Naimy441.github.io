"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, ChevronRight, Clock, Search, SearchX, UtensilsCrossed, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { isOpenNow } from "@/lib/hours";
import { useMounted } from "@/hooks/use-mounted";
import type { HalalMenu, MenuItem, NutritionInfo, Restaurant } from "@/lib/types";
import { ItemDetail } from "./item-detail";

interface Props {
  menu: HalalMenu;
  nutrition: Record<string, NutritionInfo>;
}

export function FoodExplorer({ menu, nutrition }: Props) {
  const [query, setQuery] = useState("");
  const [activeRestaurant, setActiveRestaurant] = useState<string | null>(null);
  const [openOnly, setOpenOnly] = useState(false);
  const [selected, setSelected] = useState<{ item: MenuItem; restaurant: string } | null>(null);
  const mounted = useMounted();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = menu.restaurants
      .filter((r) => (activeRestaurant ? r.name === activeRestaurant : true))
      .filter((r) => (openOnly ? isOpenNow(r.openRanges) === true : true))
      .map((r) => {
        if (!q) return r;
        const categories = r.categories
          .map((c) => ({
            ...c,
            items: c.items.filter(
              (i) =>
                i.name.toLowerCase().includes(q) ||
                c.name.toLowerCase().includes(q) ||
                r.name.toLowerCase().includes(q)
            ),
          }))
          .filter((c) => c.items.length > 0);
        return { ...r, categories, itemCount: categories.reduce((n, c) => n + c.items.length, 0) };
      })
      .filter((r) => r.itemCount > 0);

    if (!mounted) return rows;
    return [...rows].sort((a, b) => {
      const aOpen = isOpenNow(a.openRanges) === true ? 0 : 1;
      const bOpen = isOpenNow(b.openRanges) === true ? 0 : 1;
      return aOpen - bOpen;
    });
  }, [menu.restaurants, query, activeRestaurant, openOnly, mounted]);

  const visibleItems = filtered.reduce((n, r) => n + r.itemCount, 0);

  if (menu.restaurants.length === 0) {
    return (
      <Card className="py-16 text-center">
        <CardContent className="space-y-2">
          <UtensilsCrossed className="mx-auto size-8 text-muted-foreground" />
          <p className="font-medium">Menu isn&apos;t up yet</p>
          <p className="text-sm text-muted-foreground">
            Today&apos;s halal items will show here after the next refresh.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="sticky top-14 z-20 -mx-4 space-y-3 border-b border-border/40 bg-background/90 px-4 py-3 backdrop-blur-md sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0 sm:py-0 sm:backdrop-blur-none">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search dishes or spots…"
            className="h-11 rounded-full bg-card pl-10 pr-10 text-[15px] shadow-none"
            aria-label="Search halal food"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Clear search"
            >
              <X className="size-4" />
            </button>
          )}
        </div>

        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-0.5 sm:mx-0 sm:flex-wrap sm:px-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <FilterChip
            active={openOnly}
            onClick={() => setOpenOnly((v) => !v)}
            className={openOnly ? "border-emerald-600 bg-emerald-600 text-white" : ""}
          >
            <span className={cn("size-1.5 rounded-full", openOnly ? "bg-white" : "bg-emerald-500")} />
            Open now
          </FilterChip>
          <FilterChip active={activeRestaurant === null} onClick={() => setActiveRestaurant(null)}>
            All
          </FilterChip>
          {menu.restaurants.map((r) => (
            <FilterChip
              key={r.name}
              active={activeRestaurant === r.name}
              onClick={() => setActiveRestaurant((cur) => (cur === r.name ? null : r.name))}
            >
              {r.name}
            </FilterChip>
          ))}
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {visibleItems} item{visibleItems === 1 ? "" : "s"}
        {filtered.length !== 1 ? ` · ${filtered.length} spots` : ""}
      </p>

      {filtered.length === 0 ? (
        <Card className="py-14 text-center">
          <CardContent className="space-y-2">
            <SearchX className="mx-auto size-8 text-muted-foreground" />
            <p className="font-medium">Nothing matched</p>
            <p className="text-sm text-muted-foreground">
              Try a different search, or clear the filters.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid items-start gap-4 md:grid-cols-2">
          <AnimatePresence mode="popLayout" initial={false}>
            {filtered.map((r) => (
              <motion.div
                key={r.name}
                layout
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.97 }}
                transition={{ duration: 0.22, ease: [0.21, 0.47, 0.32, 0.98] }}
                className="h-full"
              >
                <RestaurantCard
                  restaurant={r}
                  nutrition={nutrition}
                  forceOpen={query.trim().length > 0}
                  onSelect={(item) => setSelected({ item, restaurant: r.name })}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      <ItemDetail
        open={selected !== null}
        onOpenChange={(open) => !open && setSelected(null)}
        info={
          selected?.item.nutritionKey ? nutrition[selected.item.nutritionKey] ?? null : null
        }
        itemName={selected?.item.name ?? ""}
        restaurant={selected?.restaurant ?? ""}
      />
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
  className,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] font-medium transition-all active:scale-95",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground",
        className
      )}
    >
      {children}
    </button>
  );
}

function RestaurantCard({
  restaurant,
  nutrition,
  forceOpen,
  onSelect,
}: {
  restaurant: Restaurant;
  nutrition: Record<string, NutritionInfo>;
  forceOpen: boolean;
  onSelect: (item: MenuItem) => void;
}) {
  const mounted = useMounted();
  const open = mounted ? isOpenNow(restaurant.openRanges) : null;
  const [expanded, setExpanded] = useState(true);
  const showItems = forceOpen || expanded;

  return (
    <Card className="h-full gap-0 overflow-hidden py-0 transition-shadow hover:shadow-md">
      <CardHeader className="gap-1.5 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex min-w-0 flex-1 items-start gap-2 text-left"
            aria-expanded={showItems}
          >
            <h2 className="text-lg font-semibold leading-tight tracking-tight">
              {restaurant.name}
            </h2>
            <ChevronDown
              className={cn(
                "mt-1 size-4 shrink-0 text-muted-foreground transition-transform",
                showItems && "rotate-180"
              )}
            />
          </button>
          {open !== null && (
            <Badge
              variant="outline"
              className={cn(
                "shrink-0 gap-1.5 rounded-full",
                open
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-border bg-muted text-muted-foreground"
              )}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  open ? "animate-pulse bg-emerald-500" : "bg-muted-foreground/50"
                )}
              />
              {open ? "Open" : "Closed"}
            </Badge>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {restaurant.hours && (
            <p className="flex items-center gap-1.5">
              <Clock className="size-3.5" />
              {restaurant.hours}
            </p>
          )}
          <span>
            {restaurant.itemCount} item{restaurant.itemCount === 1 ? "" : "s"}
          </span>
        </div>
      </CardHeader>
      {showItems && (
        <CardContent className="space-y-4 px-5 pb-5">
          {restaurant.categories.map((category) => (
            <div key={category.name}>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {category.name}
              </p>
              <ul className="divide-y divide-border/60 overflow-hidden rounded-xl border border-border/60">
                {category.items.map((item, i) => {
                  const info = item.nutritionKey ? nutrition[item.nutritionKey] : null;
                  return (
                    <li key={`${item.name}-${i}`}>
                      <button
                        type="button"
                        onClick={() => onSelect(item)}
                        className="flex w-full items-center justify-between gap-2 bg-card px-3 py-2.5 text-left text-sm transition-colors hover:bg-accent/60 active:bg-accent"
                      >
                        <span className="font-medium">{item.name}</span>
                        <span className="flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground">
                          {info?.calories && <span>{info.calories} cal</span>}
                          <ChevronRight className="size-3.5" />
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </CardContent>
      )}
    </Card>
  );
}
