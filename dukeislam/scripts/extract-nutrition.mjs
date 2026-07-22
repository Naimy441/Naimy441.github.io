// Extracts nutrition facts for halal items from the repo's scrape output
// (../outputs/restaurants/*.json) into a compact data/nutrition.json that the
// app bundles statically. Re-run after a fresh nutrition scrape:
//   node scripts/extract-nutrition.mjs
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const restaurantsDir = path.resolve(here, "../../outputs/restaurants");
const outFile = path.resolve(here, "../data/nutrition.json");

const normalize = (s) =>
  s
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

const byRestaurant = {};
const byItem = {};
let count = 0;

for (const file of readdirSync(restaurantsDir)) {
  if (!file.endsWith(".json") || file === "index.json" || file === "summary_stats.json") continue;
  const data = JSON.parse(readFileSync(path.join(restaurantsDir, file), "utf8"));
  const restKey = normalize(data.name);
  for (const category of data.categories ?? []) {
    for (const meal of category.meals ?? []) {
      if (!meal.is_halal || !meal.nutrition) continue;
      const n = meal.nutrition;
      const compact = {
        item: n.item_name || meal.name,
        restaurant: data.name,
        category: category.name,
        servingSize: n.serving_info?.serving_size ?? null,
        calories: n.calories ?? null,
        facts: n.nutrition_facts ?? {},
        secondary: n.secondary_nutrients ?? {},
        ingredients: n.ingredients ?? null,
      };
      const itemKey = normalize(meal.name);
      (byRestaurant[restKey] ??= {})[itemKey] = compact;
      // Global fallback keyed by item name alone (first hit wins)
      byItem[itemKey] ??= compact;
      count++;
    }
  }
}

mkdirSync(path.dirname(outFile), { recursive: true });
writeFileSync(outFile, JSON.stringify({ byRestaurant, byItem }, null, 1));
console.log(`Wrote ${count} halal items to ${outFile}`);
