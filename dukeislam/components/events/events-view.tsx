"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  CalendarDays,
  CalendarX2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  MapPin,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  dateKeyOf,
  etDateKey,
  etDayHeading,
  etTime,
  etYear,
  monthGrid,
  monthLabel,
} from "@/lib/dates";
import type { MuslimEvent } from "@/lib/types";
import type { EventsPayload } from "@/lib/events";
import { Stagger, StaggerItem } from "@/components/motion-primitives";

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

interface Props {
  payload: EventsPayload;
}

export function EventsView({ payload }: Props) {
  // The upcoming/past split and "now" are computed on the server when the page
  // regenerates (every 30 min), which keeps server and client HTML identical.
  const { events, upcoming, past, asOf } = payload;

  if (events.length === 0) {
    return (
      <Card className="py-16 text-center">
        <CardContent className="space-y-2">
          <CalendarX2 className="mx-auto size-8 text-muted-foreground" />
          <p className="font-medium">No events found</p>
          <p className="text-sm text-muted-foreground">
            The DukeGroups feed didn&apos;t return any events right now. Check back soon.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Tabs defaultValue="list">
      <TabsList className="mb-4">
        <TabsTrigger value="list">Upcoming</TabsTrigger>
        <TabsTrigger value="calendar">Calendar</TabsTrigger>
      </TabsList>

      <TabsContent value="list">
        <UpcomingList upcoming={upcoming} past={past} />
      </TabsContent>

      <TabsContent value="calendar">
        <MonthCalendar events={events} now={asOf} />
      </TabsContent>
    </Tabs>
  );
}

function UpcomingList({ upcoming, past }: { upcoming: MuslimEvent[]; past: MuslimEvent[] }) {
  const [showPast, setShowPast] = useState(false);

  const grouped = useMemo(() => {
    const map = new Map<string, MuslimEvent[]>();
    for (const e of upcoming) {
      const key = etDateKey(e.start);
      (map.get(key) ?? map.set(key, []).get(key)!).push(e);
    }
    return [...map.entries()];
  }, [upcoming]);

  return (
    <div className="space-y-8">
      {grouped.length === 0 && (
        <Card className="py-12 text-center">
          <CardContent className="space-y-1.5">
            <CalendarDays className="mx-auto size-7 text-muted-foreground" />
            <p className="font-medium">Nothing scheduled right now</p>
            <p className="text-sm text-muted-foreground">
              New events land here as soon as groups post them on DukeGroups.
            </p>
          </CardContent>
        </Card>
      )}

      {grouped.map(([key, dayEvents]) => (
        <section key={key}>
          <h2 className="mb-3 flex items-baseline gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            {etDayHeading(dayEvents[0].start)}
            <span className="text-xs font-normal normal-case tracking-normal">
              {etYear(dayEvents[0].start)}
            </span>
          </h2>
          <Stagger className="space-y-3" staggerDelay={0.05}>
            {dayEvents.map((e) => (
              <StaggerItem key={e.id}>
                <EventCard event={e} />
              </StaggerItem>
            ))}
          </Stagger>
        </section>
      ))}

      {past.length > 0 && (
        <div className="border-t pt-6">
          <button
            type="button"
            onClick={() => setShowPast((v) => !v)}
            className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <ChevronDown
              className={cn("size-4 transition-transform", showPast && "rotate-180")}
            />
            {showPast ? "Hide" : "Show"} {past.length} past event{past.length === 1 ? "" : "s"}
          </button>
          <AnimatePresence initial={false}>
            {showPast && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <div className="space-y-3 pt-4 opacity-70">
                  {past.map((e) => (
                    <EventCard key={e.id} event={e} muted />
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

function EventCard({ event, muted = false }: { event: MuslimEvent; muted?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const hasLongDescription = event.description.length > 180;

  return (
    <Card className="gap-3 overflow-hidden py-4 transition-shadow hover:shadow-md">
      <CardContent className="space-y-2.5 px-4 sm:px-5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <Badge variant="secondary" className="rounded-full font-semibold tabular-nums">
            {etTime(event.start)} – {etTime(event.end)}
          </Badge>
          {event.location && (
            <span className="flex min-w-0 items-center gap-1 text-xs text-muted-foreground">
              <MapPin className="size-3.5 shrink-0" />
              <span className="truncate">{event.location}</span>
            </span>
          )}
        </div>

        <h3 className="text-base font-semibold leading-snug tracking-tight sm:text-lg">
          {event.title}
        </h3>

        {event.description && (
          <div>
            <p
              className={cn(
                "whitespace-pre-line text-sm leading-relaxed text-muted-foreground",
                !expanded && hasLongDescription && "line-clamp-3"
              )}
            >
              {event.description}
            </p>
            {hasLongDescription && (
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="mt-1 text-xs font-medium text-primary hover:underline"
              >
                {expanded ? "Show less" : "Read more"}
              </button>
            )}
          </div>
        )}

        {event.rsvpUrl && !muted && (
          <Button asChild size="sm" className="rounded-full">
            <a href={event.rsvpUrl} target="_blank" rel="noopener noreferrer">
              RSVP
              <ExternalLink className="size-3.5" />
            </a>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function MonthCalendar({ events, now }: { events: MuslimEvent[]; now: number }) {
  const eventsByDay = useMemo(() => {
    const map = new Map<string, MuslimEvent[]>();
    for (const e of events) {
      const key = etDateKey(e.start);
      (map.get(key) ?? map.set(key, []).get(key)!).push(e);
    }
    return map;
  }, [events]);

  const todayKey = etDateKey(now);

  // Start on the month of the first event that hasn't ended, else today's month
  const initialKey =
    events.find((e) => new Date(e.end).getTime() >= now)?.start ?? new Date(now).toISOString();
  const initial = etDateKey(initialKey);
  const [year, setYear] = useState(() => parseInt(initial.slice(0, 4), 10));
  const [month, setMonth] = useState(() => parseInt(initial.slice(5, 7), 10));
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [direction, setDirection] = useState(0);

  const cells = monthGrid(year, month);

  const navigate = (delta: number) => {
    setDirection(delta);
    setSelectedDay(null);
    let m = month + delta;
    let y = year;
    if (m < 1) {
      m = 12;
      y--;
    }
    if (m > 12) {
      m = 1;
      y++;
    }
    setMonth(m);
    setYear(y);
  };

  const selectedEvents = selectedDay ? eventsByDay.get(selectedDay) ?? [] : [];

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,26rem)_1fr] lg:items-start">
      <Card className="py-4">
        <CardContent className="px-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold">{monthLabel(year, month)}</p>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => navigate(-1)}
                aria-label="Previous month"
              >
                <ChevronLeft className="size-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => navigate(1)}
                aria-label="Next month"
              >
                <ChevronRight className="size-4" />
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-7 text-center text-[11px] font-medium text-muted-foreground">
            {WEEKDAYS.map((d) => (
              <span key={d} className="py-1">
                {d}
              </span>
            ))}
          </div>

          <AnimatePresence mode="popLayout" initial={false}>
            <motion.div
              key={`${year}-${month}`}
              initial={{ opacity: 0, x: direction * 24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: direction * -24 }}
              transition={{ duration: 0.22 }}
              className="grid grid-cols-7 gap-y-1"
            >
              {cells.map((day, i) => {
                if (day === null) return <span key={`empty-${i}`} />;
                const key = dateKeyOf(year, month, day);
                const dayEvents = eventsByDay.get(key);
                const isToday = key === todayKey;
                const isSelected = key === selectedDay;
                return (
                  <button
                    key={key}
                    type="button"
                    disabled={!dayEvents}
                    onClick={() => setSelectedDay(isSelected ? null : key)}
                    className={cn(
                      "relative mx-auto flex size-9 flex-col items-center justify-center rounded-full text-sm tabular-nums transition-colors",
                      dayEvents && "font-semibold hover:bg-accent",
                      isSelected && "bg-primary text-primary-foreground hover:bg-primary",
                      !dayEvents && "text-muted-foreground/60",
                      isToday && !isSelected && "ring-1 ring-primary/50"
                    )}
                  >
                    {day}
                    {dayEvents && (
                      <span className="absolute bottom-1 flex gap-0.5">
                        {dayEvents.slice(0, 3).map((_, j) => (
                          <span
                            key={j}
                            className={cn(
                              "size-1 rounded-full",
                              isSelected ? "bg-primary-foreground" : "bg-primary"
                            )}
                          />
                        ))}
                      </span>
                    )}
                  </button>
                );
              })}
            </motion.div>
          </AnimatePresence>
        </CardContent>
      </Card>

      <div className="min-h-40">
        <AnimatePresence mode="wait">
          {selectedDay ? (
            <motion.div
              key={selectedDay}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="space-y-3"
            >
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                {selectedEvents[0]
                  ? etDayHeading(selectedEvents[0].start)
                  : selectedDay}
              </h2>
              {selectedEvents.map((e) => (
                <EventCard key={e.id} event={e} />
              ))}
            </motion.div>
          ) : (
            <motion.div
              key="hint"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex h-full min-h-40 items-center justify-center rounded-xl border border-dashed text-sm text-muted-foreground"
            >
              Select a highlighted day to see its events
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
