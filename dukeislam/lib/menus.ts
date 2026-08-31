import { getCampusHours } from "./campus-hours";
import { parseHours } from "./hours";
import { findNutritionKey, normalizeKey } from "./nutrition";
import type { HalalMenu, Restaurant } from "./types";

const MENU_URL =
  "https://raw.githubusercontent.com/Naimy441/Naimy441.github.io/main/outputs/halal_menus.txt";

// The scraper pings /api/revalidate after each run, which purges the "menus"
// tag. This interval is only a backstop if that ping is missed.
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

async function fetchText(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, {
      next: { revalidate: REVALIDATE_SECONDS, tags: ["menus"] },
    });
    if (!res.ok) return null;
    return res.text();
  } catch {
    return null;
  }
}

/**
 * Overwrites a restaurant's hours with today's live campus hours when
 * available. "Closed" days get empty openRanges (known closed, as opposed to
 * null = hours unknown).
 */
function applyCampusHours(r: Restaurant, hoursByKey: Map<string, string>): Restaurant {
  const live = hoursByKey.get(normalizeKey(r.name));
  if (!live) return r;
  if (/^closed/i.test(live)) {
    return { ...r, hours: "Closed today", openRanges: [] };
  }
  return { ...r, hours: live, openRanges: parseHours(live) };
}

export async function getHalalMenu(): Promise<HalalMenu> {
  const [text, campusHours] = await Promise.all([fetchText(MENU_URL), getCampusHours()]);
  const menu = text ? parseHalalMenus(text) : { restaurants: [], totalItems: 0 };
  menu.restaurants = menu.restaurants.map((r) => applyCampusHours(r, campusHours));
  return menu;
}
