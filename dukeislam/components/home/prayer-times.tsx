"use client";

import { useState } from "react";
import { CalendarPlus, Check, Link2, MoonStar, Sunrise } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
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
    <Card className="py-0 shadow-md">
      <CardContent className="space-y-4 p-4 sm:p-5">
        <div className="flex items-center justify-between gap-3">
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
          <SubscribeButtons />
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

        <p className="text-right text-[11px] text-muted-foreground/80">
          ISNA
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
    <div className="flex shrink-0 items-center gap-1.5">
      <Button
        asChild
        size="sm"
        variant="outline"
        className="size-8 rounded-full bg-card p-0 text-xs sm:size-auto sm:px-3 sm:py-1.5"
      >
        <a href={webcalUrl} aria-label="Add prayer times to your calendar">
          <CalendarPlus className="size-3.5" />
          <span className="hidden sm:inline">Add to calendar</span>
        </a>
      </Button>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            size="icon"
            variant="ghost"
            onClick={copy}
            className="size-8 rounded-full text-muted-foreground"
            aria-label="Copy calendar link"
          >
            {copied ? (
              <Check className="size-3.5 text-emerald-600" />
            ) : (
              <Link2 className="size-3.5" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{copied ? "Copied!" : "Copy calendar link"}</TooltipContent>
      </Tooltip>
    </div>
  );
}
