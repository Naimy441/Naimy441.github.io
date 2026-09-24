#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
MOBILE_ORDER_APP="${MOBILE_ORDER_APP:-/Applications/Mobile Order.app}"
MOBILE_ORDER_EXECUTABLE="$MOBILE_ORDER_APP/Wrapper/TRANSACT.app/Transact Prod"
SESSION_FILE="${TRANSACT_SESSION_FILE:-$SCRIPT_DIR/.transact-session.json}"
OUTPUT_DIR="${FRESH_MENU_OUTPUT_DIR:-$SCRIPT_DIR}"
FETCH_DELAY="${TRANSACT_FETCH_DELAY:-0.1}"
MITM_LOG="/private/tmp/duke-halal-mitmdump.log"

progress() {
  print "[$(date '+%H:%M:%S')] $*"
}

progress "Checking Mobile Order and mitmdump setup..."

if ! command -v mitmdump >/dev/null 2>&1; then
  print -u2 "mitmdump was not found. Install mitmproxy first."
  exit 1
fi

if [[ ! -d "$MOBILE_ORDER_APP" ]]; then
  print -u2 "Mobile Order was not found at: $MOBILE_ORDER_APP"
  print -u2 "Set MOBILE_ORDER_APP to its installed location and try again."
  exit 1
fi

find_mobile_order_pid() {
  local pid
  pid="$(pgrep -f "$MOBILE_ORDER_EXECUTABLE" | head -n 1 || true)"
  if [[ -z "$pid" ]]; then
    pid="$(pgrep -x "Transact Prod" | head -n 1 || true)"
  fi
  print -r -- "$pid"
}

progress "Opening Mobile Order..."
open "$MOBILE_ORDER_APP"

if [[ $# -ge 1 ]]; then
  MOBILE_ORDER_PID="$1"
  progress "Using supplied Mobile Order PID $MOBILE_ORDER_PID."
else
  MOBILE_ORDER_PID=""
  progress "Looking for the Mobile Order process..."
  for attempt in {1..120}; do
    MOBILE_ORDER_PID="$(find_mobile_order_pid)"
    if [[ -n "$MOBILE_ORDER_PID" ]]; then
      break
    fi
    sleep 0.25
  done
fi

if [[ -z "$MOBILE_ORDER_PID" ]] || ! kill -0 "$MOBILE_ORDER_PID" 2>/dev/null; then
  print -u2 "Could not find a running Mobile Order process."
  print -u2 "Usage: $0 [mobile-order-pid]"
  exit 1
fi
progress "Mobile Order is running with PID $MOBILE_ORDER_PID."

umask 077
capture_started_at="$(date +%s)"
session_inode_before="$(stat -f %i "$SESSION_FILE" 2>/dev/null || print 0)"
export TRANSACT_SESSION_FILE="$SESSION_FILE"

progress "Starting headless mitmdump capture..."
mitmdump \
  --mode "local:$MOBILE_ORDER_PID" \
  -s "$SCRIPT_DIR/capture_transact_session.py" \
  >"$MITM_LOG" 2>&1 &
MITM_PID=$!

cleanup() {
  if kill -0 "$MITM_PID" 2>/dev/null; then
    kill "$MITM_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

progress "Waiting for the local capture redirector..."
for attempt in {1..10}; do
  if ! kill -0 "$MITM_PID" 2>/dev/null; then
    print -u2 "mitmdump stopped during startup. Its log says:"
    sed -n '1,120p' "$MITM_LOG" >&2
    exit 1
  fi
  if (( attempt == 1 )); then
    progress "mitmdump process is running; allowing the local redirector to initialize..."
  fi
  sleep 0.1
done

progress "Headless capture is ready; no dashboard is needed."
progress "Opening the first available restaurant in Mobile Order..."

if ! osascript "$SCRIPT_DIR/open_first_menu.applescript"; then
  print -u2 "Could not open a restaurant automatically."
  print -u2 "Grant Terminal Accessibility access in System Settings > Privacy & Security > Accessibility, then try again."
  exit 1
fi

progress "Restaurant opened. Waiting for the menu session to be captured..."

session_ready=0
for attempt in {1..600}; do
  if [[ -f "$SESSION_FILE" ]]; then
    session_mtime="$(stat -f %m "$SESSION_FILE" 2>/dev/null || print 0)"
    session_inode="$(stat -f %i "$SESSION_FILE" 2>/dev/null || print 0)"
    if (( session_mtime >= capture_started_at )) && [[ "$session_inode" != "$session_inode_before" ]]; then
      session_ready=1
      break
    fi
  fi
  if (( attempt % 20 == 0 )); then
    progress "Still waiting for the captured session..."
  fi
  sleep 0.1
done

if (( session_ready == 0 )); then
  print -u2 "No fresh captured session was found at $SESSION_FILE."
  print -u2 "The automatic restaurant click may have failed or the menu request did not reach mitmdump."
  exit 1
fi

progress "Session captured. Fetching fresh menus..."
python3 "$SCRIPT_DIR/fetch_fresh_menus.py" \
  --session-file "$SESSION_FILE" \
  --output-dir "$OUTPUT_DIR" \
  --delay "$FETCH_DELAY"

progress "Finished. Fresh menus are in $OUTPUT_DIR"
