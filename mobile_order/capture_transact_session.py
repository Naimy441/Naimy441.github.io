"""Capture Transact session values from the user's local getmenu traffic.

This addon only observes the matching request and writes the current session
to a local mode-600 file. It does not print or modify credentials.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from mitmproxy import http


HOST = "mobileorderprodapi.transactcampus.com"
PATH_PREFIX = "/api_user/getmenu"
SESSION_FILE = Path(os.environ.get("TRANSACT_SESSION_FILE", "/private/tmp/transact-session.json"))


def request(flow: http.HTTPFlow) -> None:
    request = flow.request
    # In local process-capture mode, mitmproxy may expose the resolved server
    # IP as request.host instead of the original hostname. The endpoint path
    # and these two Transact headers identify the intended request reliably.
    if not request.path.startswith(PATH_PREFIX):
        return

    login_token = request.headers.get("login_token")
    session_id = request.headers.get("sessionid")
    if not login_token or not session_id:
        return

    try:
        body = json.loads(request.get_text(strict=False) or "{}")
    except (TypeError, ValueError):
        body = {}

    payload = {
        "login_token": login_token,
        "sessionid": session_id,
        "userid": str(body.get("userid", "")),
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="transact-session-", suffix=".json", dir=SESSION_FILE.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
            handle.write("\n")
        os.replace(temp_name, SESSION_FILE)
        print(f"Captured Transact getmenu session from {request.host}.", flush=True)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
