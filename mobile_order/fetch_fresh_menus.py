#!/usr/bin/env python3
"""Fetch fresh Transact menus without Charles.

The login token, user ID, and session ID are read from environment variables
so they are not written into the menu exports or source code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENDPOINT = "https://mobileorderprodapi.transactcampus.com/api_user/getmenu"
WEEKDAYS = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "restaurant"


def format_clock(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)[:5]


def service_windows(row: dict, prefix: str) -> list[dict[str, str | None]]:
    windows = []
    for suffix in ("", "_2", "_3"):
        opening = format_clock(row.get(f"{prefix}_open_time{suffix}"))
        closing = format_clock(row.get(f"{prefix}_close_time{suffix}"))
        if opening is None or closing is None:
            continue
        if suffix and opening == "00:00" and closing == "00:00":
            continue
        windows.append({"open": opening, "close": closing})
    return windows


def simple_hours(location: dict) -> dict:
    weekly = {}
    for row in location.get("hours_list") or []:
        takeout = service_windows(row, "takeout")
        delivery = service_windows(row, "delivery")
        holiday_date = row.get("holiday_date") or ""
        holiday_end = row.get("holiday_date_end") or ""
        label = row.get("label") or WEEKDAYS.get(row.get("day_of_week"), "")
        if holiday_date or holiday_end:
            continue
        if label:
            day = weekly.setdefault(label, {"takeout": [], "delivery": []})
            day["takeout"].extend(takeout)
            day["delivery"].extend(delivery)
    return weekly


def money(value: object) -> float | None:
    if value in (None, ""):
        return None
    return round(float(value) / 100, 2)


def compact_option(option: dict) -> dict:
    return {
        "name": option.get("name") or option.get("qp_name", ""),
        "minimum": option.get("minimum"),
        "maximum": option.get("maximum"),
        "allow_quantity": bool(option.get("allow_qty")),
        "values": [
            {
                "name": value.get("name") or value.get("qp_name", ""),
                "price": money(value.get("price")),
                "is_default": bool(value.get("is_default")),
                "is_hidden": bool(value.get("is_hidden") or value.get("is_deleted")),
                "is_out_of_stock": bool(value.get("pos_outofstock")),
                "max_quantity": value.get("max_quantity"),
            }
            for value in option.get("values") or []
        ],
    }


def compact_item(item: dict) -> dict:
    return {
        "name": item.get("name") or item.get("qp_name", ""),
        "description": item.get("description", ""),
        "price": money(item.get("price_display", item.get("price_base"))),
        "options": [compact_option(option) for option in item.get("options") or []],
        "busy_min": item.get(
            "busy_minimum_pickup_minutes",
            item.get("busy_kitchen_print_minutes"),
        ),
        "normal_min": item.get(
            "normal_minimum_pickup_minutes",
            item.get("normal_kitchen_print_minutes"),
        ),
        "is_hidden": bool(item.get("is_hidden")),
    }


def fetch_menu(token: str, user_id: str, session_id: str, campus_id: int, location_id: int) -> dict:
    body = {
        "ct_id2": "0",
        "target_date": "",
        "userid": user_id,
        "target_time": "",
        "campusid": str(campus_id),
        "ct_id": "0",
        "locationid": str(location_id),
        "payment_method": "0",
        "retrieval_type": "0",
    }
    request = Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "TransactMenuFetcher/1.0",
            "sessionid": session_id,
            "login_token": token,
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def normalize(response: dict) -> dict:
    location = response.get("location") or {}
    menu = response.get("menu") or {}
    sections = []
    for section in menu.get("sections_1") or []:
        if section.get("is_deleted", 0):
            continue
        sections.append(
            {
                "name": section.get("name", ""),
                "is_hidden": bool(section.get("is_hidden")),
                "items": [
                    compact_item(item)
                    for item in section.get("items") or []
                    if not item.get("is_deleted", 0)
                ],
            }
        )
    return {
        "restaurant": location.get("name", ""),
        "campus_id": location.get("campusid"),
        "location_id": location.get("locationid"),
        "cafeteria_id": location.get("cafeteriaid"),
        "icon_image_url": location.get("icon_picture_url", ""),
        "estimated_wait_time_minutes": location.get("estimated_wait_time"),
        "currently_open": bool(
            location.get("is_currently_takeout_open")
            or location.get("is_currently_delivery_open")
        ),
        "takeout_open": bool(location.get("is_currently_takeout_open")),
        "delivery_open": bool(location.get("is_currently_delivery_open")),
        "takeout_hours": {
            "open": location.get("takeout_open_time"),
            "close": location.get("takeout_close_time"),
        },
        "delivery_hours": {
            "open": location.get("delivery_open_time"),
            "close": location.get("delivery_close_time"),
        },
        "hours": simple_hours(location),
        "retrieved_at": menu.get("retrieved_at_datetime"),
        "menu_last_updated": menu.get("menu_last_updated_datetime"),
        "sections": sections,
    }


def load_session(session_file: Path) -> tuple[str, str, str]:
    """Load the captured session without exposing its values in menu exports."""
    try:
        payload = json.loads(session_file.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"Captured session file not found: {session_file}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Captured session file is not valid JSON: {session_file}") from error

    token = str(payload.get("login_token", ""))
    user_id = str(payload.get("userid", ""))
    session_id = str(payload.get("sessionid", ""))
    if not token or not user_id or not session_id:
        raise RuntimeError(
            "Captured session is missing login_token, userid, or sessionid. "
            "Reload a menu in Mobile Order while capture is running."
        )
    return token, user_id, session_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument(
        "--session-file",
        type=Path,
        default=Path(
            os.environ.get(
                "TRANSACT_SESSION_FILE",
                Path(__file__).resolve().parent / ".transact-session.json",
            )
        ),
    )
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()

    token = os.environ.get("TRANSACT_LOGIN_TOKEN")
    user_id = os.environ.get("TRANSACT_USER_ID")
    session_id = os.environ.get("TRANSACT_SESSION_ID")
    if not token or not user_id or not session_id:
        try:
            token, user_id, session_id = load_session(args.session_file.expanduser().resolve())
        except RuntimeError as error:
            print(error, file=sys.stderr)
            return 2

    index_path = Path(__file__).resolve().parent / "restaurants.json"
    restaurants = json.loads(index_path.read_text(encoding="utf-8"))["restaurants"]
    output_dir = args.output_dir.resolve()
    menu_dir = output_dir / "menus"
    menu_dir.mkdir(parents=True, exist_ok=True)

    fresh = []
    for number, restaurant in enumerate(restaurants, start=1):
        name = restaurant["restaurant"]
        location_id = int(restaurant["location_id"])
        campus_id = int(restaurant["campus_id"])
        print(f"[{number}/{len(restaurants)}] {name}", flush=True)
        try:
            response = fetch_menu(token, user_id, session_id, campus_id, location_id)
            if response.get("message") != "SUCCESS":
                print(f"  server message: {response.get('message', 'unknown')}", file=sys.stderr)
                continue
            normalized = normalize(response)
            fresh.append(normalized)
            filename = f"{slugify(name)}__location-{location_id}.json"
            (menu_dir / filename).write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except HTTPError as error:
            print(f"  HTTP {error.code}; token may be expired or invalid", file=sys.stderr)
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            print(f"  request failed: {error}", file=sys.stderr)
        if number < len(restaurants):
            time.sleep(max(args.delay, 0))

    fresh.sort(key=lambda item: item.get("restaurant", "").lower())
    output_dir.mkdir(parents=True, exist_ok=True)

    fresh_by_location = {str(item.get("location_id")): item for item in fresh}
    restaurant_index = []
    for source_restaurant in restaurants:
        location_key = str(source_restaurant.get("location_id", ""))
        normalized = fresh_by_location.get(location_key)
        if normalized is None:
            restaurant_index.append(source_restaurant)
            continue
        filename = f"{slugify(normalized.get('restaurant', ''))}__location-{normalized.get('location_id')}.json"
        restaurant_index.append(
            {
                "restaurant": normalized.get("restaurant", ""),
                "campus_id": normalized.get("campus_id"),
                "location_id": normalized.get("location_id"),
                "cafeteria_id": normalized.get("cafeteria_id"),
                "icon_image_url": normalized.get("icon_image_url", ""),
                "estimated_wait_time_minutes": normalized.get("estimated_wait_time_minutes"),
                "currently_open": normalized.get("currently_open", False),
                "takeout_hours": normalized.get("takeout_hours", {}),
                "delivery_hours": normalized.get("delivery_hours", {}),
                "hours": normalized.get("hours", []),
                "retrieved_at": normalized.get("retrieved_at"),
                "menu_last_updated": normalized.get("menu_last_updated"),
                "section_count": len(normalized.get("sections") or []),
                "item_count": sum(
                    len(section.get("items") or [])
                    for section in normalized.get("sections") or []
                ),
                "file": f"menus/{filename}",
            }
        )
    restaurant_index.sort(key=lambda item: item.get("restaurant", "").lower())

    (output_dir / "restaurants.json").write_text(
        json.dumps(
            {
                "restaurant_count": len(restaurant_index),
                "restaurants": restaurant_index,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "all_restaurant_menus.json").write_text(
        json.dumps(
            {
                "restaurant_count": len(fresh),
                "restaurants": fresh,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Fetched {len(fresh)} menus into {output_dir}")
    return 0 if fresh else 1


if __name__ == "__main__":
    raise SystemExit(main())
