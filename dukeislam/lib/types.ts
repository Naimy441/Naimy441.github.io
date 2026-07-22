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
