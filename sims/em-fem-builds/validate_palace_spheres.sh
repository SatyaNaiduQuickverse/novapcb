#!/usr/bin/env bash
# Palace validation — two-sphere capacitance matrix (bundled example).
#
# Reference: Palace project docs (palace/docs/src/examples/spheres.md, AWS Labs 2024+).
# Analytical: Smythe W.R., "Static and Dynamic Electricity" 3rd ed., McGraw-Hill 1968,
# infinite-series solution for two-sphere capacitance.
# Palace's own published numerical reference: palace/test/examples/ref/spheres/terminal-C.csv
#   C[0][0] = +1.237445610357e-12 F
#   C[0][1] = -4.770975738888e-13 F (= C[1][0])
#   C[1][1] = +2.478413459856e-12 F
#
# Geometry (from spheres.json): a=1cm, b=2cm, c=5cm, vacuum.
# Tolerance: ±5% on each matrix entry.
set -euo pipefail

PALACE_BIN=~/local/palace/bin/palace
EXAMPLE=~/local/src/em-fem-builds/palace/examples/spheres
WORK=/tmp/palace_validate_spheres
mkdir -p "$WORK"
cp -r "$EXAMPLE"/* "$WORK/"
cd "$WORK"

if [ ! -x "$PALACE_BIN" ]; then
  echo "[palace-validate] FAIL — palace binary not found at $PALACE_BIN"
  exit 2
fi

# Adjust the JSON to write results into $WORK/postpro
python3 -c "
import json
with open('spheres.json') as f: cfg = json.load(f)
cfg.setdefault('Problem', {})['Output'] = '$WORK/postpro'
with open('spheres.json','w') as f: json.dump(cfg, f, indent=2)
"

echo "[palace-validate] running Palace on spheres example (~5-15 min on Pi 5)"
T0=$(date +%s.%N)
"$PALACE_BIN" -np 1 spheres.json > palace.log 2>&1
ELAPSED=$(echo "$(date +%s.%N) - $T0" | bc 2>/dev/null || echo "?")
echo "[palace-validate] runtime: ${ELAPSED}s"

# Parse the output terminal-C.csv
RESULT="$WORK/postpro/terminal-C.csv"
if [ ! -f "$RESULT" ]; then
  echo "[palace-validate] FAIL — no terminal-C.csv produced"
  tail -20 palace.log
  exit 1
fi

python3 - <<'PYEOF'
import csv, sys

REFS = {
    (0, 0): +1.237445610357e-12,
    (0, 1): -4.770975738888e-13,
    (1, 0): -4.770975738888e-13,
    (1, 1): +2.478413459856e-12,
}
TOL_PCT = 5.0

with open('/tmp/palace_validate_spheres/postpro/terminal-C.csv') as f:
    rdr = csv.reader(f)
    header = next(rdr)
    rows = list(rdr)

# Last row is the converged value; rows are by iteration "i".
# CSV format: i, C[i][1] (F), C[i][2] (F) — repeated for each terminal row
# Palace writes the full matrix as 2 rows in the final block.
final = rows[-2:]  # last 2 rows = 2 terminals' capacitance to each other
print(f"\n[palace-validate] RESULT — two-sphere capacitance matrix")
print(f"  Reference (Palace docs spheres.md + test/examples/ref/spheres/terminal-C.csv;")
print(f"             analytical via Smythe 'Static and Dynamic Electricity' 1968):")
for (i, j), v in REFS.items(): print(f"      C[{i}][{j}] = {v:+.4e} F")

print(f"  Palace computed:")
all_pass = True
for row_idx, row in enumerate(final):
    # row[0] = terminal index (1-based), row[1] = C[i][1], row[2] = C[i][2]
    i = int(float(row[0])) - 1
    for j, v_str in enumerate(row[1:]):
        v = float(v_str)
        ref = REFS.get((i, j))
        if ref is None: continue
        err_pct = abs(v - ref) / abs(ref) * 100
        status = "PASS" if err_pct <= TOL_PCT else "FAIL"
        if status == "FAIL": all_pass = False
        print(f"      C[{i}][{j}] = {v:+.4e} F  (err {err_pct:.2f}%)  → {status}")

print(f"\n  Tolerance: ±{TOL_PCT}%  Overall: {'PASS' if all_pass else 'FAIL'}")
sys.exit(0 if all_pass else 1)
PYEOF
