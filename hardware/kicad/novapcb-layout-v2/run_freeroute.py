#!/usr/bin/env python3
"""Step 5 routing — Freerouting on novapcb-layout-v2 80×60 6-layer.

Adapted from Phase 4d's run_freeroute.py (36×36/4-layer attempt that
hung at Pass #1). Different conditions:
  - 80×60 mm (5x the area of 36×36)
  - 6 layers vs 4
  - Power on dedicated planes (L2 GND, L3 +3V3, L4 +5V, L5 GND) →
    signal nets only auto-routed (~70 nets vs the 4d 80+ nets-incl-power)

Workflow:
  1. Load + report nets (signal vs plane-served)
  2. ExportSpecctraDSN
  3. Run Freerouting headless: java -jar freerouting.jar -de in.dsn -do out.ses -mt 4 -mp 100
  4. ImportSpecctraSES → save board
  5. Parse Freerouting log for completion %
  6. Report results
"""

import os
import sys
import time
import subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
DSN_PATH = os.path.join(HERE, "novapcb-layout-v2.dsn")
SES_PATH = os.path.join(HERE, "novapcb-layout-v2.ses")
LOG_PATH = os.path.join(HERE, "freerouting.log")
JAVA     = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
FREEROUTING_JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V", "+5V_BEC", "+5V_BEC_PROT", "VBAT"}

print(f"[1/6] load board: {PCB_PATH}")
brd = pcbnew.LoadBoard(PCB_PATH)
print(f"      footprints: {len(list(brd.GetFootprints()))}")
print(f"      zones: {len(list(brd.Zones()))}")
nets_raw = brd.GetNetsByName().asdict()
nets = {str(k): v for k, v in nets_raw.items()}
signal_nets = [n for n in nets if n and n not in PLANE_NETS]
plane_served = [n for n in nets if n in PLANE_NETS]
print(f"      total nets: {len(nets)}")
print(f"      plane-served nets ({len(plane_served)}): {', '.join(sorted(plane_served))}")
print(f"      signal nets to route ({len(signal_nets)}): first 10 = {sorted(signal_nets)[:10]}")

print(f"[2/6] export DSN: {DSN_PATH}")
if os.path.exists(DSN_PATH):
    os.remove(DSN_PATH)
ok = pcbnew.ExportSpecctraDSN(brd, DSN_PATH)
if not ok or not os.path.exists(DSN_PATH):
    print(f"      !!! ExportSpecctraDSN failed")
    sys.exit(2)
print(f"      DSN size: {os.path.getsize(DSN_PATH)} bytes")

print(f"[3/6] run Freerouting (-mp 100 -mt 4; expect 15-45 min on roomy 6-layer board)")
if os.path.exists(SES_PATH):
    os.remove(SES_PATH)
t0 = time.time()
cmd = [
    JAVA, "-Dgui.enabled=false",
    "-jar", FREEROUTING_JAR,
    "-de", DSN_PATH,
    "-do", SES_PATH,
    "-mt", "4",
    "-mp", "100",
]
print(f"      cmd: {' '.join(cmd)}")
with open(LOG_PATH, "w") as logf:
    try:
        result = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, timeout=5400)
        rc = result.returncode
    except subprocess.TimeoutExpired:
        print(f"      !! Freerouting timed out at 90 min — partial SES may exist")
        rc = -1
elapsed = time.time() - t0
print(f"      Freerouting returned {rc} in {elapsed:.0f}s ({elapsed/60:.1f}min)")
print(f"      log: {LOG_PATH} ({os.path.getsize(LOG_PATH)} bytes)")
if not os.path.exists(SES_PATH):
    print(f"      !!! SES file not produced — Freerouting failed entirely")
    # Still show last bit of log to diagnose
    with open(LOG_PATH) as f:
        print(f.read()[-2000:])
    sys.exit(3)
print(f"      SES size: {os.path.getsize(SES_PATH)} bytes")

print(f"[4/6] import SES → board")
ok = pcbnew.ImportSpecctraSES(brd, SES_PATH)
if not ok:
    print(f"      !!! ImportSpecctraSES returned False")
    sys.exit(4)

tracks = list(brd.GetTracks())
n_tracks = sum(1 for t in tracks if isinstance(t, pcbnew.PCB_TRACK)
               and not isinstance(t, pcbnew.PCB_VIA))
n_vias = sum(1 for t in tracks if isinstance(t, pcbnew.PCB_VIA))
print(f"      post-import tracks: {n_tracks}, vias: {n_vias}")

print(f"[5/6] save board")
pcbnew.SaveBoard(PCB_PATH, brd)
print(f"      out: {PCB_PATH} ({os.path.getsize(PCB_PATH)} bytes)")

print(f"[6/6] parse Freerouting log")
import re
with open(LOG_PATH) as f:
    log = f.read()
passes = re.findall(r"Pass #(\d+): (\d+) incompletes across (\d+) items", log)
if passes:
    last = passes[-1]
    n_inc = int(last[1]); n_items = int(last[2])
    pct = 100 - 100*n_inc/n_items if n_items > 0 else 0
    print(f"      last pass: Pass #{last[0]} — {n_inc} incompletes / {n_items} items ({pct:.1f}% complete)")
for line in log.splitlines()[-20:]:
    if any(k in line for k in ["error", "ERROR", "complete", "Complete", "finished", "Finished",
                                "all items", "Optimization"]):
        print(f"      log: {line[:200]}")
print(f"done. Run kicad-cli pcb drc on {PCB_PATH} to check DRC + unconnected.")
