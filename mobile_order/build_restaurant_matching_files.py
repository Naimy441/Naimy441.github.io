#!/usr/bin/env python3
"""Build a names-only dataset for comparing Mobile Order and nutrition menus."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MOBILE_FILE = ROOT / "outputs" / "mobile_order" / "all_restaurant_menus.json"
DEFAULT_NUTRITION_DIR = ROOT / "outputs" / "restaurants"
DEFAULT_RESTAURANT_DIR = ROOT / "outputs" / "mobile_order" / "restaurant_matching"

NUTRITION_RESTAURANT_ALIASES = {
    "Beyu Blue": ["Beyu Blue Coffee"],
    "Farmstead  &  Sprout Sandwiches": ["The Farmstead", "Sprout"],
    "Ginger & Soy": ["Ginger + Soy"],
    "JBs Roast & Chops": ["J.B.'s Roast & Chops"],
    "Pitchfork's": ["The Pitchfork"],
    "Saladelia Perkins": ["Saladalia @ The Perk"],
    "Saladelia Sanford": ["Sanford Deli"],
    "Tandoor": ["Tandoor Indian Cuisine"],
    "The Devil's Krafthouse": ["The Devils Krafthouse"],
    "Trinity": ["Trinity Cafe"],
}


def slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "unknown"


def unique_id(prefix: str, *parts: object, used: set[str]) -> str:
    base = ":".join([prefix, *(slug(part) for part in parts)])
    candidate = base
    number = 2
    while candidate in used:
        candidate = f"{base}-{number}"
        number += 1
    used.add(candidate)
    return candidate


def normalized_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.findall(r"[a-z0-9]+", text.replace("&", " and ")))


def mobile_names(data: dict) -> list[dict]:
    restaurants = []
    used_ids: set[str] = set()
    for restaurant in data.get("restaurants", []):
        restaurant_prefix = f"mobile:{slug(restaurant.get('restaurant'))}"
        dishes = []
        for section in restaurant.get("sections", []):
            for item in section.get("items", []):
                dish_id = unique_id(
                    restaurant_prefix,
                    section.get("name"),
                    item.get("name"),
                    used=used_ids,
                )
                options = [
                    {
                        "id": unique_id(
                            dish_id, "option", option.get("name"), used=used_ids
                        ),
                        "name": option.get("name", ""),
                        "values": [
                            {
                                "id": unique_id(
                                    dish_id,
                                    "value",
                                    option.get("name"),
                                    value.get("name"),
                                    used=used_ids,
                                ),
                                "name": value.get("name", ""),
                            }
                            for value in option.get("values", [])
                            if value.get("name", "")
                        ],
                    }
                    for option in item.get("options", [])
                    if option.get("name", "")
                ]
                dishes.append(
                    {
                        "id": dish_id,
                        "name": item.get("name", ""),
                        "section": section.get("name", ""),
                        "options": options,
                    }
                )
        restaurants.append(
            {
                "restaurant": restaurant.get("restaurant", ""),
                "dishes": dishes,
            }
        )
    return restaurants


def nutrition_names(data: dict) -> list[dict]:
    restaurants = []
    used_ids: set[str] = set()
    for restaurant in data.get("restaurants", []):
        restaurant_prefix = f"nutrition:{slug(restaurant.get('name'))}"
        dishes = []
        for category in restaurant.get("categories", []):
            for meal in category.get("meals", []):
                dishes.append(
                    {
                        "id": unique_id(
                            restaurant_prefix,
                            category.get("name"),
                            meal.get("name"),
                            used=used_ids,
                        ),
                        "name": meal.get("name", ""),
                        "category": category.get("name", ""),
                        "options": [],
                    }
                )
        restaurants.append(
            {
                "restaurant": restaurant.get("name", ""),
                "dishes": dishes,
            }
        )
    return restaurants


def load_nutrition_data(directory: Path) -> tuple[dict, dict[str, str]]:
    restaurants = []
    filenames = {}
    for path in sorted(directory.glob("*.json")):
        if path.name in {"index.json", "summary_stats.json"}:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("name") and isinstance(payload.get("categories"), list):
            restaurants.append(payload)
            filenames[normalized_name(payload["name"])] = path.name
    return {"restaurants": restaurants}, filenames


def write_restaurant_files(
    mobile_restaurants: list[dict],
    nutrition_restaurants: list[dict],
    nutrition_filenames: dict[str, str],
    output_dir: Path,
) -> None:
    nutrition_by_name = {
        normalized_name(restaurant["restaurant"]): restaurant
        for restaurant in nutrition_restaurants
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_file in output_dir.glob("*.json"):
        old_file.unlink()
    for mobile in mobile_restaurants:
        source_names = NUTRITION_RESTAURANT_ALIASES.get(
            mobile["restaurant"], [mobile["restaurant"]]
        )
        nutrition_matches = []
        for source_name in source_names:
            source = nutrition_by_name.get(normalized_name(source_name))
            if source is not None and source not in nutrition_matches:
                nutrition_matches.append(source)
        if nutrition_matches:
            method = "alias" if mobile["restaurant"] in NUTRITION_RESTAURANT_ALIASES else "normalized_name"
        else:
            method = "unmatched"
        output = {
            "restaurant_match": {
                "mobile_order_name": mobile["restaurant"],
                "nutrition_names": [
                    source["restaurant"] for source in nutrition_matches
                ],
                "method": method,
            },
            "mobile_order": mobile,
            "nutrition": nutrition_matches,
        }
        filename = None
        if len(nutrition_matches) == 1:
            filename = nutrition_filenames.get(
                normalized_name(nutrition_matches[0]["restaurant"])
            )
        path = output_dir / (filename or f"{slug(mobile['restaurant'])}.json")
        path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mobile-file", type=Path, default=DEFAULT_MOBILE_FILE)
    parser.add_argument("--nutrition-dir", type=Path, default=DEFAULT_NUTRITION_DIR)
    parser.add_argument("--restaurant-dir", type=Path, default=DEFAULT_RESTAURANT_DIR)
    args = parser.parse_args()

    mobile = json.loads(args.mobile_file.read_text(encoding="utf-8"))
    nutrition, nutrition_filenames = load_nutrition_data(args.nutrition_dir)
    mobile_restaurants = mobile_names(mobile)
    nutrition_restaurants = nutrition_names(nutrition)
    print(f"Mobile Order restaurants: {len(mobile_restaurants)}")
    print(f"Nutrition restaurants: {len(nutrition_restaurants)}")
    write_restaurant_files(
        mobile_restaurants,
        nutrition_restaurants,
        nutrition_filenames,
        args.restaurant_dir,
    )
    print(f"Wrote restaurant matching files to {args.restaurant_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
