import type { Metadata } from "next";
import { getHalalMenu } from "@/lib/menus";
import { getNutritionMap } from "@/lib/nutrition";
import { FoodExplorer } from "@/components/food/food-explorer";

export const metadata: Metadata = {
  title: "Halal Food",
  description:
    "Every halal item served on Duke's campus today, with hours and nutrition facts. Updated twice daily from Duke NetNutrition.",
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
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-12">
      <div className="mb-6 space-y-2 md:mb-8">
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
          Halal food <span className="font-display italic text-primary">today</span>
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground md:text-base">
          Every halal-certified item on Duke&apos;s campus menus, refreshed twice a
          day. Tap an item to see full nutrition facts and ingredients.
        </p>
      </div>
      <FoodExplorer menu={menu} nutrition={nutrition} />
    </div>
  );
}
