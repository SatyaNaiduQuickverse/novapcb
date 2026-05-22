#!/usr/bin/env python3
"""Gate 14 — KiCad DRC on the on-board area.

Per docs/PLACEMENT_ROUTING_GATES.md §Gate 14 (added 2026-05-22 after
#67 process miss): every PR touching .kicad_pcb must run KiCad DRC and
show 0 "real" on-board violations. unconnected_items for unrouted power
nets are accepted but listed.

Run: python3 gate14_drc.py
Exit 0 if Gate 14 GREEN, 1 otherwise.
"""
import os
import re
import sys
import subprocess
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
DRC_TXT = "/tmp/_gate14_drc.txt"
ON_BOARD_MAX = 100.0   # mm — parked footprints are at X >= 110


def main():
    r = subprocess.run([
        "kicad-cli", "pcb", "drc",
        "--severity-error", "--format", "report",
        "--output", DRC_TXT, "--units", "mm", PCB,
    ], capture_output=True, text=True)
    if r.returncode != 0 and not os.path.exists(DRC_TXT):
        print("kicad-cli failed:", r.stderr); return 2

    with open(DRC_TXT) as f: lines = f.readlines()
    blocks, cur = [], []
    for ln in lines:
        if ln.startswith("["):
            if cur: blocks.append(cur)
            cur = [ln]
        elif cur: cur.append(ln)
    if cur: blocks.append(cur)

    on_board = []
    for b in blocks:
        text = "".join(b)
        coords = re.findall(r'@\(([\d.-]+) mm,\s*([\d.-]+) mm', text)
        if not coords:
            continue
        if all(abs(float(x)) < ON_BOARD_MAX and abs(float(y)) < ON_BOARD_MAX
               for x, y in coords):
            on_board.append((b[0].strip(), text))

    uc = [v for v in on_board if "unconnected" in v[0]]
    real = [v for v in on_board if "unconnected" not in v[0]]

    print(f"=== Gate 14 — KiCad DRC ===\n")
    print(f"On-board violations: {len(on_board)}", flush=True)
    print(f"  Unconnected items (expected for unrouted power nets): {len(uc)}")
    print(f"  REAL violations (must be 0): {len(real)}")
    cats = Counter(v[0].split(":")[0].strip() for v in real)
    if cats:
        print(f"  By type: {dict(cats)}")
        print(f"\nSample real violations:")
        for v in real[:5]:
            txt = " ".join(l.strip() for l in v[1].split("\n"))
            print(f"  {txt[:180]}")

    if uc:
        # List the unique nets that have unconnected items
        nets = set()
        for v in uc:
            m = re.search(r'\[([+\w]+)\]', v[1])
            if m: nets.add(m.group(1))
        print(f"\nUnconnected nets (verify these are power/deferred):")
        for n in sorted(nets)[:20]:
            print(f"  {n}")

    ok = (len(real) == 0)
    print(f"\nGate 14: {'GREEN' if ok else 'RED'}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
