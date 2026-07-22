"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronRight, Clock, Search, SearchX, UtensilsCrossed } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { isOpenNow } from "@/lib/hours";
import { useMounted } from "@/hooks/use-mounted";
import type { HalalMenu, MenuItem, NutritionInfo, Restaurant } from "@/lib/types";
import { ItemDetail } from "./item-detail";
import { Stagger, StaggerItem } from "@/components/motion-primitives";

interface Props {
  menu: HalalMenu;
  nutrition: Record<string, NutritionInfo>;
}

export function FoodExplorer({ menu, nutrition }: Props) {
  const [query, setQuery] = useState("");
  const [activeRestaurant, setActiveRestaurant] = useState<string | null>(null);
  const [openOnly, setOpenOnly] = useState(false);
  const [selected, setSelected] = useState<{ item: MenuItem; restaurant: string } | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return menu.restaurants
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
  }, [menu.restaurants, query, activeRestaurant, openOnly]);

  if (menu.restaurants.length === 0) {
    return (
      <Card className="py-16 text-center">
        <CardContent className="space-y-2">
          <UtensilsCrossed className="mx-auto size-8 text-muted-foreground" />
          <p className="font-medium">Menu data is refreshing</p>
          <p className="text-sm text-muted-foreground">
            Today&apos;s halal menus aren&apos;t available right now. Check back shortly.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      {/* Search + filters */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search dishes, categories, or restaurants…"
            className="h-11 rounded-full pl-10 text-[15px] shadow-none"
            aria-label="Search halal food"
          />
        </div>

        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <FilterChip
            active={openOnly}
            onClick={() => setOpenOnly((v) => !v)}
            className={openOnly ? "border-emerald-600 bg-emerald-600 text-white" : ""}
          >
            <span
              className={cn(
                "size-1.5 rounded-full",
                openOnly ? "bg-white" : "bg-emerald-500"
              )}
            />
            Open now
          </FilterChip>
          <FilterChip active={activeRestaurant === null} onClick={() => setActiveRestaurant(null)}>
            All spots
          </FilterChip>
          {menu.restaurants.map((r) => (
            <FilterChip
              key={r.name}
              active={activeRestaurant === r.name}
              onClick={() =>
                setActiveRestaurant((cur) => (cur === r.name ? null : r.name))
              }
            >
              {r.name}
              <span className="text-[11px] opacity-60">{r.itemCount}</span>
            </FilterChip>
          ))}
        </div>
      </div>

      {/* Results */}
      <AnimatePresence mode="popLayout" initial={false}>
        {filtered.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Card className="py-14 text-center">
              <CardContent className="space-y-2">
                <SearchX className="mx-auto size-8 text-muted-foreground" />
                <p className="font-medium">Nothing matched</p>
                <p className="text-sm text-muted-foreground">
                  Try a different search, or clear the filters above.
                </p>
              </CardContent>
            </Card>
          </motion.div>
        ) : (
          <Stagger key="list" className="grid gap-4 md:grid-cols-2" staggerDelay={0.05}>
            {filtered.map((r) => (
              <StaggerItem key={r.name}>
                <RestaurantCard
                  restaurant={r}
                  nutrition={nutrition}
                  onSelect={(item) => setSelected({ item, restaurant: r.name })}
                />
              </StaggerItem>
            ))}
          </Stagger>
        )}
      </AnimatePresence>

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
        "flex shrink-0 items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition-all active:scale-95",
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
  onSelect,
}: {
  restaurant: Restaurant;
  nutrition: Record<string, NutritionInfo>;
  onSelect: (item: MenuItem) => void;
}) {
  // Wall-clock dependent; only computed after mount so ISR-rendered HTML
  // never disagrees with the client at hydration time.
  const mounted = useMounted();
  const open = mounted ? isOpenNow(restaurant.openRanges) : null;

  return (
    <Card className="h-full gap-4 overflow-hidden pt-5 transition-shadow hover:shadow-md">
      <CardHeader className="gap-1.5">
        <div className="flex items-start justify-between gap-3">
          <h2 className="text-lg font-semibold leading-tight tracking-tight">
            {restaurant.name}
          </h2>
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
        {restaurant.hours && (
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="size-3.5" />
            {restaurant.hours}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
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
    </Card>
  );
}
