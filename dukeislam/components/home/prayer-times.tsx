"use client";

import { useState } from "react";
import { CalendarPlus, Check, Link2, MoonStar, Sunrise } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { cn } from "@/lib/utils";
import { useMediaQuery } from "@/hooks/use-media-query";
import { useMounted } from "@/hooks/use-mounted";
import { useNowMinute } from "@/hooks/use-now";

export interface PrayerEntry {
  name: string;
  /** "5:03 AM" (Eastern) */
  display: string;
  /** UTC ms of the athan (or sunrise) */
  utcMs: number;
  /** Sunrise is informational — never highlighted as "next" */
  kind: "prayer" | "sunrise";
}

interface Props {
  dateLabel: string;
  hijri: string | null;
  prayers: PrayerEntry[];
}

export function PrayerTimes({ dateLabel, hijri, prayers }: Props) {
  // Wall-clock dependent; null until hydration so server/client HTML match
  const now = useNowMinute();
  const nextIndex =
    now === null
      ? -1
      : prayers.findIndex((p) => p.kind === "prayer" && p.utcMs + 5 * 60_000 > now);

  return (
    <Card className="py-0 shadow-md">
      <CardContent className="space-y-4 p-4 sm:p-5">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <MoonStar className="size-4.5" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold leading-tight">Prayer times</p>
            <p className="truncate text-xs text-muted-foreground">
              {dateLabel}
              {hijri ? ` · ${hijri}` : ""}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-6 sm:gap-2">
          {prayers.map((p, i) => {
            const isNext = i === nextIndex;
            const isSunrise = p.kind === "sunrise";
            return (
              <div
                key={p.name}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-xl py-3 transition-colors sm:py-3.5",
                  isNext
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-muted/50",
                  isSunrise && "opacity-75"
                )}
              >
                <span
                  className={cn(
                    "flex items-center gap-1 text-[11px] font-medium",
                    isNext ? "text-primary-foreground/75" : "text-muted-foreground"
                  )}
                >
                  {isSunrise && <Sunrise className="size-3" />}
                  {p.name}
                </span>
                <span className="text-sm font-semibold tabular-nums">{p.display}</span>
              </div>
            );
          })}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border/50 pt-3">
          <p className="text-[11px] text-muted-foreground/70">ISNA method</p>
          <AddToCalendar />
        </div>
      </CardContent>
    </Card>
  );
}

function AddToCalendar() {
  const [open, setOpen] = useState(false);
  const isDesktop = useMediaQuery("(min-width: 768px)");

  const trigger = (
    <button
      type="button"
      onClick={() => setOpen(true)}
      className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
    >
      <CalendarPlus className="size-3.5" />
      Add to calendar
    </button>
  );

  if (isDesktop) {
    return (
      <>
        {trigger}
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent className="max-w-md gap-4 p-6">
            <DialogHeader>
              <DialogTitle>Add prayer times to your calendar</DialogTitle>
              <DialogDescription>
                Subscribe once and each day&apos;s Fajr through Isha (plus
                sunrise) will show up in your calendar and stay updated.
              </DialogDescription>
            </DialogHeader>
            <CalendarActions />
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <>
      {trigger}
      <Drawer open={open} onOpenChange={setOpen}>
        <DrawerContent>
          <DrawerHeader className="text-left">
            <DrawerTitle>Add prayer times to your calendar</DrawerTitle>
            <DrawerDescription>
              Subscribe once and each day&apos;s Fajr through Isha (plus
              sunrise) will show up in your calendar and stay updated.
            </DrawerDescription>
          </DrawerHeader>
          <div className="px-4 pb-8">
            <CalendarActions />
          </div>
        </DrawerContent>
      </Drawer>
    </>
  );
}

function CalendarActions() {
  const mounted = useMounted();
  const [copied, setCopied] = useState(false);

  const host = mounted ? window.location.host : "dukeislam.org";
  const webcalUrl = `webcal://${host}/prayers.ics`;
  const httpsUrl = `https://${host}/prayers.ics`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(httpsUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard unavailable; the subscribe link still works
    }
  };

  return (
    <div className="space-y-3">
      <Button asChild className="h-11 w-full rounded-full text-[15px]">
        <a href={webcalUrl}>
          <CalendarPlus className="size-4" />
          Open in your calendar app
        </a>
      </Button>
      <Button
        type="button"
        variant="outline"
        className="h-11 w-full rounded-full text-[15px]"
        onClick={copy}
      >
        {copied ? <Check className="size-4 text-emerald-600" /> : <Link2 className="size-4" />}
        {copied ? "Link copied" : "Copy calendar link"}
      </Button>
      <p className="text-xs leading-relaxed text-muted-foreground">
        On iPhone or Outlook, use the first button. For Google Calendar, copy
        the link, then go to Settings → Add calendar → From URL.
      </p>
    </div>
  );
}
