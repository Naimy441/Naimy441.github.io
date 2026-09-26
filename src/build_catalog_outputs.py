#!/usr/bin/env python3
"""Build the repository's catalog artifacts from direct NetNutrition JSON.

The direct client is the source of truth.  This adapter preserves the existing
files consumed by the site and nutrition extraction step:

    outputs/netnutrition-direct.json -> outputs/restaurants/*.json
                                      -> outputs/halal_menus.txt
                                      -> docs/outputs/halal_menus.pdf
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import OrderedDict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


DEFAULT_INPUT = Path("outputs/netnutrition-direct.json")
DEFAULT_MENU_TEXT = Path("outputs/halal_menus.txt")
DEFAULT_PDF = Path("docs/outputs/halal_menus.pdf")
DEFAULT_RESTAURANTS_DIR = Path("outputs/restaurants")
HOURS_URL = "https://campushours.oit.duke.edu/places/dining"

# Campus Hours uses a few names that differ from NetNutrition's unit labels.
HOURS_NAME_MAP = {
    "Freeman Center for Jewish Life": "Freeman Café",
    "Ginger & Soy": "Ginger + Soy",
    "JB's Roasts and Chops": "J.B.'s Roast & Chops",
    "Red Mango Cafe": "Red Mango",
    "Saladelia Cafe at Perkins": "Saladalia @ The Perk",
    "Saladelia Cafe at Sanford": "Sanford Deli",
    "Tandoor": "Tandoor Indian Cuisine",
    "The Devil's Krafthouse": "The Devils Krafthouse",
    "Farmstead": "The Farmstead",
    "Pitchfork's": "The PitchFork",
    "Twinnie's": "Twinnie's",
    "Zweli's Cafe at Duke Divinity": "Zweli's Café at Duke Divinity",
}

SECONDARY_NUTRIENTS = {"Calcium", "Iron", "Potas.", "Potassium", "Vitamin D"}


def normalize_name(value: str) -> str:
    return " ".join((value or "").split()).casefold()


def fetch_dining_hours(*, verify: bool | str = True, timeout: float = 30.0) -> dict[str, str]:
    """Fetch today's campus hours, returning an empty map on failure."""

    try:
        response = requests.get(
            HOURS_URL,
            params={"start_date": date.today().isoformat()},
            headers={"User-Agent": "duke-halal-netnutrition-client/1.0"},
            timeout=timeout,
            verify=verify,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Warning: campus hours unavailable ({exc})")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    hours: dict[str, str] = {}
    for row in soup.find_all("div", role="row")[1:]:
        location = row.find("div", role="rowheader")
        cells = row.find_all("div", role="cell")
        if not location or not cells:
            continue
        source_name = " ".join(location.get_text(" ", strip=True).split())
        value = " ".join(cells[0].get_text(" ", strip=True).split())
        value = re.sub(r"(?<=[ap]m)(?=\d)", ", ", value)
        value = re.sub(r"(?<=[ap]m)(?=Noon|Midnight)", ", ", value)
        hours[HOURS_NAME_MAP.get(source_name, source_name)] = value
    return hours


def convert_nutrition(nutrition: dict[str, Any] | None) -> dict[str, Any] | None:
    if not nutrition:
        return None

    facts: dict[str, Any] = OrderedDict()
    secondary: dict[str, Any] = OrderedDict()
    for name, record in (nutrition.get("nutrients") or {}).items():
        amount = record.get("amount") or {}
        converted = {
            "amount": amount.get("value"),
            "unit": amount.get("unit"),
            "daily_value_percent": record.get("daily_value_percent"),
        }
        (secondary if name in SECONDARY_NUTRIENTS else facts)[name] = converted

    return {
        "item_name": nutrition.get("name"),
        "serving_info": {
            "servings_per_container": nutrition.get("servings_per_container"),
            "serving_size": nutrition.get("serving_size"),
        },
        "calories": nutrition.get("calories"),
        "nutrition_facts": facts,
        "secondary_nutrients": secondary,
        "ingredients": nutrition.get("ingredients"),
        "contains": nutrition.get("contains"),
    }


def build_catalog(source: dict[str, Any], hours: dict[str, str]) -> dict[str, Any]:
    restaurants: list[dict[str, Any]] = []
    for unit in source.get("units", []):
        name = unit.get("name") or "Unknown"
        categories: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        seen: set[tuple[str, str]] = set()

        for menu in unit.get("menus", []):
            for item in menu.get("items", []):
                # The direct run is normally --halal-only; keep this guard so a
                # mistakenly broad input cannot pollute the halal artifacts.
                if not item.get("halal"):
                    continue
                category = item.get("category") or "Uncategorized"
                item_name = item.get("name") or "Unnamed item"
                key = (category, normalize_name(item_name))
                if key in seen:
                    continue
                seen.add(key)
                categories.setdefault(category, []).append({
                    "name": item_name,
                    "is_halal": True,
                    "nutrition": convert_nutrition(item.get("nutrition")),
                })

        if not categories:
            continue
        fallback_hours = "Closed today" if str(unit.get("status", "")).casefold() == "closed" else "Hours not available"
        restaurants.append({
            "name": name,
            "hours": hours.get(name, fallback_hours),
            "categories": [
                {"name": category, "meals": meals}
                for category, meals in categories.items()
                if meals
            ],
        })

    return {
        "timestamp": datetime.now().isoformat(),
        "restaurants": restaurants,
    }


def sanitize_filename(name: str) -> str:
    filename = re.sub(r"[^\w\s-]", "", name)
    filename = re.sub(r"[\s-]+", "_", filename)
    return filename.strip("_").lower() or "unknown"


def write_restaurant_files(catalog: dict[str, Any], output_dir: Path) -> None:
    """Write the per-restaurant files consumed by extract-nutrition.mjs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now().isoformat()
    index: dict[str, Any] = {
        "created_at": created_at,
        "total_restaurants": len(catalog.get("restaurants", [])),
        "restaurants": {},
    }

    for restaurant in catalog.get("restaurants", []):
        name = restaurant.get("name", "Unknown")
        categories = restaurant.get("categories", [])
        restaurant_data = {
            "name": name,
            "hours": restaurant.get("hours", "Hours not available"),
            "categories": categories,
            "total_items": sum(len(category.get("meals", [])) for category in categories),
            "halal_items": sum(
                len([meal for meal in category.get("meals", []) if meal.get("is_halal", False)])
                for category in categories
            ),
            "created_at": created_at,
        }
        filename = f"{sanitize_filename(name)}.json"
        (output_dir / filename).write_text(
            json.dumps(restaurant_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        index["restaurants"][name] = {
            "filename": filename,
            "safe_name": sanitize_filename(name),
            "hours": restaurant_data["hours"],
            "total_items": restaurant_data["total_items"],
            "halal_items": restaurant_data["halal_items"],
            "categories_count": len(categories),
        }

    (output_dir / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    restaurants = index["restaurants"]
    summary = {
        "summary": {
            "total_restaurants": len(restaurants),
            "total_items": sum(item["total_items"] for item in restaurants.values()),
            "total_halal_items": sum(item["halal_items"] for item in restaurants.values()),
            "average_items_per_restaurant": round(
                sum(item["total_items"] for item in restaurants.values()) / len(restaurants), 1
            ) if restaurants else 0,
            "restaurants_with_halal": len(
                [item for item in restaurants.values() if item["halal_items"] > 0]
            ),
        },
        "top_restaurants_by_items": sorted(
            [(name, item["total_items"]) for name, item in restaurants.items()],
            key=lambda pair: pair[1],
            reverse=True,
        )[:10],
        "top_restaurants_by_halal": sorted(
            [(name, item["halal_items"]) for name, item in restaurants.items()],
            key=lambda pair: pair[1],
            reverse=True,
        )[:10],
        "restaurants_by_category_count": sorted(
            [(name, item["categories_count"]) for name, item in restaurants.items()],
            key=lambda pair: pair[1],
            reverse=True,
        )[:10],
    }
    (output_dir / "summary_stats.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_menu_text(catalog: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for restaurant in catalog["restaurants"]:
        lines.append(f"{restaurant['name']} - {restaurant['hours']}")
        for category in restaurant["categories"]:
            meals = category.get("meals", [])
            if not meals:
                continue
            lines.append(f"  {category['name']}:")
            for meal in meals:
                lines.append(f"    - {meal['name']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_pdf(catalog: dict[str, Any], path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title = styles["Title"]
    subtitle = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10,
        textColor=colors.HexColor("#444444"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    normal = styles["Normal"]
    header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.white,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    elements: list[Any] = [
        Paragraph(f"Halal @ Duke - {date.today().strftime('%A, %B %d, %Y')}", title),
        Spacer(1, 12),
    ]
    for restaurant in catalog["restaurants"]:
        elements.append(Paragraph(html.escape(restaurant["name"]), title))
        elements.append(Paragraph(html.escape(restaurant["hours"]), subtitle))
        for category in restaurant["categories"]:
            rows = [[Paragraph(html.escape(category["name"]), header)]]
            rows.extend([[Paragraph(html.escape(meal["name"]), normal)] for meal in category["meals"]])
            table = Table(rows, colWidths=[500])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f4f7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.extend([table, Spacer(1, 10)])

    SimpleDocTemplate(str(path), pagesize=letter).build(elements)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--menu-text", type=Path, default=DEFAULT_MENU_TEXT)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--restaurants-dir", type=Path, default=DEFAULT_RESTAURANTS_DIR)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--ca-bundle", type=Path, help="CA bundle path for the campus-hours request")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification for campus hours")
    parser.add_argument("--no-hours", action="store_true", help="Skip the campus-hours request")
    return parser


def main() -> int:
    args = _parser().parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    verify: bool | str = False if args.insecure else (str(args.ca_bundle) if args.ca_bundle else True)
    hours = {} if args.no_hours else fetch_dining_hours(verify=verify, timeout=args.timeout)
    catalog = build_catalog(source, hours)
    write_menu_text(catalog, args.menu_text)
    write_pdf(catalog, args.pdf)
    write_restaurant_files(catalog, args.restaurants_dir)
    item_count = sum(len(category["meals"]) for restaurant in catalog["restaurants"] for category in restaurant["categories"])
    print(f"Wrote {item_count} halal items across {len(catalog['restaurants'])} restaurants")
    print(f"  {args.menu_text}")
    print(f"  {args.pdf}")
    print(f"  {args.restaurants_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
