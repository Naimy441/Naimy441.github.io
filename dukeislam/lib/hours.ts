/**
 * Parses hour strings from the scraper like:
 *   "7 am - 3 pm"
 *   "11 am - Midnight"
 *   "6:30 am - 7 am, 7:30 am - 11 am, Noon - 2 pm, 5 pm - 9 pm"
 * into ranges of minutes-from-midnight. Returns null when unparseable
 * (e.g. "Hours not available").
 */
export function parseHours(hours: string): [number, number][] | null {
  if (!hours || /not available/i.test(hours)) return null;

  const parseTime = (raw: string, isEnd: boolean): number | null => {
    const token = raw.trim().toLowerCase();
    if (token === "noon") return 12 * 60;
    if (token === "midnight") return isEnd ? 24 * 60 : 0;
    const m = token.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$/);
    if (!m) return null;
    let hour = parseInt(m[1], 10) % 12;
    if (m[3] === "pm") hour += 12;
    return hour * 60 + parseInt(m[2] ?? "0", 10);
  };

  const ranges: [number, number][] = [];
  for (const part of hours.split(",")) {
    const [startRaw, endRaw] = part.split(/\s*[-–]\s*/);
    if (!startRaw || !endRaw) return null;
    const start = parseTime(startRaw, false);
    const end = parseTime(endRaw, true);
    if (start === null || end === null) return null;
    ranges.push([start, end]);
  }
  return ranges.length > 0 ? ranges : null;
}

/** Current minutes-from-midnight in Duke's timezone (America/New_York). */
export function nowInEasternMinutes(): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  }).formatToParts(new Date());
  const hour = parseInt(parts.find((p) => p.type === "hour")?.value ?? "0", 10) % 24;
  const minute = parseInt(parts.find((p) => p.type === "minute")?.value ?? "0", 10);
  return hour * 60 + minute;
}

export function isOpenNow(ranges: [number, number][] | null): boolean | null {
  if (!ranges) return null;
  const now = nowInEasternMinutes();
  return ranges.some(([start, end]) => now >= start && now < end);
}
