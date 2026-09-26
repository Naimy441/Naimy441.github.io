#!/usr/bin/env python3
"""Refresh Mobile Order menus and reauthenticate only after an auth failure."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "outputs" / "mobile_order"
DEFAULT_SESSION_FILE = SCRIPT_DIR / ".transact-session.json"
DEFAULT_BLOB_PATH = "mobile-order/transact-session.json"


def _load_local_env() -> None:
    """Load simple .env values without overriding GitHub/real environment vars."""
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


def _run(command: list[str], env: dict[str, str] | None = None) -> int:
    return subprocess.run(command, cwd=PROJECT_DIR, env=env).returncode


def _blob_config() -> tuple[str, str, str] | None:
    token = os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip()
    store_id = os.environ.get("BLOB_STORE_ID", "").strip()
    if not token and not store_id:
        return None
    if not token or not store_id:
        raise RuntimeError(
            "Vercel Blob requires both BLOB_STORE_ID and BLOB_READ_WRITE_TOKEN."
        )
    return token, store_id, os.environ.get("TRANSACT_SESSION_BLOB_PATH", DEFAULT_BLOB_PATH)


def _blob_client(token: str):
    try:
        from vercel.blob import BlobClient
    except ImportError as error:
        raise RuntimeError(
            "Vercel Blob support requires the `vercel` Python package."
        ) from error
    return BlobClient(token=token)


def _download_blob_session(blob_config: tuple[str, str, str], session_file: Path) -> bool:
    token, _store_id, blob_path = blob_config
    try:
        from vercel.blob.errors import BlobNotFoundError
    except ImportError as error:
        raise RuntimeError(
            "The installed Vercel package does not include Blob error types."
        ) from error
    try:
        result = _blob_client(token).get(
            blob_path,
            access="private",
            use_cache=False,
        )
    except BlobNotFoundError:
        return False
    except Exception as error:
        raise RuntimeError(
            f"Could not read the private Vercel Blob session ({type(error).__name__})."
        ) from error
    if result is None or getattr(result, "status_code", 0) != 200:
        return False

    stream = getattr(result, "stream", None)
    if stream is None:
        raise RuntimeError("The private Vercel Blob session had no content.")
    contents = b"".join(stream)
    try:
        json.loads(contents.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("The private Vercel Blob session was not valid JSON.") from error

    session_file.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix="transact-session-", suffix=".json", dir=session_file.parent
    )
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "wb") as handle:
            handle.write(contents)
        os.replace(temporary_name, session_file)
        os.chmod(session_file, stat.S_IRUSR | stat.S_IWUSR)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return True


def _upload_blob_session(blob_config: tuple[str, str, str], session_file: Path) -> None:
    token, _store_id, blob_path = blob_config
    try:
        _blob_client(token).put(
            blob_path,
            session_file.read_bytes(),
            access="private",
            content_type="application/json",
            overwrite=True,
        )
    except Exception as error:
        raise RuntimeError(
            f"Could not update the private Vercel Blob session ({type(error).__name__})."
        ) from error


def _write_session_from_environment(session_file: Path, env: dict[str, str]) -> bool:
    values = {
        "login_token": env.get("TRANSACT_LOGIN_TOKEN", ""),
        "userid": env.get("TRANSACT_USER_ID", ""),
        "sessionid": env.get("TRANSACT_SESSION_ID", ""),
    }
    if not all(values.values()):
        return False
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(json.dumps(values) + "\n", encoding="utf-8")
    os.chmod(session_file, stat.S_IRUSR | stat.S_IWUSR)
    return True


def main() -> int:
    _load_local_env()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(os.environ.get("FRESH_MENU_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)))
    parser.add_argument("--session-file", type=Path, default=Path(os.environ.get("TRANSACT_SESSION_FILE", DEFAULT_SESSION_FILE)))
    parser.add_argument("--delay", type=float, default=0.1)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    session_file = args.session_file.expanduser().resolve()
    try:
        blob_config = _blob_config()
    except RuntimeError as error:
        print(f"[mobile-order] {error}", file=sys.stderr)
        return 2

    session_env = os.environ.copy()
    blob_loaded = False
    if blob_config is not None:
        try:
            blob_loaded = _download_blob_session(blob_config, session_file)
        except RuntimeError as error:
            print(f"[mobile-order] {error}", file=sys.stderr)
            return 2
        if blob_loaded:
            # The Blob is the source of truth when it exists; do not let older
            # GitHub session secrets override the downloaded file.
            for name in ("TRANSACT_LOGIN_TOKEN", "TRANSACT_USER_ID", "TRANSACT_SESSION_ID"):
                session_env.pop(name, None)
            print("[mobile-order] Loaded the saved session from private Vercel Blob.", flush=True)
        else:
            print("[mobile-order] No Blob session exists yet; using the configured local/session secrets.", flush=True)
    check_command = [
        sys.executable,
        str(SCRIPT_DIR / "check_transact_session.py"),
        "--session-file",
        str(session_file),
        "--output-dir",
        str(output_dir),
    ]
    fetch_command = [
        sys.executable,
        str(SCRIPT_DIR / "fetch_fresh_menus.py"),
        "--session-file",
        str(session_file),
        "--output-dir",
        str(output_dir),
        "--delay",
        str(args.delay),
    ]

    has_environment_session = all(
        session_env.get(name)
        for name in ("TRANSACT_LOGIN_TOKEN", "TRANSACT_USER_ID", "TRANSACT_SESSION_ID")
    )
    has_local_session = session_file.is_file()
    if blob_config is not None and not blob_loaded and not has_environment_session and not has_local_session:
        print("[mobile-order] No saved session exists yet; starting the initial login.", flush=True)
        check_result = 1
    else:
        print("[mobile-order] Checking the current Transact session...", flush=True)
        check_result = _run(check_command, env=session_env)
    if check_result not in {0, 1}:
        print(
            "[mobile-order] Session check failed for a non-authentication reason; "
            "not attempting a new login.",
            file=sys.stderr,
        )
        return check_result

    if check_result == 0:
        print("[mobile-order] Session is valid; fetching menus normally.", flush=True)
        if blob_config is not None and not blob_loaded:
            try:
                if _write_session_from_environment(session_file, session_env):
                    _upload_blob_session(blob_config, session_file)
                    print("[mobile-order] Seeded the private Vercel Blob session.", flush=True)
            except RuntimeError as error:
                print(f"[mobile-order] {error}", file=sys.stderr)
                return 2
        fetch_result = _run(fetch_command, env=session_env)
        if fetch_result != 3:
            return fetch_result
        print("[mobile-order] Session expired during fetch; starting reauthentication.", flush=True)
    else:
        print("[mobile-order] Session is expired; starting reauthentication.", flush=True)

    # Do not let stale TRANSACT_* secrets override the newly captured session
    # when recapture_web_session.py validates and fetches after login.
    recapture_env = session_env.copy()
    for name in ("TRANSACT_LOGIN_TOKEN", "TRANSACT_USER_ID", "TRANSACT_SESSION_ID"):
        recapture_env.pop(name, None)

    recapture_command = [
        sys.executable,
        str(SCRIPT_DIR / "recapture_web_session.py"),
        "--headless-login",
        "--fetch",
        "--session-file",
        str(session_file),
        "--output-dir",
        str(output_dir),
        "--timeout",
        str(args.timeout),
    ]
    recapture_result = _run(recapture_command, env=recapture_env)
    if recapture_result != 0 or blob_config is None:
        return recapture_result
    try:
        _upload_blob_session(blob_config, session_file)
        print("[mobile-order] Uploaded the refreshed session to private Vercel Blob.", flush=True)
    except RuntimeError as error:
        print(f"[mobile-order] {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
