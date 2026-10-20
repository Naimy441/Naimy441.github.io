import type { Metadata } from "next";
import { getHalalMenu } from "@/lib/menus";
import { getNutritionMap } from "@/lib/nutrition";
import { enrichVenues, campusVenuesData } from "@/lib/map-data";
import { CampusDiningMap } from "@/components/map/campus-dining-map";

export const metadata: Metadata = {
  title: "Duke Halal Dining Map — Interactive Campus Discovery",
  description:
    "Explore halal dining across Duke University with the interactive Duke Islam campus map. Find open spots in Brodhead Center, Bryan Center, and East Campus with live menus and nutrition facts.",
  keywords: [
    "Duke Islam map",
    "Duke halal map",
    "Duke campus dining map",
    "Brodhead Center halal map",
    "Duke University halal",
  ],
};

export default async function CampusMapPage() {
  const menu = await getHalalMenu();

  const keys = menu.restaurants.flatMap((r) =>
    r.categories.flatMap((c) =>
      c.items.map((i) => i.nutritionKey).filter((k): k is string => k !== null)
    )
  );
  const nutrition = getNutritionMap([...new Set(keys)]);
  const enrichedVenues = enrichVenues(campusVenuesData, menu);

  return (
    <div className="relative flex flex-col h-[calc(100dvh-3.5rem)] w-full overflow-hidden">
      <CampusDiningMap venues={enrichedVenues} nutrition={nutrition} />
    </div>
  );
}
