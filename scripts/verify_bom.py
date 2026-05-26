#!/usr/bin/env python3
"""BOM verification — cross-check bom/novapcb-bom.csv against the live board.

Phase 7a freeze-gate item ("BOM final verify"). This is a LOCAL completeness +
staleness check — it does NOT do live LCSC stock/price lookups (that's Sai's
JLCPCB-portal step at fab order). It verifies:

  1. Every board footprint reference appears in the BOM (and vice-versa).
  2. Every BOM line has LCSC_Part + JLCPCB_Type (Basic/Extended) populated.
  3. Reports Basic vs Extended split (assembly-cost signal).
  4. Flags known staleness (the BOM/sourcing notes predate the 6-layer pivot).

Usage: python3 scripts/verify_bom.py
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOM = ROOT / "bom" / "novapcb-bom.csv"
PCB = ROOT / "hardware" / "kicad" / "novapcb-stepwise" / "novapcb-stepwise.kicad_pcb"

# refs that are mechanical / fiducial / test and not assembled BOM parts
NON_BOM_PREFIX = ("TP", "FID", "MK")


def board_refs():
    """ref -> (value, footprint) for every footprint on the board."""
    import pcbnew
    b = pcbnew.LoadBoard(str(PCB))
    out = {}
    for fp in b.GetFootprints():
        out[fp.GetReference()] = (fp.GetValue(),
                                  fp.GetFPIDAsString().split(":")[-1])
    return out


def bom_rows():
    return list(csv.DictReader(open(BOM)))


def expand_refdes(s):
    """'C11,C12,C13' or 'C11-C13' -> [C11,C12,C13]."""
    out = []
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        m = re.match(r"([A-Za-z]+)(\d+)-([A-Za-z]+)?(\d+)$", tok)
        if m:
            pre, a, _pre2, b = m.groups()
            out += [f"{pre}{i}" for i in range(int(a), int(b) + 1)]
        else:
            out.append(tok)
    return out


def main():
    brd = board_refs()
    rows = bom_rows()

    bom_ref_to_line = {}
    for i, r in enumerate(rows, 1):
        for ref in expand_refdes(r["RefDes"]):
            bom_ref_to_line[ref] = r

    brd_set = set(brd)
    bom_set = set(bom_ref_to_line)

    on_board_not_bom = sorted(brd_set - bom_set)
    in_bom_not_board = sorted(bom_set - brd_set)

    # exclude non-BOM mechanical/test refs from the "missing from BOM" fault list
    missing_real = [r for r in on_board_not_bom
                    if not r.startswith(NON_BOM_PREFIX)]
    missing_nonbom = [r for r in on_board_not_bom
                      if r.startswith(NON_BOM_PREFIX)]

    print("=== BOM vs live board ===")
    print(f"  board footprints:        {len(brd_set)}")
    print(f"  BOM-covered refs:        {len(bom_set)}")
    print(f"  on board, NOT in BOM:    {len(on_board_not_bom)} "
          f"({len(missing_real)} real parts + {len(missing_nonbom)} TP/mech)")
    if missing_real:
        print("    REAL parts missing from BOM (added since BOM date):")
        for r in missing_real:
            print(f"      {r:6} {brd[r][0]:24} {brd[r][1]}")
    if missing_nonbom:
        print(f"    TP/mech (not assembled, OK to omit): {missing_nonbom}")
    print(f"  in BOM, NOT on board:    {len(in_bom_not_board)}")
    for r in in_bom_not_board:
        print(f"      {r:6} (removed from board since BOM) — {bom_ref_to_line[r]['Value']}")

    # LCSC / JLCPCB-type completeness. A blank OR a "TBD*" placeholder both count
    # as unsourced (the latter is an explicit Sai-source flag, not a real part #).
    def unsourced(v):
        v = v.strip().lower()
        return (not v) or v.startswith("tbd")
    no_lcsc = [r for r in rows if unsourced(r.get("LCSC_Part", ""))]
    no_type = [r for r in rows if unsourced(r.get("JLCPCB_Type", ""))]
    basic = sum(1 for r in rows if r.get("JLCPCB_Type", "").strip().lower() == "basic")
    ext = sum(1 for r in rows if r.get("JLCPCB_Type", "").strip().lower() == "extended")
    print("\n=== BOM line completeness ===")
    print(f"  line items:              {len(rows)}")
    print(f"  unsourced LCSC (blank/TBD): {len(no_lcsc)}"
          + (f"  -> {[r['RefDes'][:14] for r in no_lcsc]}" if no_lcsc else ""))
    print(f"  unsourced JLCPCB_Type:   {len(no_type)} (Sai confirms basic/extended at order)")
    print(f"  Basic / Extended split:  {basic} basic / {ext} extended "
          f"(extended parts add per-type assembly fee + reel setup)")

    print("\n=== Known staleness (must refresh before freeze) ===")
    notes = (ROOT / "bom" / "SOURCING_NOTES.md").read_text()
    stale = []
    # Stale only if the OLD value appears WITHOUT the corrected value present
    # (a historical "was 4-layer, now 6-layer" note is fine — not stale).
    if "4-layer" in notes and "6-layer" not in notes:
        stale.append("SOURCING_NOTES says '4-layer' — design is now 6-layer JLC06161H")
    if (("36×36" in notes or "36x36" in notes or "36 × 36" in notes)
            and "105×85" not in notes and "105x85" not in notes):
        stale.append("SOURCING_NOTES says ~36×36mm — board is now 105×85mm")
    for s in stale:
        print(f"  ⚠ {s}")
    if not stale:
        print("  (sourcing notes dimensions/stackup look current)")

    faults = len(missing_real) + len(in_bom_not_board) + len(no_lcsc) + len(no_type)
    print("\n=== Verdict ===")
    if faults == 0 and not stale:
        print("  PASS — BOM matches board, all parts sourced, notes current.")
        return 0
    print(f"  NOT-READY — {len(missing_real)} parts missing from BOM, "
          f"{len(in_bom_not_board)} stale BOM rows, {len(no_lcsc)} unsourced, "
          f"{len(stale)} stale-notes flags. Refresh BOM + SOURCING_NOTES before freeze.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
