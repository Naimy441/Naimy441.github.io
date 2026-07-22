"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NutritionInfo } from "@/lib/types";

// Nutrients that render bold + flush-left on an FDA-style label
const MAJOR = new Set([
  "Total Fat",
  "Cholesterol",
  "Sodium",
  "Total Carbohydrate",
  "Total Carbohydrates",
  "Protein",
]);

export function NutritionLabel({ info }: { info: NutritionInfo }) {
  const [showIngredients, setShowIngredients] = useState(false);
  const facts = Object.entries(info.facts);
  const secondary = Object.entries(info.secondary);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border-2 border-foreground/80 p-4 font-sans">
        <p className="text-xl font-extrabold leading-none tracking-tight">
          Nutrition Facts
        </p>
        {info.servingSize && (
          <p className="mt-1.5 text-sm text-muted-foreground">
            Serving size <span className="font-medium text-foreground">{info.servingSize}</span>
          </p>
        )}

        <div className="my-2 h-2 rounded bg-foreground/90" />

        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs font-semibold">Amount per serving</p>
            <p className="text-2xl font-extrabold leading-tight">Calories</p>
          </div>
          <p className="text-4xl font-extrabold tabular-nums">{info.calories ?? "—"}</p>
        </div>

        <div className="my-2 h-1 rounded bg-foreground/90" />
        <p className="text-right text-[11px] font-semibold">% Daily Value*</p>

        <ul className="divide-y divide-border text-sm">
          {facts.map(([name, f]) => (
            <li
              key={name}
              className={cn(
                "flex items-baseline justify-between gap-2 py-1.5",
                !MAJOR.has(name) && "pl-4"
              )}
            >
              <span className={cn(MAJOR.has(name) ? "font-bold" : "text-foreground/80")}>
                {name}{" "}
                {f.amount !== null && (
                  <span className="font-normal text-muted-foreground">
                    {f.amount}
                    {f.unit ?? ""}
                  </span>
                )}
              </span>
              {f.daily_value_percent !== null && (
                <span className="font-bold tabular-nums">{f.daily_value_percent}%</span>
              )}
            </li>
          ))}
        </ul>

        {secondary.length > 0 && (
          <>
            <div className="my-2 h-1 rounded bg-foreground/90" />
            <ul className="grid grid-cols-2 gap-x-4 text-sm">
              {secondary.map(([name, f]) => (
                <li key={name} className="flex items-baseline justify-between gap-2 py-1">
                  <span className="text-foreground/80">
                    {name}{" "}
                    {f.amount !== null && (
                      <span className="text-muted-foreground">
                        {f.amount}
                        {f.unit ?? ""}
                      </span>
                    )}
                  </span>
                  {f.daily_value_percent !== null && (
                    <span className="font-semibold tabular-nums">
                      {f.daily_value_percent}%
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}

        <p className="mt-3 border-t pt-2 text-[11px] leading-snug text-muted-foreground">
          * The % Daily Value tells you how much a nutrient in a serving contributes to
          a daily diet. 2,000 calories a day is used for general nutrition advice.
        </p>
      </div>

      {info.ingredients && (
        <div className="rounded-xl border bg-muted/40">
          <button
            type="button"
            onClick={() => setShowIngredients((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold"
          >
            Ingredients
            <ChevronDown
              className={cn(
                "size-4 text-muted-foreground transition-transform",
                showIngredients && "rotate-180"
              )}
            />
          </button>
          {showIngredients && (
            <p className="px-4 pb-4 text-xs leading-relaxed text-muted-foreground">
              {info.ingredients}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
