"use client";

import { useEffect, useRef } from "react";
import { animate, useInView } from "motion/react";

export function StatCounter({ value, label }: { value: number; label: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });

  useEffect(() => {
    if (!inView || !ref.current) return;
    const controls = animate(0, value, {
      duration: 1.2,
      ease: [0.21, 0.47, 0.32, 0.98],
      onUpdate: (v) => {
        if (ref.current) ref.current.textContent = Math.round(v).toString();
      },
    });
    return () => controls.stop();
  }, [inView, value]);

  return (
    <div className="flex flex-col items-center gap-0.5 py-4 text-center md:py-5">
      <span ref={ref} className="text-2xl font-semibold tabular-nums text-primary md:text-3xl">
        0
      </span>
      <span className="px-1 text-[11px] font-medium leading-tight text-muted-foreground md:text-sm">
        {label}
      </span>
    </div>
  );
}
