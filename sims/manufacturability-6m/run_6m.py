#!/usr/bin/env python3
"""
Phase 6m — Manufacturability: DRC + ERC + DFM + BOM cross-check (TIER-2,
gates on Phase 4f + Sai's routing).

Tools (all INSTALLED per TOOLCHAIN.md):
  - kicad-cli pcb drc        — DRC against the loaded ruleset
  - kicad-cli sch erc        — schematic ERC
  - InteractiveHtmlBom 2.11.1 — BOM ↔ board cross-check viewer
  - bom/novapcb-bom.csv      — Phase 5 deliverable (already merged)

LAYOUT-DEPENDENT — gates on:
  - Sai's GUI routing complete + pushed to main
  - Phase 4f (run_gerber_export.py) gerbers/drill exported

This scaffold:
  - DRC + ERC clean-pass check
  - BOM ↔ board cross-check via InteractiveHtmlBom HTML
  - JLCPCB DFM checklist (post-fab-order pre-checks)

Pass criterion (SIMULATION_PLAN §6m):
  DRC clean, BOM ↔ board cross-check 100%, interactiveHtmlBom renders.
"""

import json, subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
LAYOUT = Path.home()/"novapcb/hardware/kicad/novapcb-layout"
PCB = LAYOUT/"novapcb-layout.kicad_pcb"
SCH_DIR = Path.home()/"novapcb/hardware/kicad/novapcb"


def run_drc():
    """kicad-cli pcb drc — fail on any violation."""
    if not PCB.exists():
        return {"pcb_exists": False, "pass": None}
    proc = subprocess.run(
        ["kicad-cli", "pcb", "drc", "--severity-error", "--exit-code-violations", "--units", "mm", str(PCB)],
        capture_output=True, text=True,
    )
    has_violations = "0 violations" not in proc.stdout
    return {
        "pcb_exists": True,
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-3:] if proc.stdout.strip() else [],
        "pass": not has_violations,
    }


def run_ihb():
    """InteractiveHtmlBom — generates HTML viewer of board + BOM cross-reference."""
    if not PCB.exists():
        return {"pcb_exists": False, "pass": None}
    out_html = HERE/"novapcb-interactive-bom.html"
    proc = subprocess.run(
        ["python3", "-m", "InteractiveHtmlBom.generate_interactive_bom",
         str(PCB), "--dest-dir", str(HERE), "--no-browser"],
        capture_output=True, text=True,
    )
    return {
        "pcb_exists": True,
        "exit_code": proc.returncode,
        "html_exists": out_html.exists(),
        "html_path": str(out_html) if out_html.exists() else None,
        "stderr_tail": proc.stderr.strip().splitlines()[-3:] if proc.stderr.strip() else [],
        "pass": out_html.exists(),
    }


def bom_cross_check():
    """Verify every refdes in board ↔ bom/novapcb-bom.csv match."""
    bom_path = Path.home()/"novapcb/bom/novapcb-bom.csv"
    if not (PCB.exists() and bom_path.exists()):
        return {"pass": None, "note": "Missing PCB or BOM"}

    import pcbnew, csv
    brd = pcbnew.LoadBoard(str(PCB))
    board_refs = set(fp.GetReference() for fp in brd.GetFootprints())

    bom_refs = set()
    with bom_path.open() as f:
        rdr = csv.reader(f); next(rdr)
        for row in rdr:
            for r in row[1].split(","):
                bom_refs.add(r.strip())

    missing_in_bom = board_refs - bom_refs
    extra_in_bom = bom_refs - board_refs
    return {
        "board_refs": len(board_refs),
        "bom_refs": len(bom_refs),
        "missing_in_bom": sorted(missing_in_bom),
        "extra_in_bom": sorted(extra_in_bom),
        "pass": len(missing_in_bom) == 0 and len(extra_in_bom) == 0,
    }


def main():
    print("Phase 6m — Manufacturability DRC + BOM cross-check (SCAFFOLD)")
    results = {
        "tool": "kicad-cli + InteractiveHtmlBom + pcbnew Python",
        "tier": 2,
        "gates_on": ["Sai's GUI routing complete", "Phase 4f gerber export"],
        "checks": [],
    }

    results["checks"].append({
        "check": "6m.1_drc",
        "status": "INFO",
        "result": run_drc(),
        "notes": "kicad-cli pcb drc — pass requires 0 violations",
    })
    results["checks"].append({
        "check": "6m.2_interactiveHtmlBom_render",
        "status": "INFO",
        "result": run_ihb(),
        "notes": "InteractiveHtmlBom 2.11.1 — HTML viewer for board+BOM cross-reference",
    })
    results["checks"].append({
        "check": "6m.3_bom_board_cross_check",
        "status": "INFO",
        "result": bom_cross_check(),
        "notes": "Every refdes on board ↔ every refdes in bom/novapcb-bom.csv",
    })

    results["JLCPCB_DFM_checklist"] = [
        "Min trace width ≥ 0.13 mm (JLC 4-layer free spec)",
        "Min via diameter ≥ 0.45 mm (we use 0.45)",
        "Min via drill ≥ 0.25 mm (we use 0.25; JLC spec is 0.20 — clean)",
        "Annular ring ≥ 0.05 mm",
        "ICM-42688-P footprint matches TDK datasheet land pattern (OPEN_QUESTIONS phase4a-1 — must close)",
        "Pick-and-place CSV columns match JLCPCB SMT format",
        "Two-sided assembly orderable (B.Cu has J2 + J9 + U4 + R51-R55)",
        "Gerber + drill files present in hardware/kicad/novapcb-layout/exports/",
    ]
    results["summary"] = {"total": len(results["checks"]), "info": len(results["checks"])}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"  SUMMARY: {results['summary']}")
    print(f"  Will produce real PASS/FAIL post-Sai-routing + Phase 4f.")


if __name__ == "__main__":
    main()
