#!/usr/bin/env python3
"""Gate 3 — component uniqueness check.

Per docs/PLACEMENT_ROUTING_GATES.md §Gate 3:

  "Every component in the SKiDL netlist must appear in .kicad_pcb
   exactly once, at a unique position (no two footprints at the same
   coords, no missing refdes from the netlist). This counters the
   kinet2pcb silent-drop trap."

Step 1 scope: this PR places C; the other subsystems' components are
PARKED off-board at X >= 110 mm. The Gate-3 check still applies — every
netlist refdes (whether on-board or parked) must be present, and no
refdes may be duplicated. Mounting holes H1..H4 are board mechanicals
added by step1_place_C.py and are EXPECTED not to be in the netlist.

Exit code 0 = match, 1 = mismatch.
"""
import os
import sys
import re
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
NETLIST = os.path.join(ROOT, "hardware", "kicad", "novapcb", "novapcb.net")
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
MOUNTING_REFS = {"H1", "H2", "H3", "H4"}


def netlist_refs(path: str) -> set:
    """Extract every component refdes from the SKiDL netlist (.net).
    Excludes SKiDL power-flag pseudo-components (#FLG_*) which carry no
    footprint — they are netlist annotations only."""
    refs = set()
    with open(path) as f:
        txt = f.read()
    for m in re.finditer(r'\(comp\s+\(ref\s+"?([^")\s]+)"?\)', txt):
        r = m.group(1)
        if r.startswith("#FLG") or r.startswith("#PWR"):
            continue   # SKiDL pseudo-comp; not a real footprint
        refs.add(r)
    return refs


def pcb_refs(path: str) -> list:
    """Return list of (ref, x_mm, y_mm) for every footprint."""
    brd = pcbnew.LoadBoard(path)
    out = []
    for fp in brd.GetFootprints():
        p = fp.GetPosition()
        out.append((fp.GetReference(), p.x / 1e6, p.y / 1e6))
    return out


def main():
    print("=== Gate 3 — component uniqueness ===\n", flush=True)

    netlist = netlist_refs(NETLIST)
    pcb_list = pcb_refs(PCB)
    pcb_set = {r for r, _, _ in pcb_list}

    # Missing: in netlist but not in PCB
    missing = sorted(netlist - pcb_set)
    # Extras: in PCB but not in netlist (mounting holes expected)
    extras_all = sorted(pcb_set - netlist)
    extras_unexpected = sorted(set(extras_all) - MOUNTING_REFS)
    extras_expected = sorted(set(extras_all) & MOUNTING_REFS)

    # Duplicates by refdes
    from collections import Counter
    ref_counts = Counter(r for r, _, _ in pcb_list)
    dup_refs = sorted(r for r, c in ref_counts.items() if c > 1)

    # Same-coord duplicates (different ref, identical position)
    from collections import defaultdict
    by_pos = defaultdict(list)
    for r, x, y in pcb_list:
        key = (round(x, 3), round(y, 3))
        by_pos[key].append(r)
    coloc = sorted([(k, v) for k, v in by_pos.items() if len(v) > 1])

    print(f"netlist refs: {len(netlist)}", flush=True)
    print(f"pcb refs: {len(pcb_set)} unique, {len(pcb_list)} total footprints", flush=True)
    print(f"missing (netlist -> pcb): {len(missing)}  {missing if missing else ''}", flush=True)
    print(f"unexpected extras (pcb -> netlist, NOT in {sorted(MOUNTING_REFS)}): "
          f"{len(extras_unexpected)}  {extras_unexpected if extras_unexpected else ''}", flush=True)
    print(f"expected mounting-hole extras: {extras_expected}", flush=True)
    print(f"duplicate refs in pcb: {len(dup_refs)}  {dup_refs if dup_refs else ''}", flush=True)
    print(f"colocated (different ref, same coord): {len(coloc)}", flush=True)
    if coloc:
        for k, refs in coloc[:5]:
            print(f"    at ({k[0]:.2f}, {k[1]:.2f}): {refs}", flush=True)

    ok = (not missing and not extras_unexpected and not dup_refs and not coloc)
    print(f"\n  Gate 3: {'GREEN' if ok else 'FAIL'}.", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
