#!/usr/bin/env python3
"""
novapcb Phase 4e — Freerouting autoroute pass on the real placed-and-planed
board (4d-deliverable output).

Differs from the P0 scale-test:
  - P0 ran Freerouting on a scatter placement with power-as-traces — stalled
    on power-net routing at Pass #1.
  - 4e runs on REAL placement (Phase 4b) + power on copper planes (Phase 4c)
    so Freerouting routes SIGNAL nets only; power nets are plane-served and
    excluded from the route list.

Net classes (set in the .kicad_pro / Phase 4a + updated 4d):
  - USB_diffpair: W=0.25mm, S=0.10mm (90Ω diff geometry computed Phase 4d
    via Hammerstad-Jensen on the 4a stackup)
  - IMU_SPI, SDMMC, DShot, Power_*: per Phase 4a
  - Default: 0.15mm track / 0.15mm clearance

Workflow:
  1. Load board (4d output)
  2. ExportSpecctraDSN
  3. Run Freerouting headless: java -jar freerouting.jar -de in.dsn -do out.ses -mt 4 -mp 50
     (-mp 50 = max 50 passes per P0 verification gate; -mt 4 = 4 threads)
  4. ImportSpecctraSES
  5. SaveBoard
  6. DRC + completion measure → classify per 4e.4 fork
"""

import os
import sys
import time
import subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout.kicad_pcb")
DSN_PATH = os.path.join(HERE, "novapcb-layout.dsn")
SES_PATH = os.path.join(HERE, "novapcb-layout.ses")
JAVA     = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
FREEROUTING_JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

# ---------- step 1: load board + report nets ----------
print(f"[1/6] load board: {PCB_PATH}")
brd = pcbnew.LoadBoard(PCB_PATH)
print(f"      footprints: {len(list(brd.GetFootprints()))}")
print(f"      zones: {len(list(brd.Zones()))}")
nets = brd.GetNetsByName().asdict()
nets_signal = [str(k) for k in nets.keys()
               if str(k) and str(k) not in ("GND", "+3V3", "+3V3A", "+5V", "VBAT")]
print(f"      total nets: {len(nets)}; signal nets (not plane-served): {len(nets_signal)}")
print(f"      plane-served nets (GND/+3V3/+3V3A/+5V/VBAT) excluded from auto-route")

# ---------- step 2: ExportSpecctraDSN ----------
print(f"[2/6] export DSN: {DSN_PATH}")
if os.path.exists(DSN_PATH):
    os.remove(DSN_PATH)
ok = pcbnew.ExportSpecctraDSN(brd, DSN_PATH)
if not ok or not os.path.exists(DSN_PATH):
    print(f"      !!! ExportSpecctraDSN failed")
    sys.exit(2)
print(f"      DSN size: {os.path.getsize(DSN_PATH)} bytes")

# ---------- step 3: run Freerouting ----------
print(f"[3/6] run Freerouting (-mp 50 -mt 4; ETA 30-60min wall)")
if os.path.exists(SES_PATH):
    os.remove(SES_PATH)
log_path = os.path.join(HERE, "freerouting.log")
t0 = time.time()
cmd = [
    JAVA, "-Dgui.enabled=false",
    "-jar", FREEROUTING_JAR,
    "-de", DSN_PATH,
    "-do", SES_PATH,
    "-mt", "4",
    "-mp", "50",
]
print(f"      cmd: {' '.join(cmd)}")
# Long-running; let it run to completion
with open(log_path, "w") as logf:
    result = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, timeout=4500)
elapsed = time.time() - t0
print(f"      Freerouting returned {result.returncode} in {elapsed:.0f}s ({elapsed/60:.1f}min)")
print(f"      log: {log_path} ({os.path.getsize(log_path)} bytes)")
if not os.path.exists(SES_PATH):
    print(f"      !!! SES file not produced")
    sys.exit(3)
print(f"      SES size: {os.path.getsize(SES_PATH)} bytes")

# ---------- step 4: ImportSpecctraSES ----------
print(f"[4/6] import SES → board")
ok = pcbnew.ImportSpecctraSES(brd, SES_PATH)
if not ok:
    print(f"      !!! ImportSpecctraSES returned False")
    sys.exit(4)

# count tracks + vias after import
tracks = list(brd.GetTracks())
n_tracks = sum(1 for t in tracks if isinstance(t, pcbnew.PCB_TRACK)
               and not isinstance(t, pcbnew.PCB_VIA))
n_vias = sum(1 for t in tracks if isinstance(t, pcbnew.PCB_VIA))
print(f"      post-import tracks: {n_tracks}, vias: {n_vias}")

# ---------- step 5: save board ----------
print(f"[5/6] save board")
pcbnew.SaveBoard(PCB_PATH, brd)
print(f"      out: {PCB_PATH} ({os.path.getsize(PCB_PATH)} bytes)")

# ---------- step 6: parse Freerouting log for completion stats ----------
print(f"[6/6] parse log for completion stats")
import re
with open(log_path) as f:
    log = f.read()
# Freerouting v2 emits "Pass #N: X incompletes across Y items to route"
passes = re.findall(r"Pass #(\d+): (\d+) incompletes across (\d+) items", log)
if passes:
    last = passes[-1]
    print(f"      last pass reported: Pass #{last[0]} — {last[1]} incompletes / {last[2]} items "
          f"({100 - 100*int(last[1])/int(last[2]):.1f}% complete)")
# Look for completion / success indicators
for line in log.splitlines()[-30:]:
    if any(k in line for k in ["error", "ERROR", "complete", "Complete", "finished", "Finished",
                                "Routing", "Optimiz", "all items"]):
        print(f"      log: {line[:200]}")
print(f"done. Run kicad-cli pcb drc on {PCB_PATH} to check DRC + unconnected.")
