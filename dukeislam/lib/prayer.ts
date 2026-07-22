import { etDateKey, etNaiveToUtc } from "./dates";

// Center for Muslim Life, per AlAdhan geocoding
export const PRAYER_ADDRESS = "2080 Duke University Road, Durham, NC 27708";

// Method 2 = ISNA (standard for North America); school 0 = Shafi Asr
const METHOD = 2;
const SCHOOL = 0;
const BASE = "https://api.aladhan.com/v1";

export const PRAYER_NAMES = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"] as const;
export type PrayerName = (typeof PRAYER_NAMES)[number];

export interface DailyPrayers {
  /** "YYYY-MM-DD" (Eastern) */
  date: string;
  /** e.g. "Ṣafar 8, 1448" */
  hijri: string | null;
  /** Prayer name -> "HH:MM" Eastern wall-clock */
  timings: Record<PrayerName, string>;
  sunrise: string | null;
}

function cleanTime(raw: string): string {
  // Calendar endpoint appends the timezone, e.g. "05:03 (EDT)"
  return raw.split(" ")[0];
}

interface AladhanDay {
  timings: Record<string, string>;
  date: {
    gregorian: { date: string }; // DD-MM-YYYY
    hijri: { day: string; year: string; month: { en: string } };
  };
}

function toDailyPrayers(day: AladhanDay): DailyPrayers {
  const [dd, mm, yyyy] = day.date.gregorian.date.split("-");
  const timings = Object.fromEntries(
    PRAYER_NAMES.map((name) => [name, cleanTime(day.timings[name] ?? "")])
  ) as Record<PrayerName, string>;
  const hijri = day.date.hijri
    ? `${day.date.hijri.month.en} ${day.date.hijri.day}, ${day.date.hijri.year} AH`
    : null;
  return {
    date: `${yyyy}-${mm}-${dd}`,
    hijri,
    timings,
    sunrise: day.timings.Sunrise ? cleanTime(day.timings.Sunrise) : null,
  };
}

/** Full month of timings; cached for 12h (times only shift by ~a minute per day). */
export async function getMonthPrayers(year: number, month: number): Promise<DailyPrayers[]> {
  const url = `${BASE}/calendarByAddress/${year}/${month}?address=${encodeURIComponent(
    PRAYER_ADDRESS
  )}&method=${METHOD}&school=${SCHOOL}`;
  const res = await fetch(url, { next: { revalidate: 43200 } });
  if (!res.ok) throw new Error(`AlAdhan calendar fetch failed: ${res.status}`);
  const json = (await res.json()) as { data: AladhanDay[] };
  return json.data.map(toDailyPrayers);
}

/** Today's timings (Eastern). Returns null if the API is unreachable. */
export async function getTodayPrayers(): Promise<DailyPrayers | null> {
  const todayKey = etDateKey(Date.now());
  const [year, month] = [parseInt(todayKey.slice(0, 4), 10), parseInt(todayKey.slice(5, 7), 10)];
  try {
    const days = await getMonthPrayers(year, month);
    return days.find((d) => d.date === todayKey) ?? null;
  } catch {
    return null;
  }
}

/** "17:11" -> "5:11 PM" */
export function to12Hour(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const hour = h % 12 || 12;
  return `${hour}:${String(m).padStart(2, "0")} ${h >= 12 ? "PM" : "AM"}`;
}

/** UTC instant for a prayer's "HH:MM" Eastern wall-clock on a given day. */
export function prayerTimeToUtc(dateKey: string, hhmm: string): Date {
  const [y, m, d] = dateKey.split("-").map(Number);
  const [h, min] = hhmm.split(":").map(Number);
  return etNaiveToUtc(y, m, d, h, min);
}
