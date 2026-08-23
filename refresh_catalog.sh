#!/usr/bin/env bash
# Refreshes the full halal catalog end to end:
#   1. full_scrape.py    -> outputs/all_menus.txt + all_menus.pdf (every item, halal-flagged)
#   2. nutri_scrape.py   -> outputs/nutri_menus.json (nutrition label for every item; SLOW)
#   3. nutri_split.py    -> outputs/restaurants/*.json + index + summary stats
#   4. extract-nutrition -> dukeislam/data/nutrition.json (the catalog the website bundles)
#
# Requires: python3 with requirements.txt installed, Chrome, node.
# Full logs for each step are written to outputs/logs/.
# Afterwards, review with `git status`, then commit and push to update the site.
set -euo pipefail
cd "$(dirname "$0")"

TOTAL_STEPS=4
LOG_DIR="outputs/logs/refresh_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
RUN_START=$SECONDS

fmt_time() {
  printf '%02d:%02d:%02d' $(($1 / 3600)) $((($1 % 3600) / 60)) $(($1 % 60))
}

step_bar() { # filled boxes for completed steps, e.g. [██░░]
  local done="$1" bar="" i
  for ((i = 1; i <= TOTAL_STEPS; i++)); do
    if ((i <= done)); then bar+="█"; else bar+="░"; fi
  done
  printf '%s' "$bar"
}

SPINNER=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')

run_step() {
  local num="$1" title="$2" logname="$3"
  shift 3
  local log="$LOG_DIR/$logname.log"
  local start=$SECONDS
  local i=0 elapsed last rc

  "$@" >"$log" 2>&1 &
  local pid=$!

  while kill -0 "$pid" 2>/dev/null; do
    i=$(((i + 1) % ${#SPINNER[@]}))
    elapsed=$((SECONDS - start))
    last=$(tail -n 1 "$log" 2>/dev/null | tr -d '\r' | cut -c 1-60)
    printf '\r\033[K[%s] %d/%d %s \033[36m%s\033[0m %s  \033[2m%s\033[0m' \
      "$(step_bar $((num - 1)))" "$num" "$TOTAL_STEPS" "$title" \
      "${SPINNER[$i]}" "$(fmt_time $elapsed)" "$last"
    sleep 0.12
  done

  rc=0
  wait "$pid" || rc=$?
  elapsed=$((SECONDS - start))

  if ((rc == 0)); then
    printf '\r\033[K[%s] %d/%d %s \033[32m✓\033[0m done in %s\n' \
      "$(step_bar "$num")" "$num" "$TOTAL_STEPS" "$title" "$(fmt_time $elapsed)"
  else
    printf '\r\033[K[%s] %d/%d %s \033[31m✗ FAILED\033[0m after %s (exit %d)\n' \
      "$(step_bar $((num - 1)))" "$num" "$TOTAL_STEPS" "$title" "$(fmt_time $elapsed)" "$rc"
    echo "--- last 20 lines of $log ---"
    tail -n 20 "$log"
    exit "$rc"
  fi
}

echo "Refreshing halal catalog (logs in $LOG_DIR)"
run_step 1 "Full menu scrape" full_scrape python3 src/full_scrape.py
run_step 2 "Nutrition scrape (slow)" nutri_scrape python3 src/nutri_scrape.py
run_step 3 "Split per-restaurant files" nutri_split python3 src/nutri_split.py
run_step 4 "Rebuild website catalog" extract_nutrition node dukeislam/scripts/extract-nutrition.mjs

echo
echo "All done in $(fmt_time $((SECONDS - RUN_START)))."
echo "Run 'git status' to review, then commit and push to update the site."
