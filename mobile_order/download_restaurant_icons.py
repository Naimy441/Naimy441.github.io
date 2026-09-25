#!/usr/bin/env python3
"""Download the restaurant icons referenced by the Mobile Order JSON exports.

This is intentionally separate from the menu refresh flow. Run it once, or
again whenever you want to refresh the local icon copies.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "mobile_order"
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Folder containing the Mobile Order JSON exports",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    aggregate_path = output_dir / "all_restaurant_menus.json"
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))

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
            downloaded += 1
            print(f"Downloaded {name}: images/{filename}")
        except (HTTPError, URLError, OSError, RuntimeError, json.JSONDecodeError) as error:
            failed.append(f"{name}: {error}")

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
