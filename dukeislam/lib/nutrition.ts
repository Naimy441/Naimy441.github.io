import nutritionData from "@/data/nutrition.json";
import type { NutritionInfo } from "./types";

interface NutritionDataset {
  byRestaurant: Record<string, Record<string, NutritionInfo>>;
  byItem: Record<string, NutritionInfo>;
}

const data = nutritionData as unknown as NutritionDataset;

export function normalizeKey(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Finds nutrition facts for a menu item, preferring a match within the same
 * restaurant and falling back to a global item-name match. Returns the lookup
 * key ("restKey/itemKey", with "*" as restKey for global) or null when nothing matches.
 */
export function findNutritionKey(restaurant: string, item: string): string | null {
  const restKey = normalizeKey(restaurant);
  const itemKey = normalizeKey(item);
  if (data.byRestaurant[restKey]?.[itemKey]) return `${restKey}/${itemKey}`;
  if (data.byItem[itemKey]) return `*/${itemKey}`;
  return null;
}

export function getNutrition(key: string): NutritionInfo | null {
  const slash = key.indexOf("/");
  if (slash === -1) return null;
  const restKey = key.slice(0, slash);
  const itemKey = key.slice(slash + 1);
  if (restKey === "*") return data.byItem[itemKey] ?? null;
  return data.byRestaurant[restKey]?.[itemKey] ?? null;
}

/** Full nutrition map keyed by lookup key, for passing to client components. */
export function getNutritionMap(keys: string[]): Record<string, NutritionInfo> {
  const map: Record<string, NutritionInfo> = {};
  for (const key of keys) {
    const info = getNutrition(key);
    if (info) map[key] = info;
  }
  return map;
}

export interface CatalogRestaurant {
  name: string;
  categories: { name: string; items: { name: string; nutritionKey: string }[] }[];
}

/**
 * Every restaurant with halal items in the full-catalog nutrition scrape,
 * regardless of whether it's serving today. Used to backfill the food page so
 * closed/not-serving spots are still browsable.
 */
export function getCatalogRestaurants(): CatalogRestaurant[] {
  const restaurants: CatalogRestaurant[] = [];
  for (const [restKey, items] of Object.entries(data.byRestaurant)) {
    const infos = Object.entries(items);
    if (infos.length === 0) continue;
    const byCategory = new Map<string, { name: string; nutritionKey: string }[]>();
    for (const [itemKey, info] of infos) {
      const list = byCategory.get(info.category) ?? [];
      list.push({ name: info.item, nutritionKey: `${restKey}/${itemKey}` });
      byCategory.set(info.category, list);
    }
    restaurants.push({
      name: infos[0][1].restaurant,
      categories: [...byCategory.entries()].map(([name, list]) => ({ name, items: list })),
    });
  }
  restaurants.sort((a, b) => a.name.localeCompare(b.name));
  return restaurants;
}
