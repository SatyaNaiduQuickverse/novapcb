#!/usr/bin/env python3
"""Step 6 Block D — gerber/drill/POS/STEP/BOM export for novapcb-layout-v2.

Adapted from hardware/kicad/novapcb-layout/run_gerber_export.py (4-layer
prior). Differences for the 6-layer JLC06161H board:
  - 6 signal/copper layers exported (F + In1..In4 + B) vs 4
  - Same paste/silk/mask/edge layers
  - Same drill format (Excellon, mm)
  - Same position file for SMT pick-and-place

Outputs go to hardware/kicad/novapcb-layout-v2/exports/ (gitignored).

Usage:
    python3 run_gerber_export.py [--allow-incomplete]

Without --allow-incomplete the script refuses to export if DRC has any
errors. Use --allow-incomplete for pipeline-testing while plane-stitch
GUI cleanup is pending (current state has 28 known unconnected items).
"""
import os, sys, subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
PCB = HERE / "novapcb-layout-v2.kicad_pcb"
EXPORTS = HERE / "exports"
GERBERS = EXPORTS / "gerbers"
DRILL = EXPORTS / "drill"

# 6-layer JLC: F.Cu, In1..In4, B.Cu + paste/silk/mask/edge
GERBER_LAYERS = ",".join([
    "F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu",
    "F.Paste", "B.Paste",
    "F.Silkscreen", "B.Silkscreen",
    "F.Mask", "B.Mask",
    "Edge.Cuts",
])

ALLOW_INCOMPLETE = "--allow-incomplete" in sys.argv


def main():
    # [0] DRC precheck
    print("[0/7] DRC precheck", flush=True)
    drc = subprocess.run(
        ["kicad-cli", "pcb", "drc", "--severity-error", "--exit-code-violations",
         "--units", "mm", str(PCB)],
        capture_output=True, text=True,
    )
    drc_clean = "0 violations" in drc.stdout
    last_line = drc.stdout.strip().splitlines()[-1] if drc.stdout.strip() else "(empty)"
    print(f"      DRC: {last_line}", flush=True)
    if not drc_clean:
        if ALLOW_INCOMPLETE:
            print(f"      DRC has issues; --allow-incomplete set, proceeding", flush=True)
        else:
            print(f"      !! DRC has errors. Re-run with --allow-incomplete for pipeline test.", flush=True)
            sys.exit(2)

    GERBERS.mkdir(parents=True, exist_ok=True)
    DRILL.mkdir(parents=True, exist_ok=True)

    # [1] Gerbers
    print(f"[1/7] Gerbers -> {GERBERS}", flush=True)
    subprocess.run([
        "kicad-cli", "pcb", "export", "gerbers",
        "--output", str(GERBERS) + "/",
        "--layers", GERBER_LAYERS,
        "--include-border-title",
        "--no-protel-ext",
        str(PCB),
    ], check=True)

    # [2] Drill
    print(f"[2/7] Drill -> {DRILL}", flush=True)
    subprocess.run([
        "kicad-cli", "pcb", "export", "drill",
        "--output", str(DRILL) + "/",
        "--format", "excellon",
        "--drill-origin", "absolute",
        "--excellon-units", "mm",
        "--excellon-zeros-format", "decimal",
        str(PCB),
    ], check=True)

    # [3] Position file (Pick-and-place — JLC format)
    print(f"[3/7] POS file", flush=True)
    pos_path = EXPORTS / "novapcb-layout-v2-pos.csv"
    subprocess.run([
        "kicad-cli", "pcb", "export", "pos",
        "--output", str(pos_path),
        "--format", "csv",
        "--units", "mm",
        "--use-drill-file-origin",
        str(PCB),
    ], check=True)
    if pos_path.exists():
        print(f"      pos: {pos_path.stat().st_size} bytes", flush=True)

    # [4] STEP (3D)
    print(f"[4/7] STEP", flush=True)
    step_path = EXPORTS / "novapcb-layout-v2.step"
    subprocess.run([
        "kicad-cli", "pcb", "export", "step",
        "--output", str(step_path),
        "--subst-models",
        str(PCB),
    ], capture_output=True)
    if step_path.exists():
        print(f"      step: {step_path.stat().st_size} bytes", flush=True)

    # [5] IPC-2581 (modern fab spec)
    print(f"[5/7] IPC-2581", flush=True)
    ipc_path = EXPORTS / "novapcb-layout-v2.xml"
    subprocess.run([
        "kicad-cli", "pcb", "export", "ipc2581",
        "--output", str(ipc_path),
        str(PCB),
    ], capture_output=True)
    if ipc_path.exists():
        print(f"      ipc2581: {ipc_path.stat().st_size} bytes", flush=True)

    # [6] Print summary of exported artifacts
    print(f"[6/7] Exported artifacts:", flush=True)
    for f in sorted(GERBERS.glob("*")):
        print(f"      gerber: {f.name} ({f.stat().st_size} bytes)", flush=True)
    for f in sorted(DRILL.glob("*")):
        print(f"      drill:  {f.name} ({f.stat().st_size} bytes)", flush=True)

    # [7] Manifest
    print(f"[7/7] Generate manifest", flush=True)
    manifest = EXPORTS / "MANIFEST.txt"
    artifacts = []
    for d in (GERBERS, DRILL):
        for f in sorted(d.glob("*")):
            artifacts.append(f"{f.relative_to(EXPORTS)} ({f.stat().st_size} B)")
    for f in (pos_path, step_path, ipc_path):
        if f.exists():
            artifacts.append(f"{f.name} ({f.stat().st_size} B)")
    manifest.write_text("novapcb-layout-v2 fab artifacts\n" + "="*40 + "\n" +
                        "\n".join(artifacts) + "\n")
    print(f"      manifest: {len(artifacts)} artifacts", flush=True)
    print(f"      MANIFEST.txt: {manifest}", flush=True)


if __name__ == "__main__":
    main()
