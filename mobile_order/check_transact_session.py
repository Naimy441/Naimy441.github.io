#!/usr/bin/env python3
"""Check whether the saved Transact/Mobile Order session is still usable."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

from fetch_fresh_menus import fetch_menu, is_session_failure, load_session


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "outputs" / "mobile_order"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--session-file",
        type=Path,
        default=Path(
            os.environ.get("TRANSACT_SESSION_FILE", SCRIPT_DIR / ".transact-session.json")
        ),
        help="Captured session JSON file (default: mobile_order/.transact-session.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("FRESH_MENU_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)),
        help="Folder containing restaurants.json",
    )
    args = parser.parse_args()

    token = os.environ.get("TRANSACT_LOGIN_TOKEN")
    user_id = os.environ.get("TRANSACT_USER_ID")
    session_id = os.environ.get("TRANSACT_SESSION_ID")
    if not all((token, user_id, session_id)):
        try:
            token, user_id, session_id = load_session(args.session_file.expanduser().resolve())
        except RuntimeError as error:
            print(f"Session check could not start: {error}", file=sys.stderr)
            return 2

    index_path = args.output_dir.expanduser().resolve() / "restaurants.json"
    try:
        restaurants = json.loads(index_path.read_text(encoding="utf-8"))["restaurants"]
        restaurant = restaurants[0]
    except (OSError, KeyError, IndexError, json.JSONDecodeError) as error:
        print(f"Could not read the restaurant index: {error}", file=sys.stderr)
        return 2

    name = restaurant["restaurant"]
    campus_id = int(restaurant["campus_id"])
    location_id = int(restaurant["location_id"])
    print(f"Testing the saved session with {name}...")

    try:
        response = fetch_menu(token, user_id, session_id, campus_id, location_id)
    except HTTPError as error:
        if error.code in {401, 403}:
            print(f"Session is expired or rejected (HTTP {error.code}).")
            return 1
        print(f"Session check failed with HTTP {error.code}: {error.reason}", file=sys.stderr)
        return 2
    except URLError as error:
        print(f"Session check could not reach Transact: {error.reason}", file=sys.stderr)
        return 2
    except TimeoutError:
        print("Session check timed out while contacting Transact.", file=sys.stderr)
        return 2

    if response.get("message") == "SUCCESS":
        print("Session is valid and the menu request succeeded.")
        return 0

    message = response.get("message") or "The server rejected the request without a message."
    if is_session_failure(message):
        print(f"Session is expired or rejected: {message}")
        return 1
    print(f"Transact rejected the request for a non-authentication reason: {message}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
