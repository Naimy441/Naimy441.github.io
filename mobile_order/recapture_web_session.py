#!/usr/bin/env python3
"""Capture a Transact session through the Duke web SSO flow.

This is intentionally separate from refresh_menus.sh and the Mobile Order
process-capture addon. It starts a headless mitmdump proxy by default, launches a
dedicated Chrome profile, and waits for the normal interactive Duke login.

The normal interactive mode never receives or stores a password. The optional
headless mode reads TRANSACT_NETID and TRANSACT_PASSWORD from the process environment
and does not write either value to disk.

Run from the project root:

    python3 mobile_order/recapture_web_session.py --fetch

The capture proxy runs headlessly by default. Use --dashboard when the
mitmweb dashboard is wanted for debugging.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

try:
    # The orchestrator itself does not need the mitmproxy Python package. The
    # package is available when mitmweb loads this file with `-s`.
    from mitmproxy import http
except ModuleNotFoundError:  # pragma: no cover - used by the outer process
    http = Any  # type: ignore[assignment,misc]


HOST = "mobileorderprodapi.transactcampus.com"
LOGIN_URL = f"https://{HOST}/api_user/samllogin?campusid=19"
API_URL = f"https://{HOST}"
SSO_CAMPUS_ID = "19"
SSO_APP_HASH_OVERRIDE = os.environ.get("TRANSACT_SSO_HASH", "")
# This is the salt embedded in the native Transact client. The app computes
# HMAC-SHA256(temp_token, key=salt) and sends the lowercase hexadecimal digest
# as the `hash` field of registerwithcampusssotoken.
SSO_HASH_SALT = b"dFz9Dq435BT3xCVU2PCy"
CAPTURE_PATHS = {
    "/api_user/loginwithtoken",
    "/api_user/registerwithcampusssotoken",
    "/api_user/getmenu",
}

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "mobile_order"
DEFAULT_SESSION_FILE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "DukeHalalMobileOrder"
    / "web-transact-session.json"
)
DEFAULT_PROFILE_DIR = (
    Path.home()
    / "Library"
    / "Application Support"
    / "DukeHalalMobileOrder"
    / "browser-profile"
)


def _load_local_env() -> None:
    """Load simple local .env values without overriding real environment vars."""
    for env_path in (PROJECT_DIR / ".env", SCRIPT_DIR / ".env"):
        if not env_path.is_file():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            key, separator, value = line.partition("=")
            key = key.strip()
            if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ.setdefault(key, value)


_load_local_env()


def _hidden_inputs(html: str) -> dict[str, str]:
    """Extract simple hidden input fields without addon dependencies."""
    values: dict[str, str] = {}
    for tag in re.findall(r"<input\b[^>]*>", html, flags=re.IGNORECASE):
        attributes = {}
        for match in re.finditer(
            r"([:\w-]+)\s*=\s*(['\"])(.*?)\2", tag, flags=re.IGNORECASE
        ):
            attributes[match.group(1).lower()] = match.group(3)
        name = attributes.get("name") or attributes.get("id")
        if name:
            values[name] = attributes.get("value", "")
    return values


def _walk_values(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).lower(), child
            yield from _walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child)


def _find_string(data: Any, names: set[str], *, minimum_length: int = 1) -> str:
    for key, value in _walk_values(data):
        if key in names and isinstance(value, (str, int)):
            result = str(value).strip()
            if len(result) >= minimum_length:
                return result
    return ""


def _json_body(flow: http.HTTPFlow) -> dict[str, Any]:
    try:
        body = flow.response.get_text(strict=False) if flow.response else ""
        parsed = json.loads(body or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _request_json_body(flow: http.HTTPFlow) -> dict[str, Any]:
    try:
        parsed = json.loads(flow.request.get_text(strict=False) or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _write_session(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix="web-transact-session-", suffix=".json", dir=path.parent
    )
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
            handle.write("\n")
        os.replace(temporary_name, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _write_json_private(path: Path, payload: dict[str, str]) -> None:
    _write_session(path, payload)


def _api_post(
    path: str,
    payload: dict[str, str],
    extra_headers: dict[str, str] | None = None,
    proxy_port: int | None = None,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Transact%20Prod/92 CFNetwork/3860.500.112 Darwin/25.4.0",
    }
    if extra_headers:
        headers.update(extra_headers)
    request = Request(
        f"{API_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    if proxy_port is None:
        opener = build_opener()
    else:
        proxy = f"http://127.0.0.1:{proxy_port}"
        mitm_ca = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.pem"
        if mitm_ca.exists():
            tls_context = ssl.create_default_context(cafile=str(mitm_ca))
        else:
            # The connection being relaxed is only Python -> mitmproxy on
            # loopback. mitmproxy still verifies the remote Transact TLS hop.
            tls_context = ssl._create_unverified_context()
        opener = build_opener(
            ProxyHandler({"http": proxy, "https": proxy}),
            HTTPSHandler(context=tls_context),
        )
    with opener.open(request, timeout=30) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def _response_message(response: dict[str, Any]) -> str:
    message = response.get("message")
    return str(message) if message is not None else "Unknown Transact response"


def _transact_sso_hash(temp_token: str) -> str:
    """Return the same SSO registration hash generated by the native app."""
    return hmac.new(
        SSO_HASH_SALT,
        temp_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def complete_web_sso(temp_token: str, session_file: Path, proxy_port: int) -> None:
    """Perform the two native-client calls that follow /api_user/samlsuccess."""
    session_id = str(int(time.time() * 1000))
    # The native app computes HMAC-SHA256 over the one-time SAML temp token.
    # An explicit environment override remains available for testing a
    # captured value without changing the normal flow.
    sso_hash = SSO_APP_HASH_OVERRIDE or _transact_sso_hash(temp_token)
    register_payload = {
        "userid": "0",
        "hash": sso_hash,
        "os_type": "0",
        "app_bundle_name": "com.transact.mobileorder",
        "language": "EN",
        "temp_token": temp_token,
        "campusid": SSO_CAMPUS_ID,
    }
    register_response = _api_post(
        "/api_user/registerwithcampusssotoken",
        register_payload,
        {"sessionid": session_id},
        proxy_port,
    )
    if str(register_response.get("status", "")).upper() != "OK":
        raise RuntimeError(
            "registerwithcampusssotoken failed: "
            f"{_response_message(register_response)}"
        )

    registered_user = register_response.get("user")
    registered_user = registered_user if isinstance(registered_user, dict) else {}
    user_id = _find_string(registered_user, {"userid"})
    if not user_id:
        user_id = _find_string(register_response, {"userid"})
    if not user_id:
        raise RuntimeError("The SSO registration response did not include a user ID.")
    registration_token = _find_string(
        registered_user, {"login_token"}, minimum_length=20
    )
    if not registration_token:
        registration_token = _find_string(
            register_response, {"login_token"}, minimum_length=20
        )
    if not registration_token:
        raise RuntimeError("The SSO registration response did not include a login token.")

    login_payload = {
        "device_model": "DukeHalal Web SSO",
        "campusid": SSO_CAMPUS_ID,
        "on_launch": "1",
        "app_version": "2026.3.1",
        "userid": user_id,
        "carrier_name": "",
        "accessibility_mode": "0",
        "device_name": "DukeHalal Web SSO",
        "push_enabled": "0",
        "os_language": "en-US",
        "timezone": "EST",
        "app_bundle_name": "com.transact.mobileorder",
        "os_version": "web",
        "push_token": "",
        "os_type": "0",
    }
    login_response = _api_post(
        "/api_user/loginwithtoken",
        login_payload,
        {"sessionid": session_id, "login_token": registration_token},
        proxy_port,
    )
    if str(login_response.get("status", "")).upper() != "OK":
        raise RuntimeError(
            f"loginwithtoken failed: {_response_message(login_response)}"
        )

    login_user = login_response.get("user")
    login_user = login_user if isinstance(login_user, dict) else {}
    login_token = _find_string(login_user, {"login_token"}, minimum_length=20)
    if not login_token:
        login_token = _find_string(login_response, {"login_token"}, minimum_length=20)
    if not login_token:
        raise RuntimeError("The final login response did not include a login token.")

    _write_session(
        session_file,
        {
            "login_token": login_token,
            "userid": user_id,
            "sessionid": session_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "/api_user/loginwithtoken via web SSO",
        },
    )


class WebSessionCapture:
    """mitmproxy addon loaded by this same file."""

    def __init__(self) -> None:
        self.session_file = Path(
            os.environ.get("TRANSACT_WEB_SESSION_FILE", str(DEFAULT_SESSION_FILE))
        ).expanduser().resolve()
        self.sso_event_file = Path(
            os.environ.get(
                "TRANSACT_WEB_SSO_EVENT_FILE",
                str(self.session_file.with_name("web-transact-sso-event.json")),
            )
        ).expanduser().resolve()

    def response(self, flow: http.HTTPFlow) -> None:
        request = flow.request
        if request.host != HOST:
            return
        path = request.path.split("?", 1)[0]
        if path == "/api_user/samlsuccess" and flow.response:
            fields = _hidden_inputs(flow.response.get_text(strict=False) or "")
            temp_token = fields.get("temp_token", "")
            if temp_token:
                _write_json_private(
                    self.sso_event_file,
                    {
                        "temp_token": temp_token,
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                print("Captured the temporary web SSO handoff.", flush=True)
            return
        if path not in CAPTURE_PATHS:
            return

        body = _json_body(flow)
        request_body = _request_json_body(flow)
        headers = {str(key).lower(): str(value) for key, value in request.headers.items()}

        # The login response normally contains login_token/userid. The
        # getmenu fallback matches the existing app-capture behavior in case
        # the browser completes the final exchange through a later request.
        login_token = _find_string(
            body,
            {"login_token", "logintoken"},
            minimum_length=20,
        )
        if not login_token:
            login_token = headers.get("login_token", "")

        user_id = _find_string(body, {"userid", "user_id"}) or _find_string(
            request_body, {"userid", "user_id"}
        )
        if not user_id:
            user_id = headers.get("userid", "")

        session_id = _find_string(body, {"sessionid", "session_id"}) or _find_string(
            request_body, {"sessionid", "session_id"}
        )
        if not session_id:
            session_id = headers.get("sessionid", "")

        if not (login_token and user_id and session_id):
            return

        payload = {
            "login_token": login_token,
            "userid": user_id,
            "sessionid": session_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": path,
        }
        _write_session(self.session_file, payload)
        print(f"Captured web Transact session from {path}.", flush=True)


# This makes the file usable directly as a mitmproxy addon with `-s`.
addons = [WebSessionCapture()]


def progress(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def wait_for_port(host: str, port: int, process: subprocess.Popen[bytes], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.2)
            try:
                connection.connect((host, port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def launch_browser(profile_dir: Path, proxy_port: int, browser_app: str) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "open",
        "-na",
        browser_app,
        "--args",
        f"--user-data-dir={profile_dir}",
        f"--proxy-server=http://127.0.0.1:{proxy_port}",
        "--disable-quic",
        LOGIN_URL,
    ]
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def launch_headless_browser(
    profile_dir: Path,
    proxy_port: int,
    netid: str,
    password: str,
    login_url: str,
    event_file: Path,
    event_before: int,
):
    """Launch Chrome headlessly and submit the Duke SSO form.

    The browser remains headless, but Duke may still require a visible browser
    for WebAuthn or another MFA challenge. In that case the caller times out
    and can be rerun without --headless-login.
    """
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Headless login requires the Python Playwright package. "
            "Run `python3 -m pip install playwright` first."
        ) from error

    playwright = sync_playwright().start()
    launch_options: dict[str, Any] = {
        "headless": True,
        "proxy": {"server": f"http://127.0.0.1:{proxy_port}"},
        "args": ["--disable-quic"],
        # The browser-to-local-mitm connection is local; mitmproxy handles
        # verification of the remote HTTPS connection.
        "ignore_https_errors": True,
    }
    chrome_path = Path(
        os.environ.get(
            "DUKE_SSO_CHROME_EXECUTABLE",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
    )
    if chrome_path.exists():
        launch_options["executable_path"] = str(chrome_path)

    try:
        browser_context = playwright.chromium.launch_persistent_context(
            str(profile_dir), **launch_options
        )
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        page.goto(login_url, wait_until="domcontentloaded", timeout=60_000)

        event_is_new = event_file.exists() and event_file.stat().st_mtime_ns > event_before
        if not event_is_new:
            try:
                page.locator('input[name="j_username"]').wait_for(
                    state="visible", timeout=15_000
                )
                page.locator('input[name="j_username"]').fill(netid)
                page.locator('input[name="j_password"]').fill(password)
                page.locator(
                    'input[name="Submit"], input[type="submit"], button[type="submit"]'
                ).first.click()
            except PlaywrightTimeoutError as error:
                if not (event_file.exists() and event_file.stat().st_mtime_ns > event_before):
                    raise RuntimeError(
                        "The headless SSO page did not expose the login form. "
                        "Duke may be requesting MFA or another interactive step."
                    ) from error
        return playwright, browser_context
    except Exception:
        playwright.stop()
        raise


def run_checked(command: list[str]) -> int:
    return subprocess.run(command, cwd=PROJECT_DIR).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--session-file",
        type=Path,
        default=Path(os.environ.get("TRANSACT_WEB_SESSION_FILE", DEFAULT_SESSION_FILE)),
        help="Where to save the web-captured session (default: outside the repo).",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=Path(os.environ.get("DUKE_SSO_PROFILE_DIR", DEFAULT_PROFILE_DIR)),
        help="Persistent browser profile directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("FRESH_MENU_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)),
        help="Mobile Order output directory used for validation/fetching.",
    )
    parser.add_argument("--proxy-port", type=int, default=int(os.environ.get("DUKE_SSO_PROXY_PORT", "8080")))
    parser.add_argument("--web-port", type=int, default=int(os.environ.get("DUKE_SSO_WEB_PORT", "8081")))
    parser.add_argument("--browser", default=os.environ.get("DUKE_SSO_BROWSER_APP", "Google Chrome"))
    parser.add_argument("--timeout", type=float, default=600, help="Seconds to wait for login.")
    parser.add_argument("--fetch", action="store_true", help="Fetch fresh menus after capturing and validating.")
    parser.add_argument(
        "--headless-login",
        action="store_true",
        help="Fill Duke SSO from TRANSACT_NETID/TRANSACT_PASSWORD using headless Chrome.",
    )
    parser.add_argument(
        "--netid",
        default=os.environ.get("TRANSACT_NETID", ""),
        help="Duke NetID for --headless-login (prefer TRANSACT_NETID).",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Use mitmweb and open its dashboard for debugging (default: headless mitmdump).",
    )
    # Keep the old flag working for callers that already use it. Headless
    # capture is now the default, so this is intentionally hidden from help.
    parser.add_argument("--no-dashboard", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.headless_login:
        if not args.netid.strip():
            print("--headless-login requires TRANSACT_NETID or --netid.", file=sys.stderr)
            return 2
        if not os.environ.get("TRANSACT_PASSWORD"):
            print("--headless-login requires the TRANSACT_PASSWORD environment variable.", file=sys.stderr)
            return 2

    use_dashboard = args.dashboard and not args.no_dashboard
    mitm_command = shutil.which("mitmweb" if use_dashboard else "mitmdump")
    if not mitm_command:
        required_command = "mitmweb" if use_dashboard else "mitmdump"
        print(f"{required_command} was not found. Install mitmproxy first.", file=sys.stderr)
        return 2
    if not args.headless_login and shutil.which("open") is None:
        print("macOS 'open' command was not found.", file=sys.stderr)
        return 2

    session_file = args.session_file.expanduser().resolve()
    profile_dir = args.profile_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    event_file = session_file.with_name("web-transact-sso-event.json")
    event_before = event_file.stat().st_mtime_ns if event_file.exists() else 0

    env = os.environ.copy()
    env["TRANSACT_WEB_SESSION_FILE"] = str(session_file)
    env["TRANSACT_WEB_SSO_EVENT_FILE"] = str(event_file)
    env["PYTHONPATH"] = str(SCRIPT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    # The proxy addon does not need the login credentials.
    env.pop("TRANSACT_PASSWORD", None)
    env.pop("TRANSACT_NETID", None)
    flow_file = Path(f"/private/tmp/duke-halal-web-flow-{os.getpid()}.mitm")
    flow_file.parent.mkdir(parents=True, exist_ok=True)
    flow_file.touch(mode=0o600, exist_ok=True)
    os.chmod(flow_file, 0o600)
    retain_flow_file = False
    playwright_runtime = None
    browser_context = None

    command = [
        mitm_command,
        "--mode",
        "regular",
        "--listen-host",
        "127.0.0.1",
        "--listen-port",
        str(args.proxy_port),
        "-w",
        str(flow_file),
        "-s",
        str(Path(__file__).resolve()),
    ]
    dashboard_token = ""
    if use_dashboard:
        dashboard_token = secrets.token_urlsafe(32)
        command[command.index("-w"):command.index("-w")] = [
            "--web-host",
            "127.0.0.1",
            "--web-port",
            str(args.web_port),
            "--set",
            "web_open_browser=false",
            "--set",
            f"web_password={dashboard_token}",
        ]
    mitm_log = Path("/private/tmp/duke-halal-web-mitm.log")
    progress(
        "Starting mitmweb in browser-proxy mode..."
        if use_dashboard
        else "Starting headless mitmdump in browser-proxy mode..."
    )
    with mitm_log.open("w", encoding="utf-8") as log_handle:
        mitm = subprocess.Popen(command, env=env, stdout=log_handle, stderr=subprocess.STDOUT)

    try:
        if not wait_for_port("127.0.0.1", args.proxy_port, mitm, 15):
            print(f"{mitm_command} did not start. See {mitm_log}", file=sys.stderr)
            return 1
        if use_dashboard:
            if not wait_for_port("127.0.0.1", args.web_port, mitm, 15):
                print(f"mitmweb dashboard did not start. See {mitm_log}", file=sys.stderr)
                return 1
            url = (
                f"http://127.0.0.1:{args.web_port}/?token="
                f"{quote(dashboard_token, safe='')}"
            )
            subprocess.Popen(["open", url])
            progress(f"mitmweb dashboard opened at http://127.0.0.1:{args.web_port}")

        if args.headless_login:
            progress("Opening headless Chrome and submitting the Duke SSO form...")
            try:
                playwright_runtime, browser_context = launch_headless_browser(
                    profile_dir,
                    args.proxy_port,
                    args.netid.strip(),
                    os.environ["TRANSACT_PASSWORD"],
                    LOGIN_URL,
                    event_file,
                    event_before,
                )
            except RuntimeError as error:
                retain_flow_file = True
                print(f"Could not start headless Duke login: {error}", file=sys.stderr)
                print(f"Private mitm flow dump: {flow_file}", file=sys.stderr)
                return 1
        else:
            progress(f"Opening {args.browser} with a dedicated SSO profile...")
            progress("Complete Duke login/MFA in that browser window.")
            launch_browser(profile_dir, args.proxy_port, args.browser)

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if event_file.exists() and event_file.stat().st_mtime_ns > event_before:
                try:
                    event = json.loads(event_file.read_text(encoding="utf-8"))
                    temp_token = str(event.get("temp_token", ""))
                    if not temp_token:
                        raise RuntimeError("The SSO handoff did not include a temporary token.")
                    progress("Duke SSO completed; completing the Transact token exchange...")
                    complete_web_sso(temp_token, session_file, args.proxy_port)
                    event_file.unlink(missing_ok=True)
                    progress(f"Web session captured securely at {session_file}")
                    break
                except (
                    OSError,
                    json.JSONDecodeError,
                    HTTPError,
                    URLError,
                    TimeoutError,
                    RuntimeError,
                ) as error:
                    retain_flow_file = True
                    print(f"Could not complete the Transact SSO exchange: {error}", file=sys.stderr)
                    print(f"Private mitm flow dump: {flow_file}", file=sys.stderr)
                    return 1
            if mitm.poll() is not None:
                retain_flow_file = True
                print(f"{mitm_command} stopped. See {mitm_log}", file=sys.stderr)
                return 1
            time.sleep(0.5)
        else:
            retain_flow_file = True
            print("Timed out waiting for the Duke SSO handoff.", file=sys.stderr)
            print(f"Inspect the mitm log: {mitm_log}", file=sys.stderr)
            print(f"Private mitm flow dump: {flow_file}", file=sys.stderr)
            return 1

        check = run_checked(
            [
                sys.executable,
                str(SCRIPT_DIR / "check_transact_session.py"),
                "--session-file",
                str(session_file),
                "--output-dir",
                str(output_dir),
            ]
        )
        if check != 0:
            print("The captured web session did not pass validation.", file=sys.stderr)
            return check

        if args.fetch:
            return run_checked(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "fetch_fresh_menus.py"),
                    "--session-file",
                    str(session_file),
                    "--output-dir",
                    str(output_dir),
                ]
            )
        return 0
    finally:
        if mitm.poll() is None:
            mitm.terminate()
            try:
                mitm.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mitm.kill()
        if browser_context is not None:
            browser_context.close()
        if playwright_runtime is not None:
            playwright_runtime.stop()
        if not retain_flow_file:
            flow_file.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
