"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, CalendarDays, UtensilsCrossed } from "lucide-react";
import { Button } from "@/components/ui/button";

const ease = [0.21, 0.47, 0.32, 0.98] as const;

export function Hero() {
  return (
    <section className="border-b border-border/60">
      <div className="mx-auto flex max-w-5xl flex-col items-center px-4 pb-20 pt-6 text-center sm:px-6 md:pb-28 md:pt-10">
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease }}
          className="max-w-2xl text-balance text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl md:text-6xl"
        >
          Discover{" "}
          <span className="font-display italic text-primary">prayer</span>
          {", "}
          <span className="font-display italic text-primary">food</span>
          {", and "}
          <span className="font-display italic text-primary">events</span>
          {" at "}
          <span className="font-display italic text-primary">Duke</span>
        </motion.h1>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.12, ease }}
          className="mt-7 flex w-full flex-col gap-2.5 sm:w-auto sm:flex-row"
        >
          <Button asChild size="lg" className="h-11 rounded-full px-6 text-[15px]">
            <Link href="/food">
              <UtensilsCrossed className="size-4" />
              Today&apos;s menu
              <ArrowRight className="size-4 transition-transform group-hover/button:translate-x-0.5" />
            </Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="h-11 rounded-full bg-card/80 px-6 text-[15px]"
          >
            <Link href="/events">
              <CalendarDays className="size-4" />
              Events
            </Link>
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
