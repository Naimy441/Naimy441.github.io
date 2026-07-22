"use client";

import { useSyncExternalStore } from "react";

const MINUTE = 60_000;

function subscribe(onChange: () => void) {
  const id = setInterval(onChange, 10_000);
  return () => clearInterval(id);
}

// Quantized to the minute so the snapshot stays stable between ticks
const getSnapshot = () => Math.floor(Date.now() / MINUTE) * MINUTE;
const getServerSnapshot = () => null;

/** Current time (ms, minute precision); null on the server / during hydration. */
export function useNowMinute(): number | null {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
