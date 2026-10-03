#!/usr/bin/env python3
"""Accumulate NetNutrition labels into a persistent per-restaurant library.

NetNutrition only shows the menus scheduled for the current day, so a single
crawl is never the full picture (at night most units return no items at all).
This script merges each crawl into ``nutriuni/nutrition_library/<unit>.json``,
keeping every item ever seen with its ``first_seen``/``last_seen`` dates, so
the Nutriuni build can match Mobile Order items against everything NetNutrition
has published for that restaurant.

Rows with physically impossible values (e.g. 3,680 kcal in a "4 oz ladle") are
kept in the file for transparency but flagged ``"valid": false`` so they are
never served.

    python nutriuni/update_nutrition_library.py --input outputs/netnutrition-direct.json
    python nutriuni/update_nutrition_library.py --seed-legacy outputs/nutri_menus.json
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY_DIR = ROOT / "nutriuni" / "nutrition_library"

# NetNutrition label name -> compact key used downstream.
NUTRIENT_KEYS = {
    "Total Fat": "fat",
    "Saturated Fat": "saturated_fat",
    "Trans Fat": "trans_fat",
    "Cholesterol": "cholesterol",
    "Sodium": "sodium",
    "Total Carbohydrate": "carbs",
    "Dietary Fiber": "fiber",
    "Total Sugars": "sugar",
    "Added Sugars": "added_sugar",
    "Protein": "protein",
    "Calcium": "calcium",
    "Iron": "iron",
    "Potas.": "potassium",
    "Potassium": "potassium",
}

MAX_CALORIES = 2500
MAX_GRAMS = 1500


def slug(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "unknown"


def key_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(re.findall(r"[a-z0-9.]+", text.lower()))


def entry_key(name: str, serving: str | None) -> str:
    return f"{key_text(name)}|{key_text(serving)}"


def serving_grams(serving: str | None) -> float | None:
    match = re.search(r"\((\d+(?:\.\d+)?)\s*g\)", serving or "")
    return float(match.group(1)) if match else None


def validate(entry: dict[str, Any]) -> str | None:
    """Return why an entry is unusable, or None when it looks plausible."""

    calories = entry.get("calories")
    if calories is None:
        return "missing calories"
    grams = serving_grams(entry.get("serving_size"))
    if calories > MAX_CALORIES:
        return f"{calories} kcal exceeds {MAX_CALORIES}"
    if grams is not None and grams > MAX_GRAMS:
        return f"{grams:g} g serving exceeds {MAX_GRAMS}"
    if grams is not None and grams > 0 and calories / grams > 9.5:
        return f"{calories} kcal in {grams:g} g is denser than pure fat"
    if grams == 0 and calories == 0:
        return "0 g / 0 kcal placeholder label"
    nutrients = entry.get("nutrients") or {}
    macro_kcal = 4 * (nutrients.get("protein") or 0) + 4 * (nutrients.get("carbs") or 0) + 9 * (nutrients.get("fat") or 0)
    if macro_kcal and abs(macro_kcal - calories) > max(150, 0.5 * max(calories, macro_kcal)):
        return f"macros imply {macro_kcal:.0f} kcal but label says {calories}"
    return None


def ingredients_of(label: dict[str, Any]) -> dict[str, str]:
    """The label's ingredient statement, when NetNutrition publishes one."""

    text = " ".join(str(label.get("ingredients") or "").split())
    return {"ingredients": text} if text else {}


def from_direct_item(item: dict[str, Any]) -> dict[str, Any] | None:
    label = item.get("nutrition")
    if not label:
        return None
    nutrients = {}
    for label_name, key in NUTRIENT_KEYS.items():
        value = ((label.get("nutrients") or {}).get(label_name) or {}).get("amount", {}).get("value")
        if value is not None:
            nutrients[key] = value
    return {
        "name": item["name"],
        "category": item.get("category"),
        "serving_size": label.get("serving_size") or item.get("serving_size"),
        "calories": label.get("calories"),
        "nutrients": nutrients,
        "halal": bool(item.get("halal")),
        "allergens": [a for a in item.get("allergens") or [] if a.lower() != "halal"],
        **ingredients_of(label),
    }


def from_legacy_meal(meal: dict[str, Any], category: str | None) -> dict[str, Any] | None:
    label = meal.get("nutrition")
    if not label:
        return None
    try:
        calories = int(float(label.get("calories")))
    except (TypeError, ValueError):
        calories = None
    nutrients = {}
    facts = {**(label.get("secondary_nutrients") or {}), **(label.get("nutrition_facts") or {})}
    for label_name, key in NUTRIENT_KEYS.items():
        value = (facts.get(label_name) or {}).get("amount")
        if value is not None:
            nutrients[key] = value
    return {
        "name": meal["name"],
        "category": None if category in (None, "None") else category,
        "serving_size": (label.get("serving_info") or {}).get("serving_size"),
        "calories": calories,
        "nutrients": nutrients,
        "halal": bool(meal.get("is_halal")),
        "allergens": [],
        **ingredients_of(label),
    }


def load_library(directory: Path, unit: str) -> dict[str, Any]:
    path = directory / f"{slug(unit)}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"unit": unit, "updated_at": None, "items": {}}


def save_library(directory: Path, library: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    library["items"] = dict(sorted(library["items"].items()))
    path = directory / f"{slug(library['unit'])}.json"
    path.write_text(json.dumps(library, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def merge(library: dict[str, Any], entry: dict[str, Any], seen: str, source: str) -> str:
    key = entry_key(entry["name"], entry["serving_size"])
    current = library["items"].get(key)
    problem = validate(entry)
    record = {
        **entry,
        "valid": problem is None,
        **({"invalid_reason": problem} if problem else {}),
        "source": source,
        "first_seen": seen,
        "last_seen": seen,
    }
    if current is None:
        library["items"][key] = record
        return "added"
    if current["last_seen"] > seen:
        # An older snapshot (e.g. the legacy seed) never overwrites newer data.
        current["first_seen"] = min(current["first_seen"], seen)
        return "kept"
    record["first_seen"] = min(current["first_seen"], seen)
    library["items"][key] = record
    return "updated"


def update_from_direct(path: Path, directory: Path, seen: str) -> None:
    crawl = json.loads(path.read_text(encoding="utf-8"))
    for unit in crawl.get("units", []):
        library = load_library(directory, unit["name"])
        counts: dict[str, int] = {}
        for menu in unit.get("menus", []):
            for item in menu.get("items", []):
                entry = from_direct_item(item)
                if entry:
                    result = merge(library, entry, seen, "netnutrition")
                    counts[result] = counts.get(result, 0) + 1
        if counts or library["items"]:
            library["updated_at"] = seen
            save_library(directory, library)
        print(f"{unit['name']}: {counts or 'no items today'} (library size {len(library['items'])})")


def seed_from_legacy(path: Path, directory: Path) -> None:
    legacy = json.loads(path.read_text(encoding="utf-8"))
    seen = str(legacy.get("timestamp", ""))[:10] or "2025-09-03"
    for restaurant in legacy.get("restaurants", []):
        library = load_library(directory, restaurant["name"])
        counts: dict[str, int] = {}
        for category in restaurant.get("categories", []):
            for meal in category.get("meals", []):
                entry = from_legacy_meal(meal, category.get("name"))
                if entry:
                    result = merge(library, entry, seen, "netnutrition-archive")
                    counts[result] = counts.get(result, 0) + 1
        library["updated_at"] = max(library.get("updated_at") or "", seen)
        save_library(directory, library)
        print(f"{restaurant['name']}: {counts} (library size {len(library['items'])})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, help="netnutrition_client.py output to merge")
    parser.add_argument("--seed-legacy", type=Path, help="Legacy nutri_menus.json snapshot to merge")
    parser.add_argument("--library-dir", type=Path, default=DEFAULT_LIBRARY_DIR)
    parser.add_argument("--date", help="Override the observation date (YYYY-MM-DD)")
    args = parser.parse_args()
    if not args.input and not args.seed_legacy:
        parser.error("pass --input and/or --seed-legacy")
    seen = args.date or datetime.now(timezone.utc).date().isoformat()
    date.fromisoformat(seen)
    if args.seed_legacy:
        seed_from_legacy(args.seed_legacy, args.library_dir)
    if args.input:
        update_from_direct(args.input, args.library_dir, seen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
