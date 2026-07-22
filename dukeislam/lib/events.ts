import { etNaiveToUtc } from "./dates";
import type { MuslimEvent } from "./types";

// DukeGroups ICS feed for CML, MSA, Grad/Prof MSA, SJP, Black Muslim
// Coalition, and One for All (same feed the PDF calendar is built from).
const ICS_URL =
  "https://duke.campusgroups.com/ics?group_ids=28807%2C28808%2C28704%2C28600%2C72105%2C73950&school=duke";

const REVALIDATE_SECONDS = 1800;

function unfoldIcs(text: string): string {
  return text.replace(/\r?\n[ \t]/g, "");
}

function unescapeIcsText(value: string): string {
  return value
    .replace(/\\n/gi, "\n")
    .replace(/\\,/g, ",")
    .replace(/\\;/g, ";")
    .replace(/\\\\/g, "\\");
}

function findField(field: string, block: string): { params: string; value: string } | null {
  const re = new RegExp(`^${field}((?:;[^:\\r\\n]*)*):(.*)$`, "m");
  const match = block.match(re);
  if (!match) return null;
  return { params: match[1] ?? "", value: match[2].trim() };
}

/** Parses ICS date-times: "20250903T220000Z" (UTC) or naive Eastern local time. */
function parseIcsDate(raw: string): Date | null {
  const m = raw.match(/^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})(Z)?)?$/);
  if (!m) return null;
  const [, y, mo, d, h = "0", mi = "0", s = "0", z] = m;
  if (z) return new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +s));
  return etNaiveToUtc(+y, +mo, +d, +h, +mi, +s);
}

function cleanDescription(raw: string): string {
  let desc = raw.replace(/---[\s\S]*/, "");
  desc = unescapeIcsText(desc);
  desc = desc.replace(/\s*\.\s*\.\s*(\.\s*)?/g, "\n\n");
  desc = desc.replace(/\n{3,}/g, "\n\n");
  return desc.trim();
}

export function parseIcsEvents(icsText: string): MuslimEvent[] {
  const unfolded = unfoldIcs(icsText);
  const blocks = unfolded.match(/BEGIN:VEVENT[\s\S]*?END:VEVENT/g) ?? [];
  const events: MuslimEvent[] = [];

  for (const block of blocks) {
    const summary = findField("SUMMARY", block)?.value ?? "";
    const rawDescription = findField("DESCRIPTION", block)?.value ?? "";
    const location = unescapeIcsText(findField("LOCATION", block)?.value ?? "");
    const url = findField("URL", block)?.value ?? "";
    const uid = findField("UID", block)?.value ?? "";
    const startRaw = findField("DTSTART", block)?.value ?? "";
    const endRaw = findField("DTEND", block)?.value ?? "";

    const start = parseIcsDate(startRaw);
    const end = parseIcsDate(endRaw) ?? start;
    if (!start || !summary) continue;

    const rsvpMatch = rawDescription.match(/https?:\/\/duke\.campusgroups\.com\/rsvp\?id=\d+/);

    events.push({
      id: uid || `${startRaw}-${summary}`,
      title: unescapeIcsText(summary),
      description: cleanDescription(rawDescription),
      location,
      rsvpUrl: rsvpMatch?.[0] ?? (url || null),
      start: start.toISOString(),
      end: (end ?? start).toISOString(),
    });
  }

  events.sort((a, b) => a.start.localeCompare(b.start));
  return events;
}

export async function getEvents(): Promise<MuslimEvent[]> {
  try {
    const res = await fetch(ICS_URL, { next: { revalidate: REVALIDATE_SECONDS } });
    if (!res.ok) throw new Error(`ICS fetch failed: ${res.status}`);
    return parseIcsEvents(await res.text());
  } catch {
    return [];
  }
}

export interface EventsPayload {
  events: MuslimEvent[];
  upcoming: MuslimEvent[];
  /** Most recent first */
  past: MuslimEvent[];
  /** Server timestamp (ms) the split was computed at */
  asOf: number;
}

export async function getEventsPayload(): Promise<EventsPayload> {
  const events = await getEvents();
  const asOf = Date.now();
  const upcoming = events.filter((e) => new Date(e.end).getTime() >= asOf);
  const past = events
    .filter((e) => new Date(e.end).getTime() < asOf)
    .sort((a, b) => b.start.localeCompare(a.start));
  return { events, upcoming, past, asOf };
}
