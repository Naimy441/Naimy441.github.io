import {
  getMonthPrayers,
  prayerTimeToUtc,
  PRAYER_ADDRESS,
  PRAYER_NAMES,
  type DailyPrayers,
} from "@/lib/prayer";

// Statically generated and regenerated every 12 hours, so subscribed
// calendars always pull fresh, accurate athan times.
export const dynamic = "force-static";
export const revalidate = 43200;

const EVENT_MINUTES = 5;

function icsUtc(date: Date): string {
  return date.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

function escapeIcsText(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,");
}

function buildEvents(days: DailyPrayers[], stamp: string): string[] {
  const lines: string[] = [];
  for (const day of days) {
    for (const prayer of PRAYER_NAMES) {
      const hhmm = day.timings[prayer];
      if (!/^\d{1,2}:\d{2}$/.test(hhmm)) continue;
      const start = prayerTimeToUtc(day.date, hhmm);
      const end = new Date(start.getTime() + EVENT_MINUTES * 60_000);
      lines.push(
        "BEGIN:VEVENT",
        `UID:${prayer.toLowerCase()}-${day.date}@dukeislam.org`,
        `DTSTAMP:${stamp}`,
        `DTSTART:${icsUtc(start)}`,
        `DTEND:${icsUtc(end)}`,
        `SUMMARY:${prayer}`,
        `DESCRIPTION:${escapeIcsText(`${prayer} athan · dukeislam.org (ISNA, Shafi Asr)`)}`,
        `LOCATION:${escapeIcsText(PRAYER_ADDRESS)}`,
        "TRANSP:TRANSPARENT",
        "END:VEVENT"
      );
    }
  }
  return lines;
}

export async function GET() {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = now.getUTCMonth() + 1;

  // Current month only; the feed regenerates every 12h, so subscribers roll
  // into each new month automatically.
  let days: DailyPrayers[] = [];
  try {
    days = await getMonthPrayers(year, month);
  } catch {
    // Serve an empty (but valid) calendar rather than erroring; the next
    // 12-hour regeneration will retry.
  }

  const stamp = icsUtc(now);
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//dukeislam.org//Prayer Times//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Prayer Times · Duke",
    "X-WR-CALDESC:Daily athan times at Duke University (ISNA method, Shafi Asr). Auto-updates.",
    "X-WR-TIMEZONE:America/New_York",
    "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
    "X-PUBLISHED-TTL:PT12H",
    ...buildEvents(days, stamp),
    "END:VCALENDAR",
  ];

  return new Response(lines.join("\r\n") + "\r\n", {
    headers: {
      "Content-Type": "text/calendar; charset=utf-8",
      "Content-Disposition": 'inline; filename="duke-prayer-times.ics"',
    },
  });
}
