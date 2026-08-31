import Link from "next/link";
import { ArrowRight, CalendarDays, MapPin, UtensilsCrossed } from "lucide-react";
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

      <section className="mx-auto max-w-5xl px-4 pt-6 sm:px-6 md:pt-8">
        <FadeIn>
          <div className="grid grid-cols-3 divide-x divide-border/50 rounded-2xl border border-border/50 bg-card md:mx-12">
            <StatCounter value={menu.totalItems} label="Halal items today" />
            <StatCounter value={menu.restaurants.length} label="Spots serving" />
            <StatCounter value={upcoming.length} label="Upcoming events" />
          </div>
        </FadeIn>
      </section>

      <section className="mx-auto grid max-w-5xl gap-5 px-4 py-12 sm:px-6 md:grid-cols-2 md:py-14">
        <FadeIn>
          <Card className="h-full gap-4 overflow-hidden">
            <CardContent className="flex h-full flex-col gap-4 px-5">
              <div className="flex items-center gap-3">
                <span className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <UtensilsCrossed className="size-4.5" />
                </span>
                <div>
                  <h2 className="font-semibold tracking-tight">On the menu</h2>
                  <p className="text-xs text-muted-foreground">Updated twice a day</p>
                </div>
              </div>

              {topRestaurants.length > 0 ? (
                <Stagger className="space-y-2" staggerDelay={0.05}>
                  {topRestaurants.map((r) => (
                    <StaggerItem key={r.name}>
                      <Link
                        href="/food"
                        className="flex items-center justify-between rounded-xl border border-border/60 bg-background px-3.5 py-2.5 text-sm transition-colors hover:border-primary/30 hover:bg-accent/40"
                      >
                        <span className="font-medium">{r.name}</span>
                        <Badge variant="secondary" className="rounded-full tabular-nums">
                          {r.itemCount}
                        </Badge>
                      </Link>
                    </StaggerItem>
                  ))}
                </Stagger>
              ) : (
                <p className="rounded-xl border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
                  Today&apos;s menu isn&apos;t up yet. Check back shortly.
                </p>
              )}

              <Link
                href="/food"
                className="group mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary"
              >
                See the full menu
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </CardContent>
          </Card>
        </FadeIn>

        <FadeIn delay={0.08}>
          <Card className="h-full gap-4 overflow-hidden">
            <CardContent className="flex h-full flex-col gap-4 px-5">
              <div className="flex items-center gap-3">
                <span className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <CalendarDays className="size-4.5" />
                </span>
                <div>
                  <h2 className="font-semibold tracking-tight">Coming up</h2>
                  <p className="text-xs text-muted-foreground">Live from DukeGroups</p>
                </div>
              </div>

              {nextEvents.length > 0 ? (
                <Stagger className="space-y-2" staggerDelay={0.05}>
                  {nextEvents.map((e) => (
                    <StaggerItem key={e.id}>
                      <Link
                        href="/events"
                        className="block space-y-1 rounded-xl border border-border/60 bg-background px-3.5 py-2.5 transition-colors hover:border-primary/30 hover:bg-accent/40"
                      >
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
                      </Link>
                    </StaggerItem>
                  ))}
                </Stagger>
              ) : (
                <p className="rounded-xl border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
                  No upcoming events posted yet.
                </p>
              )}

              <Link
                href="/events"
                className="group mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary"
              >
                Open the calendar
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </CardContent>
          </Card>
        </FadeIn>
      </section>
    </>
  );
}
