#!/usr/bin/env python3
"""
novapcb Phase 4f — gerber + drill + position-file + STEP + IPC-2581 export.

Runs `kicad-cli pcb export ...` for each fab-relevant artifact on the
routed board. Pre-staged per master Phase 4e dispatch ("prep 4f so it
fires immediately once Sai's routing lands").

Outputs land under `hardware/kicad/novapcb-layout/exports/` (gitignored
per `CLAUDE.md §5` — exports are generated, reproducible artifacts).

Usage:
    python3 run_gerber_export.py [--allow-incomplete]

Without --allow-incomplete, the script verifies 0 DRC errors before
exporting. With --allow-incomplete, it exports the current state (used
to test the pipeline against the 96%-routed pre-handoff board).
"""

import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PCB  = os.path.join(HERE, "novapcb-layout.kicad_pcb")
EXPORTS_DIR = os.path.join(HERE, "exports")
GERBERS_DIR = os.path.join(EXPORTS_DIR, "gerbers")
DRILL_DIR   = os.path.join(EXPORTS_DIR, "drill")

# Layers to plot per JLCPCB 4-layer convention
GERBER_LAYERS = ",".join([
    "F.Cu", "In1.Cu", "In2.Cu", "B.Cu",
    "F.Paste", "B.Paste",
    "F.Silkscreen", "B.Silkscreen",
    "F.Mask", "B.Mask",
    "Edge.Cuts",
])

ALLOW_INCOMPLETE = "--allow-incomplete" in sys.argv

# ---------- precheck: DRC ----------
print(f"[0/6] DRC precheck — require 0 errors before fab export")
drc_proc = subprocess.run(
    ["kicad-cli", "pcb", "drc", "--severity-error", "--exit-code-violations",
     "--units", "mm", PCB],
    capture_output=True, text=True,
)
drc_violations = "0 violations" in drc_proc.stdout
print(f"      DRC stdout tail: {drc_proc.stdout.strip().splitlines()[-1] if drc_proc.stdout.strip() else '(empty)'}")
if not drc_violations:
    if ALLOW_INCOMPLETE:
        print(f"      DRC reports issues — --allow-incomplete set, proceeding anyway")
    else:
        print(f"      !!! DRC has violations — refusing to export. Re-run with --allow-incomplete to override (NOT for fab).")
        sys.exit(2)
# cleanup DRC report file
drc_rpt = os.path.join(HERE, "novapcb-layout-drc.rpt")
if os.path.exists(drc_rpt):
    os.remove(drc_rpt)

os.makedirs(GERBERS_DIR, exist_ok=True)
os.makedirs(DRILL_DIR, exist_ok=True)

# ---------- 1. Gerbers ----------
print(f"[1/6] Gerbers → {GERBERS_DIR}")
subprocess.run([
    "kicad-cli", "pcb", "export", "gerbers",
    "--output", GERBERS_DIR,
    "--layers", GERBER_LAYERS,
    "--include-border-title",   # include title block for fab visibility
    "--no-protel-ext",          # use .gbr extension (modern Gerber)
    PCB,
], check=True)

# ---------- 2. Drill files (Excellon, mm) ----------
print(f"[2/6] Drill files → {DRILL_DIR}")
subprocess.run([
    "kicad-cli", "pcb", "export", "drill",
    "--output", DRILL_DIR + "/",
    "--format", "excellon",
    "--excellon-units", "mm",
    "--generate-map",            # plot map for fab visibility
    "--map-format", "pdf",
    PCB,
], check=True)

# ---------- 3. Position (pick-and-place) file ----------
print(f"[3/6] Pick-and-place position file")
subprocess.run([
    "kicad-cli", "pcb", "export", "pos",
    "--output", os.path.join(EXPORTS_DIR, "novapcb-layout.pos"),
    "--format", "csv",
    "--units", "mm",
    "--side", "both",   # both F.Cu + B.Cu (two-sided SMT per Phase 4b/4c)
    PCB,
], check=True)

# ---------- 4. STEP (3D mechanical) ----------
print(f"[4/6] STEP 3D model")
subprocess.run([
    "kicad-cli", "pcb", "export", "step",
    "--output", os.path.join(EXPORTS_DIR, "novapcb-layout.step"),
    "--subst-models",   # use 3D models from KiCad libs
    PCB,
], check=True)

# ---------- 5. IPC-2581 (machine-readable fab package) ----------
print(f"[5/6] IPC-2581 export")
subprocess.run([
    "kicad-cli", "pcb", "export", "ipc2581",
    "--output", os.path.join(EXPORTS_DIR, "novapcb-layout-ipc2581.zip"),
    "--compress",
    PCB,
], check=True)

# ---------- 6. Summary ----------
print(f"[6/6] Summary")
for path in sorted(os.listdir(EXPORTS_DIR)):
    full = os.path.join(EXPORTS_DIR, path)
    if os.path.isdir(full):
        contents = os.listdir(full)
        print(f"  {path}/ ({len(contents)} files)")
        for f in sorted(contents):
            sz = os.path.getsize(os.path.join(full, f))
            print(f"    {f}  ({sz} bytes)")
    else:
        sz = os.path.getsize(full)
        print(f"  {path}  ({sz} bytes)")

print("\nDone. Phase 4f exports ready under exports/.")
if drc_violations:
    print("DRC clean — these exports are FAB-READY (post-Phase-5 BOM + Phase-7 fab order).")
else:
    print("⚠ DRC had violations — these exports are NOT fab-ready; pipeline test only.")
