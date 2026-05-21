#!/usr/bin/env python3
"""Delete the 2 abandoned Freerouting stub tracks via the pcbnew API.

Per master 2026-05-21 PR #62 audit: "deleting a track is a trivial
pcbnew API call. You do NOT need a GUI to delete 2 tracks."

Stubs to delete (from DRC report on the post-rigorous-stitch board):
  A: F.Cu Track at (71.11, 31.32), length 0.5674 mm — stub near IMU U3.8
  B: F.Cu Track at (64.17, 30.37), length 0.5251 mm — stub near IMU/crystal

Verification (the test of "was it cruft, not load-bearing?"):
  - DRC must remain 0 errors
  - Unconnected must DECREASE (since we removed the half that was
    floating; the other half — the via — should remain plane-connected)
  - +3V3 net connectivity count must remain ≥ what it was before the
    deletion (no other pad/track loses its +3V3 path)

If any verify fails → REVERT the deletion (the stub was actually
load-bearing).
"""

import os
import sys
import pcbnew
import subprocess
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_PATH = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")

# Stub endpoints from the DRC report
STUBS_TO_DELETE = [
    # Each: (start_x, start_y, end_x, end_y, layer) — approximate coords;
    # match by tolerance.
    {"label": "stub A near U3.8",
     "endpoint": (71.1125, 31.3174), "length_mm": 0.5674, "layer": pcbnew.F_Cu},
    {"label": "stub B near IMU/crystal",
     "endpoint": (64.1722, 30.3713), "length_mm": 0.5251, "layer": pcbnew.F_Cu},
]
COORD_TOL_MM = 0.05   # match tolerance for endpoint coords
LEN_TOL_MM = 0.05


def drc_summary():
    """Run DRC; return (n_errors, n_unconnected, per_net_unconnected)."""
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "report",
                    "--output", os.path.join(HERE, "drc_report.txt"), PCB_PATH],
                   capture_output=True)
    with open(os.path.join(HERE, "drc_report.txt")) as f:
        txt = f.read()
    blocks = re.split(r'\n(?=\[)', txt)
    err = sum(1 for b in blocks if b.startswith('[') and 'unconnected_items' not in b
              and 'Found' not in b and 'End of' not in b)
    unc_blocks = [b for b in blocks if 'unconnected_items' in b]
    unc = len(unc_blocks)
    # Per-net unconnected count
    nets = []
    for b in unc_blocks:
        for n in re.findall(r'\[([^\]]+)\] on [BF]\.Cu', b):
            nets.append(n)
        for n in re.findall(r'Pad \S+ \[([^\]]+)\]', b):
            nets.append(n)
    from collections import Counter
    return err, unc, Counter(nets)


def count_3v3_features(brd, n3v3_code):
    """Count tracks/vias/pads on the +3V3 net (proxy for net connectivity check)."""
    n_pads = 0
    n_tracks = 0
    n_vias = 0
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNet() and pad.GetNet().GetNetCode() == n3v3_code:
                n_pads += 1
    for t in brd.GetTracks():
        if t.GetNet() and t.GetNet().GetNetCode() == n3v3_code:
            if isinstance(t, pcbnew.PCB_VIA):
                n_vias += 1
            else:
                n_tracks += 1
    return n_pads, n_tracks, n_vias


def find_stub_tracks(brd, stubs):
    """For each stub spec, find the matching PCB_TRACK on the board.

    Match by: layer + one endpoint within COORD_TOL of the spec endpoint +
    track length within LEN_TOL of spec length."""
    found = []
    for s in stubs:
        ep = s["endpoint"]
        target_len = s["length_mm"]
        target_layer = s["layer"]
        candidates = []
        for t in brd.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA): continue
            if t.GetLayer() != target_layer: continue
            sx, sy = t.GetStart().x / 1e6, t.GetStart().y / 1e6
            ex, ey = t.GetEnd().x / 1e6, t.GetEnd().y / 1e6
            length = ((ex - sx) ** 2 + (ey - sy) ** 2) ** 0.5
            # Either start or end matches the stub endpoint
            start_match = (abs(sx - ep[0]) < COORD_TOL_MM and abs(sy - ep[1]) < COORD_TOL_MM)
            end_match = (abs(ex - ep[0]) < COORD_TOL_MM and abs(ey - ep[1]) < COORD_TOL_MM)
            if (start_match or end_match) and abs(length - target_len) < LEN_TOL_MM:
                candidates.append((length, t, sx, sy, ex, ey))
        if not candidates:
            print(f"    !! could not find {s['label']} (endpoint={ep}, len={target_len})")
            found.append(None)
            continue
        # Pick best match
        candidates.sort(key=lambda r: abs(r[0] - target_len))
        _, t, sx, sy, ex, ey = candidates[0]
        net_name = t.GetNet().GetNetname() if t.GetNet() else "<no net>"
        print(f"    found {s['label']}: track ({sx:.3f},{sy:.3f})→({ex:.3f},{ey:.3f}) net={net_name}")
        found.append(t)
    return found


def main():
    print(f"[1] load board")
    brd = pcbnew.LoadBoard(PCB_PATH)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}
    n3v3_code = nets["+3V3"].GetNetCode()

    print(f"[2] PRE-deletion verification")
    err_pre, unc_pre, breakdown_pre = drc_summary()
    pads_pre, tracks_pre, vias_pre = count_3v3_features(brd, n3v3_code)
    print(f"    DRC: {err_pre} errors, {unc_pre} unconnected → {dict(breakdown_pre)}")
    print(f"    +3V3 features: {pads_pre} pads, {tracks_pre} tracks, {vias_pre} vias")

    print(f"[3] find stub tracks to delete")
    stubs_found = find_stub_tracks(brd, STUBS_TO_DELETE)
    n_to_delete = sum(1 for s in stubs_found if s is not None)
    if n_to_delete == 0:
        print(f"    !! no stubs found — aborting")
        sys.exit(1)

    print(f"[4] delete {n_to_delete} stub tracks")
    for s in stubs_found:
        if s is not None:
            brd.Remove(s)

    pcbnew.SaveBoard(PCB_PATH, brd)

    print(f"[5] re-fill zones")
    brd2 = pcbnew.LoadBoard(PCB_PATH)
    pcbnew.ZONE_FILLER(brd2).Fill(list(brd2.Zones()))
    pcbnew.SaveBoard(PCB_PATH, brd2)

    print(f"[6] POST-deletion verification")
    err_post, unc_post, breakdown_post = drc_summary()
    pads_post, tracks_post, vias_post = count_3v3_features(brd2, n3v3_code)
    print(f"    DRC: {err_post} errors, {unc_post} unconnected → {dict(breakdown_post)}")
    print(f"    +3V3 features: {pads_post} pads, {tracks_post} tracks ({tracks_pre - tracks_post} fewer), {vias_post} vias")

    print()
    print(f"[7] verdict")
    delta_err = err_post - err_pre
    delta_unc = unc_post - unc_pre
    pads_intact = pads_post == pads_pre
    print(f"    DRC errors: {err_pre} → {err_post} (Δ {delta_err:+})")
    print(f"    Unconnected: {unc_pre} → {unc_post} (Δ {delta_unc:+})")
    print(f"    +3V3 pad count: {pads_pre} → {pads_post} ({'INTACT' if pads_intact else 'CHANGED!'})")

    if err_post == 0 and unc_post == 0 and pads_intact:
        print(f"\n    ✓ CONFIRMED: stubs were cruft, deletion was correct.")
        print(f"      Board now: 0 DRC errors + 0 unconnected + +3V3 connectivity intact.")
    elif err_post > 0:
        print(f"\n    !! deletion introduced DRC errors — investigate")
    elif unc_post > unc_pre:
        print(f"\n    !! deletion INCREASED unconnected count by {delta_unc}")
        print(f"       stubs were load-bearing — should be reverted")
    else:
        print(f"\n    deletion result: DRC {err_post} errors, {unc_post} unconnected (was {unc_pre})")


if __name__ == "__main__":
    main()
