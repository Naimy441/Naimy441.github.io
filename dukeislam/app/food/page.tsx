import type { Metadata } from "next";
import { getHalalMenu } from "@/lib/menus";
import { getNutritionMap } from "@/lib/nutrition";
import { FoodExplorer } from "@/components/food/food-explorer";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Halal Food",
  description:
    "Halal items being served on Duke's campus today, with hours and nutrition facts.",
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
      <PageHeader
        title="Halal food"
        accent="today"
        description="What's being served on campus right now. Tap a dish for nutrition facts."
      />
      <FoodExplorer menu={menu} nutrition={nutrition} />
    </div>
  );
}
