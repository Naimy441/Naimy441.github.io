import rawBuildings from "@/data/campus-buildings.json";
import rawVenues from "@/data/campus-dining-venues.json";
import { isClosingSoon, isOpenNow } from "./hours";
import type {
  CampusBuildingsCollection,
  DiningVenue,
  EnrichedDiningVenue,
  HalalMenu,
  Restaurant,
} from "./types";

export const campusBuildingsData = rawBuildings as unknown as CampusBuildingsCollection;
export const campusVenuesData = rawVenues as unknown as DiningVenue[];

export function normalizeVenueKey(name: string): string {
  return name
    .toLowerCase()
    .replace(/[+&]/g, "and")
    .replace(/[^a-z0-9]/g, "");
}

/**
 * Pairs base venue records with live hours and today's halal menu from getHalalMenu().
 */
export function enrichVenues(
  venues: DiningVenue[],
  halalMenu: HalalMenu
): EnrichedDiningVenue[] {
  const restaurantMap = new Map<string, Restaurant>();

  for (const r of halalMenu.restaurants) {
    restaurantMap.set(normalizeVenueKey(r.name), r);
  }

  return venues.map((v) => {
    // Find matching restaurant by menuName, name, or id
    const candidateKeys = [
      v.menuName ? normalizeVenueKey(v.menuName) : null,
      normalizeVenueKey(v.name),
      normalizeVenueKey(v.id),
    ].filter((k): k is string => k !== null);

    let match: Restaurant | undefined;
    for (const key of candidateKeys) {
      if (restaurantMap.has(key)) {
        match = restaurantMap.get(key);
        break;
      }
    }

    // Also fuzzy check if key contains or is contained by candidate
    if (!match) {
      for (const [key, r] of restaurantMap.entries()) {
        if (
          candidateKeys.some(
            (ck) => key.includes(ck) || ck.includes(key)
          )
        ) {
          match = r;
          break;
        }
      }
    }

    const open = match ? isOpenNow(match.openRanges) : null;
    const closingSoon = match ? isClosingSoon(match.openRanges) : false;
    const hours = match?.hours || (v.isHalalCertified ? "Hours posted daily" : "See Duke Dining");

    return {
      ...v,
      liveRestaurant: match,
      isOpen: open,
      isClosingSoon: closingSoon,
      halalItemCount: match?.itemCount ?? (v.isHalalCertified ? 1 : 0),
      hoursString: hours,
    };
  });
}
