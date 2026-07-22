"use client";

import { useState } from "react";
import { CalendarPlus, Check, Link2, MoonStar, Sunrise } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
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
    <Card className="overflow-hidden py-0">
      <CardContent className="px-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-muted/40 px-4 py-3 sm:px-5">
          <div className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <MoonStar className="size-4" />
            </span>
            <div>
              <p className="text-sm font-semibold leading-tight">Prayer times today</p>
              <p className="text-xs text-muted-foreground">
                {dateLabel}
                {hijri ? ` · ${hijri}` : ""}
              </p>
            </div>
          </div>
          <SubscribeButtons />
        </div>

        <div className="grid grid-cols-6 divide-x divide-border/60">
          {prayers.map((p, i) => {
            const isNext = i === nextIndex;
            const isSunrise = p.kind === "sunrise";
            return (
              <div
                key={p.name}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-0.5 py-3.5 text-center transition-colors sm:py-4",
                  isNext && "bg-primary text-primary-foreground",
                  isSunrise && "bg-muted/50"
                )}
              >
                <span
                  className={cn(
                    "flex items-center gap-0.5 text-[10px] font-medium sm:text-xs",
                    isNext ? "text-primary-foreground/80" : "text-muted-foreground"
                  )}
                >
                  {isSunrise && <Sunrise className="size-3" />}
                  {p.name}
                </span>
                <span
                  className={cn(
                    "text-[12px] font-semibold tabular-nums sm:text-sm",
                    isSunrise && "font-medium text-muted-foreground"
                  )}
                >
                  {p.display}
                </span>
                {isNext && (
                  <span className="mt-0.5 rounded-full bg-primary-foreground/15 px-1.5 py-px text-[9px] font-semibold uppercase tracking-wider">
                    Next
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <p className="border-t border-border/60 px-4 py-2 text-center text-[11px] text-muted-foreground">
          ISNA calculation, Shafi Asr, for Duke&apos;s campus · Subscribe once and athan
          times stay accurate automatically
        </p>
      </CardContent>
    </Card>
  );
}

function SubscribeButtons() {
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
      // Clipboard unavailable (e.g. non-secure context); the subscribe link still works
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <Button asChild size="sm" variant="outline" className="h-8 rounded-full bg-card text-xs">
        <a href={webcalUrl}>
          <CalendarPlus className="size-3.5" />
          Subscribe
        </a>
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={copy}
        className="h-8 rounded-full px-2.5 text-xs text-muted-foreground"
        aria-label="Copy calendar link"
      >
        {copied ? <Check className="size-3.5 text-emerald-600" /> : <Link2 className="size-3.5" />}
        {copied ? "Copied" : "Copy link"}
      </Button>
    </div>
  );
}
