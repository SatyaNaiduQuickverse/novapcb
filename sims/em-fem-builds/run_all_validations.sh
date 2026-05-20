#!/usr/bin/env bash
# Master validation runner — fires all 3 tool validations in sequence + reports.
# Run after all 3 builds complete.
set -uo pipefail

HERE=$(dirname "$(realpath "$0")")
LOG=/tmp/em-fem-validation.log
: > "$LOG"

PASS=0; FAIL=0
declare -a RESULTS

run_validate() {
  local name="$1" script="$2"
  echo "============================================================" | tee -a "$LOG"
  echo "[$name] running: $script" | tee -a "$LOG"
  echo "============================================================" | tee -a "$LOG"
  if bash -c "$script" 2>&1 | tee -a "$LOG"; then
    RESULTS+=("$name: PASS")
    PASS=$((PASS+1))
  else
    RESULTS+=("$name: FAIL")
    FAIL=$((FAIL+1))
  fi
  echo "" | tee -a "$LOG"
}

run_validate "elmer-nafems-T1"  "$HERE/validate_elmer_nafems.sh"
run_validate "openems-microstrip-HJ" "LD_LIBRARY_PATH=$HOME/local/openems/lib python3 $HERE/validate_openems_hammerstad.py"
run_validate "openems-notch-tutorial" "LD_LIBRARY_PATH=$HOME/local/openems/lib python3 $HOME/local/src/em-fem-builds/openEMS/python/Tutorials/MSL_NotchFilter.py"
run_validate "palace-spheres" "$HERE/validate_palace_spheres.sh"

echo "============================================================" | tee -a "$LOG"
echo "VALIDATION SUMMARY" | tee -a "$LOG"
echo "============================================================" | tee -a "$LOG"
printf '%s\n' "${RESULTS[@]}" | tee -a "$LOG"
echo "" | tee -a "$LOG"
echo "PASS: $PASS  FAIL: $FAIL" | tee -a "$LOG"
echo "Full log: $LOG" | tee -a "$LOG"
exit $FAIL
