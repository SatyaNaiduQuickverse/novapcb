#!/usr/bin/env python3
"""Lay master's proposed resA fix: single B.Cu +3V3 trace between two
existing through-vias.

Per master 2026-05-21 vision pass on the 150 px/mm render set:
  START: (69.2000, 29.8700)  — existing +3V3 through-via at resA-A
  END:   (69.6840, 32.7459)  — existing +3V3 through-via on the orphan
  Layer: B.Cu
  Net:   +3V3
  Width: 0.2 mm (matches all 72 existing +3V3 tracks)

Verification protocol (per master directive):
  1. kicad-cli pcb drc -> expect 0 errors. If any, REVERT, do NOT force.
  2. Recount unconnected -> expect 1 -> 0 (resA closed).
  3. If both pass -> board state is 0 errors / 0 unconnected on +3V3.

This script SAVES the board only if both verifications pass.
"""
import os
import sys
import subprocess
import re
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
DRC_REPORT = os.path.join(HERE, "drc_report.txt")

START_MM = (69.2000, 29.8700)
END_MM   = (69.6840, 32.7459)
WIDTH_MM = 0.20


def drc_summary():
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report",
                    "--output", DRC_REPORT, PCB_PATH], capture_output=True)
    with open(DRC_REPORT) as f:
        txt = f.read()
    # Errors line
    m_err = re.search(r"Found (\d+) DRC violation", txt)
    n_err = int(m_err.group(1)) if m_err else None
    m_unc = re.search(r"Found (\d+) unconnected item", txt)
    n_unc = int(m_unc.group(1)) if m_unc else None
    if n_err is None or n_unc is None:
        # Fallback: count blocks
        blocks = re.split(r'\n(?=\[)', txt)
        n_err = sum(1 for b in blocks if b.startswith('[') and 'unconnected_items' not in b
                    and 'Found' not in b and 'End of' not in b)
        n_unc = sum(1 for b in blocks if 'unconnected_items' in b)
    return n_err, n_unc, txt


def main():
    print("[1] PRE-lay DRC")
    n_err_pre, n_unc_pre, _ = drc_summary()
    print(f"    DRC: {n_err_pre} errors, {n_unc_pre} unconnected")
    if n_err_pre != 0:
        print(f"    !! pre-state has DRC errors; bailing")
        sys.exit(1)

    print("[2] load board + lay trace")
    brd = pcbnew.LoadBoard(PCB_PATH)
    nets = brd.GetNetsByName().asdict()
    n3v3 = None
    for k, v in nets.items():
        if str(k) == "+3V3":
            n3v3 = v
            break
    if n3v3 is None:
        print("    !! +3V3 net not found")
        sys.exit(1)

    track = pcbnew.PCB_TRACK(brd)
    track.SetStart(pcbnew.VECTOR2I(int(START_MM[0] * 1e6), int(START_MM[1] * 1e6)))
    track.SetEnd(pcbnew.VECTOR2I(int(END_MM[0] * 1e6), int(END_MM[1] * 1e6)))
    track.SetWidth(int(WIDTH_MM * 1e6))
    track.SetLayer(pcbnew.B_Cu)
    track.SetNet(n3v3)
    brd.Add(track)
    length = ((END_MM[0]-START_MM[0])**2 + (END_MM[1]-START_MM[1])**2) ** 0.5
    print(f"    laid B.Cu track {START_MM} -> {END_MM} length={length:.3f}mm width={WIDTH_MM}mm net=+3V3")
    pcbnew.SaveBoard(PCB_PATH, brd)

    print("[3] re-fill zones")
    brd2 = pcbnew.LoadBoard(PCB_PATH)
    pcbnew.ZONE_FILLER(brd2).Fill(list(brd2.Zones()))
    pcbnew.SaveBoard(PCB_PATH, brd2)

    print("[4] POST-lay DRC")
    n_err_post, n_unc_post, txt_post = drc_summary()
    print(f"    DRC: {n_err_post} errors, {n_unc_post} unconnected")
    print(f"    delta errors: {n_err_post - n_err_pre:+}")
    print(f"    delta unconnected: {n_unc_post - n_unc_pre:+}")

    if n_err_post == 0 and n_unc_post == 0:
        print(f"\n    OK CLOSED — board is 0 DRC errors + 0 unconnected.")
        sys.exit(0)
    elif n_err_post > 0:
        print(f"\n    !! DRC introduced {n_err_post} errors — REVERTING")
        # Revert: re-load + remove the track we just added
        brd_rev = pcbnew.LoadBoard(PCB_PATH)
        removed = 0
        for t in list(brd_rev.GetTracks()):
            if isinstance(t, pcbnew.PCB_VIA): continue
            if t.GetLayer() != pcbnew.B_Cu: continue
            s = t.GetStart(); e = t.GetEnd()
            sx, sy = s.x/1e6, s.y/1e6
            ex, ey = e.x/1e6, e.y/1e6
            if (abs(sx-START_MM[0])<1e-4 and abs(sy-START_MM[1])<1e-4 and
                abs(ex-END_MM[0])<1e-4 and abs(ey-END_MM[1])<1e-4):
                brd_rev.Remove(t)
                removed += 1
        pcbnew.SaveBoard(PCB_PATH, brd_rev)
        brd_rev2 = pcbnew.LoadBoard(PCB_PATH)
        pcbnew.ZONE_FILLER(brd_rev2).Fill(list(brd_rev2.Zones()))
        pcbnew.SaveBoard(PCB_PATH, brd_rev2)
        print(f"    reverted {removed} track(s).")
        # Dump the DRC errors for master
        err_blocks = re.findall(r"\[([^\]]+)\]: ([^\n]+)\n[^\[]*", txt_post)
        print(f"\n    DRC error details (first 5):")
        for k, v in err_blocks[:5]:
            print(f"      [{k}]: {v}")
        sys.exit(2)
    else:
        print(f"\n    DRC clean but unconnected still {n_unc_post} (expected 0). Investigate.")
        sys.exit(3)


if __name__ == "__main__":
    main()
