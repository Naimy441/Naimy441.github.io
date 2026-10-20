import type { Metadata } from "next";
import { getHalalMenu } from "@/lib/menus";
import { getNutritionMap } from "@/lib/nutrition";
import { FoodExplorer } from "@/components/food/food-explorer";
import { PageHeader } from "@/components/page-header";
import { FoodViewSwitcher } from "@/components/food/view-switcher";

export const metadata: Metadata = {
  title: "Duke Halal Dining & Campus Menus",
  description:
    "Duke Islam campus guide to halal food at Duke University: daily halal menus, Brodhead Center food stalls, live hours, and nutrition facts.",
  keywords: [
    "Duke Islam halal",
    "Duke halal food",
    "Duke campus dining",
    "Brodhead Center halal",
    "Duke University halal",
  ],
};

export default async function FoodPage() {
  const menu = await getHalalMenu();

  const keys = menu.restaurants.flatMap((r) =>
    r.categories.flatMap((c) =>
      c.items.map((i) => i.nutritionKey).filter((k): k is string => k !== null)
    )
  );
  const nutrition = getNutritionMap([...new Set(keys)]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-10">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-2">
        <PageHeader
          title="Halal food"
          accent="today"
          description="What's being served on campus right now. Tap a dish for nutrition facts."
        />
        <div className="shrink-0 mb-4 sm:mb-0">
          <FoodViewSwitcher />
        </div>
      </div>
      <FoodExplorer menu={menu} nutrition={nutrition} />
    </div>
  );
}

