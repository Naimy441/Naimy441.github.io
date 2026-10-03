#!/usr/bin/env bash
# Refreshes the halal catalog end to end without a browser:
#   1. netnutrition_client.py -> outputs/netnutrition-direct.json (every item, not only halal)
#   2. update_nutrition_library.py -> outputs/nutrition_library/ (labels accumulated across runs, for Nutriuni)
#   3. build_catalog_outputs.py -> halal menu text/PDF + per-restaurant nutrition files
#   4. extract-nutrition -> dukeislam/data/nutrition.json (the catalog the website bundles)
#
# Requires: python3 with requirements.txt installed and node.
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

CA_ARGS=()
if [[ -n "${NETNUTRITION_CA_BUNDLE:-}" ]]; then
  CA_ARGS=(--ca-bundle "$NETNUTRITION_CA_BUNDLE")
fi

echo "Refreshing halal catalog with direct NetNutrition requests (logs in $LOG_DIR)"
# The crawl keeps every item: Nutriuni needs non-halal labels too, and
# build_catalog_outputs.py filters to halal items itself.
run_step 1 "Direct menu + nutrition fetch" netnutrition_client \
  python3 src/netnutrition_client.py --nutrition --output outputs/netnutrition-direct.json \
  "${CA_ARGS[@]}"
run_step 2 "Update nutrition library" update_nutrition_library \
  python3 src/update_nutrition_library.py --input outputs/netnutrition-direct.json
run_step 3 "Build menu + nutrition artifacts" build_catalog_outputs \
  python3 src/build_catalog_outputs.py --input outputs/netnutrition-direct.json \
  "${CA_ARGS[@]}"
run_step 4 "Rebuild website catalog" extract_nutrition node dukeislam/scripts/extract-nutrition.mjs

echo
echo "All done in $(fmt_time $((SECONDS - RUN_START)))."
echo "Run 'git status' to review, then commit and push to update the site."
