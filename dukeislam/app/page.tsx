import Link from "next/link";
import { ArrowRight, CalendarDays, FileText, MapPin, UtensilsCrossed } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Hero } from "@/components/home/hero";
import { StatCounter } from "@/components/home/stat-counter";
import { PrayerTimes, type PrayerEntry } from "@/components/home/prayer-times";
import { FadeIn, Stagger, StaggerItem } from "@/components/motion-primitives";
import { getHalalMenu } from "@/lib/menus";
import { getEventsPayload } from "@/lib/events";
import { getTodayPrayers, prayerTimeToUtc, to12Hour, PRAYER_NAMES } from "@/lib/prayer";
import { etDayHeading, etTime, formatDateKey } from "@/lib/dates";

export default async function Home() {
  const [menu, { upcoming }, today] = await Promise.all([
    getHalalMenu(),
    getEventsPayload(),
    getTodayPrayers(),
  ]);

  let prayerEntries: PrayerEntry[] | null = null;
  if (today) {
    prayerEntries = PRAYER_NAMES.map((name) => ({
      name: name as string,
      display: to12Hour(today.timings[name]),
      utcMs: prayerTimeToUtc(today.date, today.timings[name]).getTime(),
      kind: "prayer" as const,
    }));
    if (today.sunrise) {
      prayerEntries.splice(1, 0, {
        name: "Sunrise",
        display: to12Hour(today.sunrise),
        utcMs: prayerTimeToUtc(today.date, today.sunrise).getTime(),
        kind: "sunrise",
      });
    }
  }

  const nextEvents = upcoming.slice(0, 3);
  const topRestaurants = [...menu.restaurants]
    .sort((a, b) => b.itemCount - a.itemCount)
    .slice(0, 4);

  return (
    <>
      <Hero />

      {/* Prayer times — the day's most immediate info, floating over the hero border */}
      {today && prayerEntries ? (
        <section className="relative z-10 mx-auto -mt-10 max-w-5xl px-4 sm:px-6 md:-mt-12">
          <div className="md:mx-8">
            <PrayerTimes
              dateLabel={formatDateKey(today.date)}
              hijri={today.hijri}
              prayers={prayerEntries}
            />
          </div>
        </section>
      ) : null}

      {/* Live stats */}
      <section className="mx-auto max-w-5xl px-4 pt-8 sm:px-6 md:pt-10">
        <FadeIn>
          <div className="grid grid-cols-3 divide-x divide-border/60 rounded-2xl border border-border/60 bg-card shadow-sm md:mx-12">
            <StatCounter value={menu.totalItems} label="Halal items today" />
            <StatCounter value={menu.restaurants.length} label="Campus spots" />
            <StatCounter value={upcoming.length} label="Upcoming events" />
          </div>
        </FadeIn>
      </section>

      {/* Previews */}
      <section className="mx-auto grid max-w-5xl gap-6 px-4 py-14 sm:px-6 md:grid-cols-2 md:py-16">
        <FadeIn>
          <Card className="h-full gap-4 overflow-hidden">
            <CardContent className="flex h-full flex-col gap-4 px-5">
              <div className="flex items-center gap-3">
                <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <UtensilsCrossed className="size-5" />
                </span>
                <div>
                  <h2 className="font-semibold tracking-tight">Halal food, live</h2>
                  <p className="text-xs text-muted-foreground">
                    Scraped from NetNutrition twice a day
                  </p>
                </div>
              </div>

              <Stagger className="space-y-2" staggerDelay={0.06}>
                {topRestaurants.map((r) => (
                  <StaggerItem key={r.name}>
                    <div className="flex items-center justify-between rounded-xl border border-border/60 bg-background px-3.5 py-2.5 text-sm">
                      <span className="font-medium">{r.name}</span>
                      <Badge variant="secondary" className="rounded-full tabular-nums">
                        {r.itemCount} item{r.itemCount === 1 ? "" : "s"}
                      </Badge>
                    </div>
                  </StaggerItem>
                ))}
              </Stagger>

              <Link
                href="/food"
                className="group mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary"
              >
                See everything on the menu
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </CardContent>
          </Card>
        </FadeIn>

        <FadeIn delay={0.1}>
          <Card className="h-full gap-4 overflow-hidden">
            <CardContent className="flex h-full flex-col gap-4 px-5">
              <div className="flex items-center gap-3">
                <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <CalendarDays className="size-5" />
                </span>
                <div>
                  <h2 className="font-semibold tracking-tight">Coming up</h2>
                  <p className="text-xs text-muted-foreground">
                    Live from DukeGroups — six Muslim Life communities
                  </p>
                </div>
              </div>

              {nextEvents.length > 0 ? (
                <Stagger className="space-y-2" staggerDelay={0.06}>
                  {nextEvents.map((e) => (
                    <StaggerItem key={e.id}>
                      <div className="space-y-1 rounded-xl border border-border/60 bg-background px-3.5 py-2.5">
                        <p className="text-sm font-medium leading-snug">{e.title}</p>
                        <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                          <span>
                            {etDayHeading(e.start)} · {etTime(e.start)}
                          </span>
                          {e.location && (
                            <span className="flex items-center gap-1">
                              <MapPin className="size-3" />
                              {e.location}
                            </span>
                          )}
                        </p>
                      </div>
                    </StaggerItem>
                  ))}
                </Stagger>
              ) : (
                <p className="rounded-xl border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
                  No upcoming events posted yet — check back soon.
                </p>
              )}

              <Link
                href="/events"
                className="group mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary"
              >
                Open the full calendar
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </CardContent>
          </Card>
        </FadeIn>
      </section>

      {/* PDF continuity */}
      <section className="border-t border-border/60 bg-muted/40">
        <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
          <FadeIn className="flex flex-col items-center gap-4 text-center">
            <FileText className="size-6 text-muted-foreground" />
            <div>
              <h2 className="font-semibold tracking-tight">Prefer the classic PDFs?</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                The original auto-generated documents are still updated twice daily.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-3 text-sm font-medium">
              <a
                href="https://github.com/Naimy441/duke_halal/raw/main/docs/outputs/halal_menus.pdf"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full border bg-card px-4 py-2 transition-colors hover:border-primary/40"
              >
                Halal menus PDF
              </a>
              <a
                href="https://github.com/Naimy441/duke_halal/raw/main/docs/outputs/muslim_calendar.pdf"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full border bg-card px-4 py-2 transition-colors hover:border-primary/40"
              >
                Events calendar PDF
              </a>
            </div>
          </FadeIn>
        </div>
      </section>
    </>
  );
}
