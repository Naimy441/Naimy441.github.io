#!/usr/bin/env python3
"""Direct, no-browser client for Duke NetNutrition.

The site is an ASP.NET MVC application.  Restaurants and menus are returned as
HTML fragments from form-encoded POST requests, so this client keeps one
requests.Session and follows the same endpoint sequence as the site JavaScript
without opening a browser or clicking UI elements.

Examples:

    python src/netnutrition_client.py --list-units
    python src/netnutrition_client.py --unit "Tandoor Indian Cuisine" \
        --nutrition --output outputs/tandoor-netnutrition.json
    python src/netnutrition_client.py --halal-only --nutrition \
        --output outputs/netnutrition-direct.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup, Tag
from urllib3.exceptions import InsecureRequestWarning


DEFAULT_BASE_URL = "https://netnutrition.cbord.com/nn-prod/Duke"
DEFAULT_TIMEOUT = 30.0


class NetNutritionError(RuntimeError):
    """Raised when NetNutrition returns an unexpected response."""


@dataclass(frozen=True)
class Unit:
    name: str
    unit_oid: int
    status: str | None = None


def _clean_text(value: str | None) -> str:
    return " ".join((value or "").replace("\xa0", " ").split())


def _first_int(pattern: str, value: str) -> int | None:
    match = re.search(pattern, value or "", flags=re.I)
    return int(match.group(1)) if match else None


def _parse_menu_id(link: Tag) -> int | None:
    onclick = link.get("onclick", "")
    return _first_int(r"menuListSelectMenu\(\s*(\d+)\s*\)", onclick)


def _parse_detail_id(link: Tag) -> int | None:
    element_id = link.get("id", "")
    detail_id = _first_int(r"showNutrition_(\d+)$", element_id)
    if detail_id is not None:
        return detail_id
    return _first_int(r"getItemNutritionLabel(?:OnClick)?\([^,]+,\s*(\d+)", link.get("onclick", ""))


def parse_units(html: str) -> list[Unit]:
    """Parse the restaurant cards embedded in the initial page."""

    soup = BeautifulSoup(html, "html.parser")
    units: list[Unit] = []
    seen: set[int] = set()
    for card in soup.select(".card.unit"):
        link = card.select_one("a[onclick*=unitsSelectUnit]")
        if not link:
            continue
        unit_oid = _first_int(r"unitsSelectUnit\(\s*(\d+)\s*\)", link.get("onclick", ""))
        if unit_oid is None or unit_oid in seen:
            continue
        seen.add(unit_oid)
        badge = card.select_one(".badge")
        units.append(
            Unit(
                name=_clean_text(link.get_text(" ", strip=True)),
                unit_oid=unit_oid,
                status=_clean_text(badge.get_text(" ", strip=True)) if badge else None,
            )
        )
    return units


def parse_menus(html: str) -> list[dict[str, Any]]:
    """Parse menu links from a ``menuPanel`` HTML fragment."""

    soup = BeautifulSoup(html or "", "html.parser")
    menus: list[dict[str, Any]] = []
    seen: set[int] = set()
    for link in soup.select("a.cbo_nn_menuLink"):
        menu_oid = _parse_menu_id(link)
        if menu_oid is None or menu_oid in seen:
            continue
        seen.add(menu_oid)
        menus.append({
            "menu_oid": menu_oid,
            "name": _clean_text(link.get_text(" ", strip=True)),
        })
    return menus


def _direct_link_text(link: Tag) -> str:
    # The item anchor contains the item name as a direct text node and allergen
    # icons in nested spans.  Avoid including the icon alt text in item_name.
    direct = " ".join(str(node) for node in link.find_all(string=True, recursive=False))
    return _clean_text(direct) or _clean_text(link.get_text(" ", strip=True))


def parse_items(html: str, *, halal_only: bool = False) -> list[dict[str, Any]]:
    """Parse item rows from an ``itemPanel`` HTML fragment."""

    soup = BeautifulSoup(html or "", "html.parser")
    items: list[dict[str, Any]] = []
    category: str | None = None
    for row in soup.select("tr"):
        classes = set(row.get("class", []))
        if "cbo_nn_itemGroupRow" in classes:
            category_node = row.select_one("[role=button]")
            category = _clean_text(category_node.get_text(" ", strip=True) if category_node else row.get_text(" ", strip=True))
            continue
        if not ({"cbo_nn_itemPrimaryRow", "cbo_nn_itemAlternateRow"} & classes):
            continue

        link = row.select_one("a.cbo_nn_itemHover")
        if not link:
            continue
        detail_oid = _parse_detail_id(link)
        if detail_oid is None:
            continue
        allergens = [
            _clean_text(image.get("alt"))
            for image in link.select("img[alt]")
            if _clean_text(image.get("alt"))
        ]
        is_halal = any(value.lower() == "halal" for value in allergens)
        if halal_only and not is_halal:
            continue

        cells = row.find_all("td", recursive=False)
        serving_size = _clean_text(cells[2].get_text(" ", strip=True)) if len(cells) > 2 else None
        portion_values: list[int] = []
        for option in row.select("select option[value]"):
            try:
                portion_values.append(int(option["value"]))
            except (TypeError, ValueError):
                pass

        items.append({
            "detail_oid": detail_oid,
            "name": _direct_link_text(link),
            "category": category,
            "serving_size": serving_size,
            "allergens": allergens,
            "halal": is_halal,
            "portion_percent_options": portion_values,
        })
    return items


def _parse_amount(value: str) -> dict[str, Any]:
    value = _clean_text(value)
    if not value or value.upper() == "NA":
        return {"value": None, "unit": None, "raw": value or None}
    match = re.match(r"^([<>]?\s*\d+(?:\.\d+)?)(.*)$", value)
    if not match:
        return {"value": None, "unit": None, "raw": value}
    number = match.group(1).replace(" ", "")
    try:
        parsed: int | float = float(number.lstrip("<>") )
        if parsed.is_integer():
            parsed = int(parsed)
    except ValueError:
        parsed = None
    return {"value": parsed, "unit": match.group(2).strip() or None, "raw": value}


def parse_nutrition(html: str, *, detail_oid: int | None = None) -> dict[str, Any]:
    """Parse a nutrition-label HTML response into structured JSON."""

    soup = BeautifulSoup(html or "", "html.parser")
    header = soup.select_one(".cbo_nn_LabelHeader")
    bottom = soup.select_one(".cbo_nn_LabelBottomBorderLabel")
    bottom_text = _clean_text(bottom.get_text(" ", strip=True) if bottom else "")

    servings_match = re.search(r"([\d.]+)\s*Servings per container", bottom_text, flags=re.I)
    serving_size_match = re.search(r"Serving Size\s*(.+)$", bottom_text, flags=re.I)
    servings: int | float | None = None
    if servings_match:
        servings = float(servings_match.group(1))
        if servings.is_integer():
            servings = int(servings)

    calories = None
    calories_node = soup.select_one(".cbo_nn_LabelSubHeader .font-22")
    calories_text = _clean_text(calories_node.get_text(" ", strip=True) if calories_node else "")
    if calories_text:
        calories = _first_int(r"(\d+)", calories_text)
    if calories is None:
        calories = _first_int(r"Calories\s+(\d+)", soup.get_text(" ", strip=True))

    nutrients: dict[str, Any] = {}
    for row in soup.select(".cbo_nn_LabelBorderedSubHeader, .cbo_nn_LabelNoBorderSubHeader"):
        left = row.select_one(".inline-div-left")
        if not left:
            continue
        spans = left.find_all("span", recursive=False)
        if len(spans) >= 2:
            nutrient_name = _clean_text(spans[0].get_text(" ", strip=True))
            amount = _parse_amount(spans[-1].get_text(" ", strip=True))
        else:
            text = _clean_text(left.get_text(" ", strip=True))
            match = re.match(r"^(.*?)(NA|[<>]?\s*\d+(?:\.\d+)?\s*[A-Za-z%]*)$", text)
            if not match:
                continue
            nutrient_name = _clean_text(match.group(1))
            amount = _parse_amount(match.group(2))
        if not nutrient_name or nutrient_name.lower() == "include na added sugars":
            continue
        right = row.select_one(".inline-div-right")
        daily_value = _clean_text(right.get_text(" ", strip=True) if right else "")
        nutrients[nutrient_name] = {
            "amount": amount,
            "daily_value_percent": _first_int(r"(\d+)", daily_value) if daily_value else None,
        }

    ingredients = None
    contains = None
    ingredients_label = soup.select_one(".cbo_nn_LabelIngredientsBold")
    if ingredients_label:
        cell = ingredients_label.find_parent("td")
        cell_text = _clean_text(cell.get_text(" ", strip=True) if cell else "")
        remainder = cell_text.split("Ingredients:", 1)[-1].strip()
        split_contains = re.split(r"\s+Contains:\s*", remainder, maxsplit=1)
        ingredients = split_contains[0].strip() or None
        contains = split_contains[1].strip() if len(split_contains) == 2 else None

    return {
        "detail_oid": detail_oid,
        "name": _clean_text(header.get_text(" ", strip=True) if header else ""),
        "servings_per_container": servings,
        "serving_size": _clean_text(serving_size_match.group(1)) if serving_size_match else None,
        "calories": calories,
        "nutrients": nutrients,
        "ingredients": ingredients,
        "contains": contains,
    }


class NetNutritionClient:
    """Session-backed client for the observed NetNutrition endpoints."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        delay: float = 0.0,
        verify: bool | str = True,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.delay = max(0.0, delay)
        self.verify = verify
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "duke-halal-netnutrition-client/1.0",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        })

    def _url(self, controller_action: str) -> str:
        return f"{self.base_url}/{controller_action.lstrip('/')}"

    def _request_headers(self) -> dict[str, str]:
        return {
            "Referer": self.base_url,
            "X-Requested-With": "XMLHttpRequest",
        }

    def _get(self, url: str) -> requests.Response:
        response = self.session.get(
            url,
            headers={"Referer": self.base_url},
            timeout=self.timeout,
            verify=self.verify,
        )
        response.raise_for_status()
        return response

    def _post(self, controller_action: str, data: dict[str, Any] | None = None) -> requests.Response:
        if self.delay:
            time.sleep(self.delay)
        response = self.session.post(
            self._url(controller_action),
            data=data or {},
            headers=self._request_headers(),
            timeout=self.timeout,
            verify=self.verify,
        )
        response.raise_for_status()
        return response

    def _post_json(self, controller_action: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._post(controller_action, data)
        try:
            payload = response.json()
        except ValueError as exc:
            raise NetNutritionError(f"{controller_action} did not return JSON") from exc
        if not isinstance(payload, dict):
            raise NetNutritionError(f"{controller_action} returned {type(payload).__name__}, expected an object")
        if payload.get("success") is False:
            raise NetNutritionError(f"{controller_action} returned success=false: {payload}")
        return payload

    @staticmethod
    def _panels(payload: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for panel in payload.get("panels") or []:
            if isinstance(panel, dict) and panel.get("id"):
                result[str(panel["id"])] = str(panel.get("html") or "")
        return result

    def home(self) -> dict[str, Any]:
        """Load the shell and return units plus the embedded context options."""

        response = self._get(self.base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        contexts: dict[str, list[dict[str, str]]] = {"UN": [], "DT": [], "ML": []}
        for link in soup.select("a[data-type][data-unitoid][data-mealoid][data-date]"):
            type_name = str(link.get("data-type"))
            if type_name not in contexts:
                continue
            contexts[type_name].append({
                "label": _clean_text(link.get_text(" ", strip=True)),
                "unit_oid": str(link.get("data-unitoid")),
                "meal_oid": str(link.get("data-mealoid")),
                "date": str(link.get("data-date")),
            })
        return {
            "units": [asdict(unit) for unit in parse_units(response.text)],
            "contexts": contexts,
        }

    def set_context(
        self,
        *,
        unit: int = -1,
        meal: int = -1,
        date: str = "Show All Dates",
        type_change: str = "DT",
    ) -> dict[str, Any]:
        """Change the site's current unit/date/meal context without a click."""

        payload = self._post_json(
            "Home/HandleNavBarSelection",
            {"unit": unit, "meal": meal, "date": date, "typeChange": type_change},
        )
        return {"panels": self._panels(payload), "raw": payload}

    def select_unit(self, unit_oid: int, *, halal_only: bool = False) -> dict[str, Any]:
        payload = self._post_json("Unit/SelectUnitFromUnitsList", {"unitOid": unit_oid})
        panels = self._panels(payload)
        return {
            "menus": parse_menus(panels.get("menuPanel", "")),
            "items": parse_items(panels.get("itemPanel", ""), halal_only=halal_only),
            "panels": panels,
            "raw": payload,
        }

    def select_menu(self, menu_oid: int, *, halal_only: bool = False) -> dict[str, Any]:
        payload = self._post_json("Menu/SelectMenu", {"menuOid": menu_oid})
        panels = self._panels(payload)
        return {
            "items": parse_items(panels.get("itemPanel", ""), halal_only=halal_only),
            "panels": panels,
            "raw": payload,
        }

    def nutrition(self, detail_oid: int) -> dict[str, Any]:
        response = self._post("NutritionDetail/ShowItemNutritionLabel", {"detailOid": detail_oid})
        return parse_nutrition(response.text, detail_oid=detail_oid)

    def crawl(
        self,
        *,
        unit_oids: Iterable[int] | None = None,
        unit_names: Iterable[str] | None = None,
        include_nutrition: bool = False,
        halal_only: bool = False,
        max_items: int | None = None,
    ) -> dict[str, Any]:
        """Fetch units, menus, items, and optionally nutrition labels."""

        home = self.home()
        units = [Unit(**unit) for unit in home["units"]]
        requested_ids = set(unit_oids or [])
        requested_names = {name.casefold() for name in (unit_names or [])}
        if requested_ids or requested_names:
            units = [
                unit for unit in units
                if unit.unit_oid in requested_ids or unit.name.casefold() in requested_names
            ]
        if not units:
            raise NetNutritionError("No matching units were found on the home page")

        output_units: list[dict[str, Any]] = []
        nutrition_cache: dict[int, dict[str, Any]] = {}
        item_count = 0

        for unit in units:
            selected = self.select_unit(unit.unit_oid, halal_only=halal_only)
            menus = selected["menus"]
            unit_result: dict[str, Any] = {**asdict(unit), "menus": []}

            if menus:
                for menu in menus:
                    menu_result = {**menu, "items": []}
                    items = self.select_menu(menu["menu_oid"], halal_only=halal_only)["items"]
                    for item in items:
                        if max_items is not None and item_count >= max_items:
                            break
                        item_count += 1
                        if include_nutrition:
                            detail_oid = item["detail_oid"]
                            if detail_oid not in nutrition_cache:
                                nutrition_cache[detail_oid] = self.nutrition(detail_oid)
                            item["nutrition"] = nutrition_cache[detail_oid]
                        menu_result["items"].append(item)
                    unit_result["menus"].append(menu_result)
                    if max_items is not None and item_count >= max_items:
                        break
            else:
                items = selected["items"]
                direct_menu = {"menu_oid": None, "name": None, "items": []}
                for item in items:
                    if max_items is not None and item_count >= max_items:
                        break
                    item_count += 1
                    if include_nutrition:
                        detail_oid = item["detail_oid"]
                        if detail_oid not in nutrition_cache:
                            nutrition_cache[detail_oid] = self.nutrition(detail_oid)
                        item["nutrition"] = nutrition_cache[detail_oid]
                    direct_menu["items"].append(item)
                unit_result["menus"].append(direct_menu)
            output_units.append(unit_result)
            if max_items is not None and item_count >= max_items:
                break

        return {
            "source": self.base_url,
            "units": output_units,
            "item_count": item_count,
            "nutrition_included": include_nutrition,
            "halal_only": halal_only,
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--unit", action="append", dest="units", help="Restaurant name; repeat for multiple restaurants")
    parser.add_argument("--unit-id", action="append", type=int, dest="unit_ids", help="NetNutrition unitOid; repeat for multiple units")
    parser.add_argument("--list-units", action="store_true", help="Print restaurant IDs and exit")
    parser.add_argument("--nutrition", action="store_true", help="Fetch the nutrition label for every returned item")
    parser.add_argument("--halal-only", action="store_true", help="Keep only items with the Halal allergen marker")
    parser.add_argument("--max-items", type=int, help="Stop after this many items")
    parser.add_argument("--delay", type=float, default=0.0, help="Optional seconds between POST requests (default: 0)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--ca-bundle", type=Path, help="CA bundle path to use for TLS verification")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification (use only for a trusted local MITM setup)")
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.insecure:
        warnings.simplefilter("ignore", InsecureRequestWarning)
    verify: bool | str = False if args.insecure else (str(args.ca_bundle) if args.ca_bundle else True)
    client = NetNutritionClient(args.base_url, timeout=args.timeout, delay=args.delay, verify=verify)
    try:
        home = client.home()
        if args.list_units:
            print(json.dumps(home["units"], indent=2, ensure_ascii=False))
            return 0

        result = client.crawl(
            unit_oids=args.unit_ids,
            unit_names=args.units,
            include_nutrition=args.nutrition,
            halal_only=args.halal_only,
            max_items=args.max_items,
        )
    except (requests.RequestException, NetNutritionError) as exc:
        print(f"NetNutrition client error: {exc}", file=sys.stderr)
        return 1

    encoded = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
        print(f"Wrote {result['item_count']} items to {args.output}")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
