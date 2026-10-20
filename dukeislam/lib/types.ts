export interface MenuItem {
  name: string;
  category: string;
  /** Key into the nutrition dataset, present when nutrition facts are available */
  nutritionKey: string | null;
}

export interface MenuCategory {
  name: string;
  items: MenuItem[];
}

export interface Restaurant {
  name: string;
  hours: string;
  /** Open ranges in minutes-from-midnight ET, e.g. [[420, 900]]. Null when unparseable. */
  openRanges: [number, number][] | null;
  categories: MenuCategory[];
  itemCount: number;
}

export interface HalalMenu {
  restaurants: Restaurant[];
  totalItems: number;
}

export interface NutritionInfo {
  item: string;
  restaurant: string;
  category: string;
  servingSize: string | null;
  calories: string | null;
  facts: Record<
    string,
    { amount: number | null; unit: string | null; daily_value_percent: number | null }
  >;
  secondary: Record<
    string,
    { amount: number | null; unit: string | null; daily_value_percent: number | null }
  >;
  ingredients: string | null;
}

export interface MuslimEvent {
  id: string;
  title: string;
  description: string;
  location: string;
  rsvpUrl: string | null;
  /** ISO 8601 UTC timestamps */
  start: string;
  end: string;
}

export interface DiningVenue {
  id: string;
  name: string;
  menuName?: string;
  building: string;
  buildingId: number;
  campus: "West" | "East" | "Central";
  floor?: string;
  coordinates: [number, number]; // [lat, lng]
  isHalalCertified: boolean;
  halalNotes?: string;
  cuisine: string;
  googleMapsUrl: string;
  dukeMapsUrl: string;
  mobileOrderId?: number | null;
  iconUrl?: string;
}

export interface EnrichedDiningVenue extends DiningVenue {
  liveRestaurant?: Restaurant;
  isOpen: boolean | null;
  isClosingSoon: boolean;
  halalItemCount: number;
  hoursString: string;
}

export interface CampusBuildingProperties {
  id: string;
  name: string;
  shortName: string;
  campus: "West" | "East" | "Central";
  isFocus: boolean;
  isLandmark?: boolean;
  hasHalal: boolean;
  fillColor: string;
  strokeColor: string;
  fillOpacity: number;
  strokeWidth: number;
  center: [number, number];
  venueIds: string[];
}

export interface CampusBuildingFeature {
  type: "Feature";
  id: string;
  properties: CampusBuildingProperties;
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: number[][][] | number[][][][];
  };
}

export interface CampusBuildingsCollection {
  type: "FeatureCollection";
  features: CampusBuildingFeature[];
}

