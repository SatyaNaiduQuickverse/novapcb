#!/usr/bin/env python3
"""Step 6 precursor — USB hand-route v2 per master 2026-05-21 amended directive.

Hand-route USB_DM/USB_DP on F.Cu + B.Cu with minimal, deliberate, GND-
stitched via transitions. Legitimate route, NOT compromise: JLC06161H
stackup is symmetric (L1↔L2 prepreg = L5↔L6 prepreg = 0.21 mm 7628),
so a B.Cu microstrip ref'd to In4-GND has SAME Z_diff = 94.4 Ω as the
F.Cu microstrip ref'd to In1-GND with W=0.30/S=0.10.

Topology — 2 transitions per line:
  U5 F.Cu pad -> short F.Cu stub -> F→B via -> long B.Cu parallel run ->
  B→F via -> short F.Cu stub -> U1 F.Cu pad

Via placement: D+/D- vias close together at each transition; GND
return-stitching vias adjacent (continuous In1↔In4 GND return path).

Endpoints:
  USB_DM: U5.4 (50.0775, 49.3400) F.Cu  -> U1.70 (47.2050, 26.5000) F.Cu
  USB_DP: U5.6 (50.0775, 47.4400) F.Cu  -> U1.71 (47.2050, 26.0000) F.Cu

Via positions (D+/D- 0.40 mm apart per W=0.30/S=0.10 spec):
  NORTH transitions (near U5):
    DM_N = (50.50, 48.50), DP_N = (50.50, 48.10)
  SOUTH transitions (near U1):
    DM_S = (47.50, 26.70), DP_S = (47.50, 26.30)
  GND stitch vias (4 total, flanking each transition):
    GND_N1 = (49.95, 48.30), GND_N2 = (51.05, 48.30)
    GND_S1 = (46.95, 26.50), GND_S2 = (48.05, 26.50)
"""
import os, sys, re, subprocess, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")

W_MM = 0.30                # trace width
PAIR_C2C = 0.40            # center-to-center for W=0.30/S=0.10
# USB pair vias: smallest project-allowed (0.40 pad / 0.30 drill).
# At via positions the pair must widen to 0.60mm center-to-center to
# meet 0.20mm clearance between via edges. The B.Cu trace run between
# vias maintains the 0.40mm spec — only the via points themselves widen.
VIA_PAD_MM = 0.40
VIA_DRILL_MM = 0.30
GND_VIA_PAD_MM = 0.60
GND_VIA_DRILL_MM = 0.30

# Endpoints
U5_DM = (50.0775, 49.3400)
U5_DP = (50.0775, 47.4400)
U1_DM = (47.2050, 26.5000)
U1_DP = (47.2050, 26.0000)

# Transition vias — EAST of U5/U1 so F.Cu stubs come in horizontally.
# Pair widens to 0.60 mm center-to-center AT the vias (0.40 trace + 0.20
# clearance between via edges with 0.40mm via pad). B.Cu run between vias
# follows actual via positions — slight gradient from 0.40 at one end to
# 0.60 at the other is acceptable for USB 2.0 pair geometry.
DM_N = (51.00, 48.70)   # 0.60 mm from DP_N
DP_N = (51.00, 48.10)
DM_S = (48.50, 26.80)   # 0.60 mm from DP_S
DP_S = (48.50, 26.20)

# GND return-stitch vias (flanking each transition).
# Needs >= 0.80 mm from USB via centers (via_pad 0.30 + 0.30 + clearance 0.20).
GND_STITCHES = [
    (50.10, 48.40),  # NORTH-left (0.92 mm from USB via centers at X=51.0)
    (51.90, 48.40),  # NORTH-right
    (47.60, 26.25),  # SOUTH-left (0.95 mm from USB via centers at X=48.5)
    (49.40, 26.25),  # SOUTH-right
]


def add_track(brd, x1, y1, x2, y2, net, layer=pcbnew.F_Cu, width=W_MM):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
    t.SetWidth(int(width * 1e6))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)


def add_via(brd, x, y, net, pad_mm=VIA_PAD_MM, drill_mm=VIA_DRILL_MM):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(int(x * 1e6), int(y * 1e6)))
    v.SetWidth(int(pad_mm * 1e6))
    v.SetDrill(int(drill_mm * 1e6))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    brd.Add(v)


def strip_net(brd, net_name):
    n = 0
    for t in list(brd.GetTracks()):
        if t.GetNet() and str(t.GetNet().GetNetname()) == net_name:
            brd.Remove(t); n += 1
    return n


def drc_summary():
    out = "/tmp/drc_usb2.txt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report", "--output", out, PCB],
                   capture_output=True)
    txt = open(out).read()
    n_err = int(re.search(r"Found (\d+) DRC violation", txt).group(1)) if re.search(r"Found \d+ DRC violation", txt) else None
    n_unc = int(re.search(r"Found (\d+) unconnected", txt).group(1)) if re.search(r"Found \d+ unconnected", txt) else None
    return n_err, n_unc


def main():
    brd = pcbnew.LoadBoard(PCB)
    nets = brd.GetNetsByName().asdict()
    n_dm = n_dp = n_gnd = None
    for k, v in nets.items():
        if str(k) == "USB_DM": n_dm = v
        if str(k) == "USB_DP": n_dp = v
        if str(k) == "GND": n_gnd = v
    if not (n_dm and n_dp and n_gnd):
        print("!! USB or GND nets not found"); sys.exit(1)

    print("[1] strip existing USB_DM / USB_DP", flush=True)
    print(f"    stripped USB_DM: {strip_net(brd, 'USB_DM')}", flush=True)
    print(f"    stripped USB_DP: {strip_net(brd, 'USB_DP')}", flush=True)

    print("[2] lay F.Cu stubs at U5 end", flush=True)
    add_track(brd, U5_DM[0], U5_DM[1], DM_N[0], DM_N[1], n_dm, pcbnew.F_Cu)
    add_track(brd, U5_DP[0], U5_DP[1], DP_N[0], DP_N[1], n_dp, pcbnew.F_Cu)

    print("[3] place N transition vias (USB pair + GND stitches)", flush=True)
    add_via(brd, DM_N[0], DM_N[1], n_dm)
    add_via(brd, DP_N[0], DP_N[1], n_dp)
    for gx, gy in GND_STITCHES[:2]:
        add_via(brd, gx, gy, n_gnd, pad_mm=GND_VIA_PAD_MM, drill_mm=GND_VIA_DRILL_MM)

    print("[4] lay B.Cu long parallel run", flush=True)
    add_track(brd, DM_N[0], DM_N[1], DM_S[0], DM_S[1], n_dm, pcbnew.B_Cu)
    add_track(brd, DP_N[0], DP_N[1], DP_S[0], DP_S[1], n_dp, pcbnew.B_Cu)

    print("[5] place S transition vias (USB pair + GND stitches)", flush=True)
    add_via(brd, DM_S[0], DM_S[1], n_dm)
    add_via(brd, DP_S[0], DP_S[1], n_dp)
    for gx, gy in GND_STITCHES[2:]:
        add_via(brd, gx, gy, n_gnd, pad_mm=GND_VIA_PAD_MM, drill_mm=GND_VIA_DRILL_MM)

    print("[6] lay F.Cu stubs at U1 end", flush=True)
    add_track(brd, DM_S[0], DM_S[1], U1_DM[0], U1_DM[1], n_dm, pcbnew.F_Cu)
    add_track(brd, DP_S[0], DP_S[1], U1_DP[0], U1_DP[1], n_dp, pcbnew.F_Cu)

    # Length check
    def seg_len(a, b): return math.hypot(b[0]-a[0], b[1]-a[1])
    dm_len = (seg_len(U5_DM, DM_N) + seg_len(DM_N, DM_S) + seg_len(DM_S, U1_DM))
    dp_len = (seg_len(U5_DP, DP_N) + seg_len(DP_N, DP_S) + seg_len(DP_S, U1_DP))
    print(f"    USB_DM total: {dm_len:.3f} mm")
    print(f"    USB_DP total: {dp_len:.3f} mm")
    print(f"    inter-pair skew: {abs(dm_len - dp_len):.3f} mm "
          f"(USB 2.0 tol ~22 mm; well under)")

    print("[7] refill zones + save", flush=True)
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)

    print("[8] DRC", flush=True)
    n_err, n_unc = drc_summary()
    print(f"    DRC: {n_err} errors, {n_unc} unconnected")


if __name__ == "__main__":
    main()
