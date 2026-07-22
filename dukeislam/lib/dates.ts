const TZ = "America/New_York";

/** Offset (ms) of a timezone from UTC at a given instant. */
export function tzOffsetMs(timeZone: string, date: Date): number {
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts: Record<string, number> = {};
  for (const p of dtf.formatToParts(date)) {
    if (p.type !== "literal") parts[p.type] = parseInt(p.value, 10);
  }
  const asUtc = Date.UTC(
    parts.year,
    parts.month - 1,
    parts.day,
    parts.hour % 24,
    parts.minute,
    parts.second
  );
  return asUtc - date.getTime();
}

/** Converts a naive Eastern-time wall clock to a UTC Date (DST-aware, two-pass). */
export function etNaiveToUtc(
  year: number,
  month: number,
  day: number,
  hour = 0,
  minute = 0,
  second = 0
): Date {
  const utcGuess = Date.UTC(year, month - 1, day, hour, minute, second);
  const offset1 = tzOffsetMs(TZ, new Date(utcGuess));
  const offset2 = tzOffsetMs(TZ, new Date(utcGuess - offset1));
  return new Date(utcGuess - offset2);
}

/** "YYYY-MM-DD" for an instant, in Duke's timezone. */
export function etDateKey(iso: string | number | Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

export function etTime(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function etDayHeading(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date(iso));
}

export function etYear(iso: string): number {
  return parseInt(etDateKey(iso).slice(0, 4), 10);
}

export function monthLabel(year: number, month: number): string {
  return new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" }).format(
    new Date(Date.UTC(year, month - 1, 15))
  );
}

/** Calendar structure for a civil month (timezone-independent once y/m known). */
export function monthGrid(year: number, month: number): (number | null)[] {
  const firstWeekday = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const cells: (number | null)[] = Array.from({ length: firstWeekday }, () => null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

/** "Wednesday, July 22" for a "YYYY-MM-DD" key (no timezone shifting). */
export function formatDateKey(key: string): string {
  const [y, m, d] = key.split("-").map(Number);
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date(Date.UTC(y, m - 1, d)));
}

export function dateKeyOf(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}
