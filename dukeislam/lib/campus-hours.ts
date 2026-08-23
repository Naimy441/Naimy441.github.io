import { normalizeKey } from "./nutrition";

// Duke's campus hours page is day-specific (Sundays differ from weekdays),
// making it the source of truth for whether a spot is open today. The
// scraper's hours snapshots go stale between runs, so we fetch this live.
const REVALIDATE_SECONDS = 1800;

/**
 * Campus-hours location names (normalized) -> NetNutrition restaurant names,
 * mirroring the mapping in src/nutri_scrape.py. Unlisted names pass through
 * unchanged.
 */
const NAME_MAP: Record<string, string> = {
  "beyu blue": "Beyu Blue Coffee",
  "cafe 300": "Café 300",
  "farmstead": "The Farmstead",
  "freeman cafe": "Freeman Café",
  "ginger soy": "Ginger + Soy",
  "it s thyme": "It's Thyme",
  "jb s roasts chops": "J.B.'s Roast & Chops",
  "nasher museum cafe": "Nasher Museum Café",
  "pitchfork s": "The PitchFork",
  "red mango": "Red Mango",
  "saladelia cafe at perkins": "Saladalia @ The Perk",
  "saladelia cafe at sanford": "Sanford Deli",
  "tandoor": "Tandoor Indian Cuisine",
  "the devil s krafthouse": "The Devils Krafthouse",
  "zweli s": "Zweli's Café at Duke Divinity",
};

function decodeEntities(s: string): string {
  return s
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/&amp;/g, "&");
}

function stripTags(s: string): string {
  return s.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}

/** Today's date in Eastern Time as YYYY-MM-DD. */
function etToday(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
  }).format(new Date());
}

/**
 * Fetches today's dining hours from campushours.oit.duke.edu and returns a
 * map of normalizeKey(NetNutrition restaurant name) -> hours string, e.g.
 * "11 am - 9 pm", "10 am - 2:30 pm, 5 pm - 9 pm", or "Closed".
 * Returns an empty map on failure so callers fall back to scraped hours.
 */
export async function getCampusHours(): Promise<Map<string, string>> {
  const hoursByKey = new Map<string, string>();
  try {
    const url = `https://campushours.oit.duke.edu/places/dining?start_date=${etToday()}`;
    const res = await fetch(url, {
      next: { revalidate: REVALIDATE_SECONDS, tags: ["menus"] },
    });
    if (!res.ok) return hoursByKey;
    const html = await res.text();

    // Rows look like: <div ... role="row"> <div role="rowheader">Name</div>
    // <div role="cell"><p>8 am - 9 pm</p></div> ... (first cell = today)
    for (const chunk of html.split(/role="row"/).slice(1)) {
      const header = chunk.match(/role="rowheader"[^>]*>([\s\S]*?)<\/div>/);
      const cell = chunk.match(/role="cell"[^>]*>([\s\S]*?)<\/div>/);
      if (!header || !cell) continue;
      const name = decodeEntities(stripTags(header[1]));
      // Multiple <p> ranges in one cell join with a comma for parseHours.
      const hours = decodeEntities(stripTags(cell[1].replace(/<\/p>\s*<p>/g, ", ")));
      if (!name || !hours) continue;
      const netName = NAME_MAP[normalizeKey(name)] ?? name;
      hoursByKey.set(normalizeKey(netName), hours);
    }
  } catch {
    // Page unreachable: callers fall back to scraped hours.
  }
  return hoursByKey;
}
