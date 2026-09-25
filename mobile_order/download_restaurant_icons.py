#!/usr/bin/env python3
"""Download the restaurant icons referenced by the Mobile Order JSON exports.

This is intentionally separate from the menu refresh flow. Run it once, or
again whenever you want to refresh the local icon copies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen


IMAGE_BASE_URL = "https://hangrybbprod.blob.core.windows.net/"


def icon_filename(value: object) -> str | None:
    if not value:
        return None
    name = Path(unquote(urlparse(str(value)).path)).name
    if not name or name in {".", ".."}:
        return None
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return safe_name or None


def download_icon(icon_value: object, output_dir: Path) -> str | None:
    if not icon_value:
        return None
    value = str(icon_value)
    url = value if value.startswith(("http://", "https://")) else urljoin(
        IMAGE_BASE_URL, value.lstrip("/")
    )
    filename = icon_filename(value)
    if not filename:
        return None

    destination = output_dir / filename
    if destination.exists() and destination.stat().st_size > 0:
        return filename

    request = Request(
        url,
        headers={"Accept": "image/*", "User-Agent": "TransactIconDownloader/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        content = response.read()
    if not content:
        raise RuntimeError("the image response was empty")
    destination.write_bytes(content)
    return filename


def write_json(path: Path, payload: dict) -> None:
    temporary = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    )
    try:
        with temporary:
            json.dump(payload, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
        os.replace(temporary.name, path)
    finally:
        if os.path.exists(temporary.name):
            os.unlink(temporary.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Folder containing the Mobile Order JSON exports",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    aggregate_path = output_dir / "all_restaurant_menus.json"
    restaurants_path = output_dir / "restaurants.json"
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    restaurants_index = json.loads(restaurants_path.read_text(encoding="utf-8"))
    by_location = {
        str(item.get("location_id")): item
        for item in restaurants_index.get("restaurants", [])
    }

    downloaded = 0
    skipped = 0
    failed = []
    for restaurant in aggregate.get("restaurants", []):
        name = restaurant.get("restaurant", "Unnamed restaurant")
        try:
            filename = download_icon(restaurant.get("icon_image_url"), image_dir)
            if not filename:
                skipped += 1
                continue
            local_path = f"images/{filename}"
            restaurant["icon_image_file"] = local_path
            indexed = by_location.get(str(restaurant.get("location_id")))
            if indexed is not None:
                indexed["icon_image_file"] = local_path
            menu_path = output_dir / restaurant.get("file", "")
            if menu_path.is_file():
                menu = json.loads(menu_path.read_text(encoding="utf-8"))
                menu["icon_image_file"] = local_path
                write_json(menu_path, menu)
            downloaded += 1
            print(f"Downloaded {name}: {local_path}")
        except (HTTPError, URLError, OSError, RuntimeError, json.JSONDecodeError) as error:
            failed.append(f"{name}: {error}")

    write_json(aggregate_path, aggregate)
    write_json(restaurants_path, restaurants_index)
    print(f"Downloaded or confirmed {downloaded} icons into {image_dir}")
    if skipped:
        print(f"Skipped {skipped} restaurants without an icon URL")
    if failed:
        print("Icon download failures:", file=sys.stderr)
        for message in failed:
            print(f"  {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
