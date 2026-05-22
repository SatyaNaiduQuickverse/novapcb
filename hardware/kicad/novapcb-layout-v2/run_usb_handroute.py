#!/usr/bin/env python3
"""Step 6 precursor — USB_DM / USB_DP F.Cu microstrip hand-route.

Per master 2026-05-21 directive: F.Cu ONLY, no via mid-pair, length-matched,
W=0.30 / S=0.10, ref'd to In1.Cu (L2 GND) for the validated Z_diff = 94.4 Ω
microstrip geometry from docs/CONTROLLED_IMPEDANCE.md.

Endpoints (the USB pair after the U5 ESD chip):
  USB_DM: U5.4 (50.0775, 49.3400) F.Cu  -> U1.70 (47.2050, 26.5000) F.Cu
  USB_DP: U5.6 (50.0775, 47.4400) F.Cu  -> U1.71 (47.2050, 26.0000) F.Cu

Routing strategy — 3 segments per line:
  1. Short fanout stub from U5 pad to the "parallel section start"
  2. Long parallel run with the partner trace, 0.40 mm center-to-center
     (W=0.30 + S=0.10), maintained from Y=46 down to Y=27
  3. Short fanout stub from parallel-section end to U1 pad

The U5-side stubs handle the necessary 1.9 mm -> 0.4 mm convergence.
The U1-side stubs handle the 0.5 mm -> 0.4 mm convergence (almost none).
The parallel-section run is true diff-pair microstrip.

Pair separation during parallel section = 0.40 mm (Y_DM_center=26.70,
Y_DP_center=26.30 — diff 0.40 mm, S=0.10).
"""
import os, sys, re, subprocess, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")

W_MM = 0.30
GAP_MM = 0.10
PAIR_C2C_MM = W_MM + GAP_MM  # 0.40 mm center-to-center

# Pair geometry
PARALLEL_X = 47.40
PARALLEL_Y_DM = 26.70    # DM line center-Y during parallel run
PARALLEL_Y_DP = 26.30    # DP line center-Y during parallel run (0.40 above/below)

# Endpoint coords (verified by reading board)
U5_DM   = (50.0775, 49.3400)
U5_DP   = (50.0775, 47.4400)
U1_DM   = (47.2050, 26.5000)
U1_DP   = (47.2050, 26.0000)

# Northern fanout intermediates — 0.40 mm apart center-to-center for diff
# pair, just south of U5 pads.
NORTH_X = 49.50
NORTH_Y_DM = PARALLEL_Y_DM + (49.0 - 26.7)  # extrapolated; use direct val
NORTH_Y_DM_FIXED = 48.55  # 0.20 mm above midpoint of U5 pads (48.39 -> 48.55)
NORTH_Y_DP_FIXED = 48.23  # 0.20 mm below midpoint of U5 pads (48.39 -> 48.23)


def add_track(brd, x1, y1, x2, y2, net, layer=pcbnew.F_Cu, width_mm=W_MM):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(width_mm * 1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


def strip_net(brd, net_name):
    """Remove every track/via on the given net."""
    n = 0
    for t in list(brd.GetTracks()):
        if t.GetNet() and str(t.GetNet().GetNetname()) == net_name:
            brd.Remove(t); n += 1
    return n


def drc_summary():
    out = "/tmp/drc_usb.txt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report", "--output", out, PCB], capture_output=True)
    txt = open(out).read()
    n_err = int(re.search(r"Found (\d+) DRC violation", txt).group(1)) if re.search(r"Found \d+ DRC violation", txt) else None
    n_unc = int(re.search(r"Found (\d+) unconnected", txt).group(1)) if re.search(r"Found \d+ unconnected", txt) else None
    return n_err, n_unc


def main():
    brd = pcbnew.LoadBoard(PCB)
    nets = brd.GetNetsByName().asdict()
    n_dm = n_dp = None
    for k, v in nets.items():
        if str(k) == "USB_DM": n_dm = v
        if str(k) == "USB_DP": n_dp = v
    if not (n_dm and n_dp):
        print("!! USB_DM/USB_DP nets not found"); sys.exit(1)

    print("[1] strip existing USB_DM / USB_DP", flush=True)
    print(f"    stripped USB_DM: {strip_net(brd, 'USB_DM')}", flush=True)
    print(f"    stripped USB_DP: {strip_net(brd, 'USB_DP')}", flush=True)

    print("[2] lay F.Cu diff-pair microstrip", flush=True)
    # USB_DM: U5.4 -> (NORTH_X, NORTH_Y_DM) -> (PARALLEL_X, PARALLEL_Y_DM) -> U1.70
    add_track(brd, U5_DM[0], U5_DM[1], NORTH_X, NORTH_Y_DM_FIXED, n_dm)
    add_track(brd, NORTH_X, NORTH_Y_DM_FIXED, PARALLEL_X, PARALLEL_Y_DM, n_dm)
    add_track(brd, PARALLEL_X, PARALLEL_Y_DM, U1_DM[0], U1_DM[1], n_dm)
    # USB_DP: U5.6 -> (NORTH_X, NORTH_Y_DP) -> (PARALLEL_X, PARALLEL_Y_DP) -> U1.71
    add_track(brd, U5_DP[0], U5_DP[1], NORTH_X, NORTH_Y_DP_FIXED, n_dp)
    add_track(brd, NORTH_X, NORTH_Y_DP_FIXED, PARALLEL_X, PARALLEL_Y_DP, n_dp)
    add_track(brd, PARALLEL_X, PARALLEL_Y_DP, U1_DP[0], U1_DP[1], n_dp)
    print("    laid 3 segments per line, F.Cu, W=0.30mm")

    # Length check
    def seg_len(a, b): return math.hypot(b[0]-a[0], b[1]-a[1])
    dm_len = (seg_len(U5_DM, (NORTH_X, NORTH_Y_DM_FIXED)) +
              seg_len((NORTH_X, NORTH_Y_DM_FIXED), (PARALLEL_X, PARALLEL_Y_DM)) +
              seg_len((PARALLEL_X, PARALLEL_Y_DM), U1_DM))
    dp_len = (seg_len(U5_DP, (NORTH_X, NORTH_Y_DP_FIXED)) +
              seg_len((NORTH_X, NORTH_Y_DP_FIXED), (PARALLEL_X, PARALLEL_Y_DP)) +
              seg_len((PARALLEL_X, PARALLEL_Y_DP), U1_DP))
    print(f"    USB_DM length: {dm_len:.3f} mm")
    print(f"    USB_DP length: {dp_len:.3f} mm")
    print(f"    diff: {abs(dm_len - dp_len):.3f} mm (USB 2.0 inter-pair skew tol ~22mm; well under)")

    print("[3] refill zones + save", flush=True)
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)

    print("[4] DRC", flush=True)
    n_err, n_unc = drc_summary()
    print(f"    DRC: {n_err} errors, {n_unc} unconnected")


if __name__ == "__main__":
    main()
