"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, CalendarDays, UtensilsCrossed } from "lucide-react";
import { Button } from "@/components/ui/button";

const ease = [0.21, 0.47, 0.32, 0.98] as const;

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border/60">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-background/40 via-background/70 to-background" />
      <div className="relative mx-auto flex max-w-5xl flex-col items-center px-4 pb-16 pt-14 text-center sm:px-6 md:pb-24 md:pt-24">
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease }}
          className="mb-4 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-medium text-primary"
        >
          السلام عليكم · Welcome
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.08, ease }}
          className="max-w-3xl text-balance text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl md:text-6xl"
        >
          Islam at Duke,{" "}
          <span className="font-display italic text-primary">made simple</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.16, ease }}
          className="mt-5 max-w-xl text-balance text-base leading-relaxed text-muted-foreground md:text-lg"
        >
          Daily prayer times, every halal option on campus, and a live calendar
          of Muslim Life events — all in one place.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.24, ease }}
          className="mt-8 flex w-full flex-col gap-3 sm:w-auto sm:flex-row"
        >
          <Button asChild size="lg" className="h-12 rounded-full px-7 text-[15px]">
            <Link href="/food">
              <UtensilsCrossed className="size-4.5" />
              Browse halal food
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="h-12 rounded-full bg-card px-7 text-[15px]"
          >
            <Link href="/events">
              <CalendarDays className="size-4.5" />
              View events
            </Link>
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
