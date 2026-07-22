"use client";

import { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

/** True after client mount; use to defer wall-clock-dependent UI (avoids hydration mismatch on ISR pages). */
export function useMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
}
