#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
MOBILE_ORDER_APP="${MOBILE_ORDER_APP:-/Applications/Mobile Order.app}"
MOBILE_ORDER_EXECUTABLE="$MOBILE_ORDER_APP/Wrapper/TRANSACT.app/Transact Prod"
SESSION_FILE="${TRANSACT_SESSION_FILE:-$SCRIPT_DIR/.transact-session.json}"
OUTPUT_DIR="${FRESH_MENU_OUTPUT_DIR:-$SCRIPT_DIR/../outputs/mobile_order}"
FETCH_DELAY="${TRANSACT_FETCH_DELAY:-0.1}"
MITM_LOG="/private/tmp/duke-halal-mitmdump.log"
MITM_PID=""

progress() {
  print "[$(date '+%H:%M:%S')] $*"
}

find_mobile_order_pid() {
  local pid
  pid="$(pgrep -f "$MOBILE_ORDER_EXECUTABLE" | head -n 1 || true)"
  if [[ -z "$pid" ]]; then
    pid="$(pgrep -x "Transact Prod" | head -n 1 || true)"
  fi
  print -r -- "$pid"
}

cleanup() {
  if [[ -n "$MITM_PID" ]] && kill -0 "$MITM_PID" 2>/dev/null; then
    kill "$MITM_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

run_fetch() {
  python3 "$SCRIPT_DIR/fetch_fresh_menus.py" \
    --session-file "$SESSION_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --delay "$FETCH_DELAY"
}

wait_for_new_session() {
  local capture_started_at="$1"
  local session_inode_before="$2"
  local session_mtime session_inode

  progress "Waiting for the newly captured session..."
  for attempt in {1..600}; do
    if [[ -f "$SESSION_FILE" ]]; then
      session_mtime="$(stat -f %m "$SESSION_FILE" 2>/dev/null || print 0)"
      session_inode="$(stat -f %i "$SESSION_FILE" 2>/dev/null || print 0)"
      if (( session_mtime >= capture_started_at )) && [[ "$session_inode" != "$session_inode_before" ]]; then
        return 0
      fi
    fi
    if (( attempt % 20 == 0 )); then
      progress "Still waiting for a menu request after login..."
    fi
    sleep 0.1
  done

  return 1
}

recapture_session() {
  progress "Starting the interactive session recapture flow..."

  if ! command -v mitmdump >/dev/null 2>&1; then
    print -u2 "mitmdump was not found. Install mitmproxy first."
    return 1
  fi
  if [[ ! -d "$MOBILE_ORDER_APP" ]]; then
    print -u2 "Mobile Order was not found at: $MOBILE_ORDER_APP"
    return 1
  fi
  if [[ ! -t 0 ]]; then
    print -u2 "The session expired, but this run has no interactive terminal for Duke SSO login."
    print -u2 "Run ./mobile_order/refresh_menus.sh from Terminal to recapture it."
    return 1
  fi

  progress "Opening Mobile Order..."
  open "$MOBILE_ORDER_APP"

  local mobile_order_pid=""
  if [[ $# -ge 1 ]] && [[ "$1" =~ '^[0-9]+$' ]]; then
    mobile_order_pid="$1"
    progress "Using the supplied Mobile Order PID $mobile_order_pid."
  else
    progress "Looking for the Mobile Order process..."
    for attempt in {1..120}; do
      mobile_order_pid="$(find_mobile_order_pid)"
      if [[ -n "$mobile_order_pid" ]]; then
        break
      fi
      sleep 0.25
    done
  fi
  if [[ -z "$mobile_order_pid" ]] || ! kill -0 "$mobile_order_pid" 2>/dev/null; then
    print -u2 "Could not find a running Mobile Order process."
    return 1
  fi
  progress "Mobile Order is running with PID $mobile_order_pid."

  umask 077
  local capture_started_at session_inode_before
  capture_started_at="$(date +%s)"
  session_inode_before="$(stat -f %i "$SESSION_FILE" 2>/dev/null || print 0)"
  export TRANSACT_SESSION_FILE="$SESSION_FILE"

  progress "Starting headless mitmdump capture..."
  mitmdump \
    --mode "local:$mobile_order_pid" \
    -s "$SCRIPT_DIR/capture_transact_session.py" \
    >"$MITM_LOG" 2>&1 &
  MITM_PID=$!

  progress "Waiting for the local capture redirector..."
  for attempt in {1..10}; do
    if ! kill -0 "$MITM_PID" 2>/dev/null; then
      print -u2 "mitmdump stopped during startup. Its log says:"
      sed -n '1,120p' "$MITM_LOG" >&2
      return 1
    fi
    sleep 0.1
  done

  progress "Complete the Duke SSO login in Mobile Order now."
  progress "If the app is already logged in, leave it open and press Return."
  read -r

  progress "Opening the first available restaurant..."
  if ! osascript "$SCRIPT_DIR/open_first_menu.applescript"; then
    print -u2 "Could not open a restaurant automatically after login."
    print -u2 "Grant Terminal Accessibility access in System Settings > Privacy & Security > Accessibility."
    return 1
  fi

  if ! wait_for_new_session "$capture_started_at" "$session_inode_before"; then
    print -u2 "No fresh session was captured after login."
    print -u2 "Reload a restaurant menu while mitmdump is running, then try again."
    return 1
  fi

  progress "New session captured."
  return 0
}

progress "Checking the current saved Transact credentials..."
check_status=0
python3 "$SCRIPT_DIR/check_transact_session.py" \
  --session-file "$SESSION_FILE" \
  --output-dir "$OUTPUT_DIR" || check_status=$?

if (( check_status == 0 )); then
  progress "Current session works; fetching fresh menus..."
  fetch_status=0
  run_fetch || fetch_status=$?
  if (( fetch_status == 0 )); then
    progress "Finished. Fresh menus are in $OUTPUT_DIR"
    exit 0
  fi
  if (( fetch_status != 3 )); then
    print -u2 "Menu fetch failed with exit code $fetch_status."
    exit "$fetch_status"
  fi
  progress "The session expired during fetching; recapture is required."
elif (( check_status == 1 )) || [[ ! -f "$SESSION_FILE" ]]; then
  progress "The current session is expired or missing; recapture is required."
else
  print -u2 "Could not check the current session; refusing to recapture automatically."
  exit "$check_status"
fi

if ! recapture_session "$@"; then
  exit 1
fi

progress "Fetching menus with the newly captured credentials..."
run_fetch
progress "Finished. Fresh menus are in $OUTPUT_DIR"
