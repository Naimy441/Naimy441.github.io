import { parseHours } from "./hours";
import { findNutritionKey } from "./nutrition";
import type { HalalMenu, Restaurant } from "./types";

const MENU_URL =
  "https://raw.githubusercontent.com/Naimy441/duke_halal/main/outputs/halal_menus.txt";

// GitHub Actions re-scrapes twice daily; refresh at most every 30 minutes.
const REVALIDATE_SECONDS = 1800;

/**
 * Parses the scraper's halal_menus.txt format:
 *   Restaurant Name - hours
 *     Category:
 *       - Item
 */
export function parseHalalMenus(text: string): HalalMenu {
  const restaurants: Restaurant[] = [];
  let current: Restaurant | null = null;
  let currentCategory: { name: string; items: Restaurant["categories"][number]["items"] } | null =
    null;
  let totalItems = 0;

  for (const line of text.split("\n")) {
    if (!line.trim()) continue;

    if (!line.startsWith(" ")) {
      // "Restaurant - hours" (hours may contain " - " too; split on first occurrence)
      const sep = line.indexOf(" - ");
      const name = sep === -1 ? line.trim() : line.slice(0, sep).trim();
      const hours = sep === -1 ? "" : line.slice(sep + 3).trim();
      current = {
        name,
        hours,
        openRanges: parseHours(hours),
        categories: [],
        itemCount: 0,
      };
      currentCategory = null;
      restaurants.push(current);
    } else if (/^ {2}\S.*:$/.test(line)) {
      currentCategory = { name: line.trim().replace(/:$/, ""), items: [] };
      current?.categories.push(currentCategory);
    } else if (line.trim().startsWith("- ") && current && currentCategory) {
      const itemName = line.trim().slice(2).trim();
      currentCategory.items.push({
        name: itemName,
        category: currentCategory.name,
        nutritionKey: findNutritionKey(current.name, itemName),
      });
      current.itemCount++;
      totalItems++;
    }
  }

  return { restaurants: restaurants.filter((r) => r.itemCount > 0), totalItems };
}

async function fetchMenuText(): Promise<string> {
  const res = await fetch(MENU_URL, { next: { revalidate: REVALIDATE_SECONDS } });
  if (!res.ok) throw new Error(`Failed to fetch halal menus: ${res.status}`);
  return res.text();
}

async function readLocalMenuText(): Promise<string | null> {
  // Dev/build fallback: the scrape output lives one level above the app.
  try {
    const { readFile } = await import("node:fs/promises");
    const path = await import("node:path");
    return await readFile(
      path.resolve(process.cwd(), "../outputs/halal_menus.txt"),
      "utf8"
    );
  } catch {
    return null;
  }
}

export async function getHalalMenu(): Promise<HalalMenu> {
  let text: string | null = null;
  try {
    text = await fetchMenuText();
  } catch {
    text = await readLocalMenuText();
  }
  if (!text) return { restaurants: [], totalItems: 0 };
  return parseHalalMenus(text);
}
