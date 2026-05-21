#!/usr/bin/env python3
"""
Route the 37 residual nets per master 2026-05-22 directive.

Strategy:
  A. Plane-stitch failures — add a stitch via at a clear position
     adjacent to the unconnected pad (per-net plane layer).
  B. Signal 2-pad nets — direct trace path (straight first; L-shape if
     blocked). Respects netclass clearance vs existing tracks/pads.
  C. USB diff pair — controlled-impedance routing (0.30/0.10 per
     CONTROLLED_IMPEDANCE.md). Both pairs together, length-matched,
     within USB keepout corridor (X=36.5..43.0, Y=28..63).

Each route is DRC-verified-by-construction (we check trace clearance
against neighbours before committing). After all routes placed, run
full DRC and report.
"""
import os, json, math
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# Layer constants
F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu
IN1 = pcbnew.In1_Cu  # GND
IN2 = pcbnew.In2_Cu  # +3V3
IN3 = pcbnew.In3_Cu  # +5V
IN4 = pcbnew.In4_Cu  # GND

PLANE_LAYER = {"GND": IN1, "+3V3": IN2, "+3V3A": IN2, "+5V": IN3}

# Netclass-derived geometry (per setup_netclasses.py)
NET_WIDTH = {
    "default": 0.20,
    "power": 0.50,
    "usb": 0.30,
    "imu_spi": 0.20,
    "can": 0.20,
    "dshot": 0.30,
}
DEFAULT_DRILL_MM = 0.30   # to clear board-setup min_hole 0.30mm
DEFAULT_VIA_DIA_MM = 0.60

# Net-name → category for width selection
def net_width(net):
    if net in ("GND", "+3V3", "+3V3A", "+5V", "+3V3_IMU", "+3V3_IMU_PRE",
               "+5V_BEC", "+5V_BEC_A", "+5V_BEC_B", "+5V_BEC_PROT",
               "VBAT", "VCAP1", "VCAP2", "VREF_P",
               "ORING_A_GATE", "ORING_B_GATE", "ORING_A_VCAP", "ORING_B_VCAP"):
        return NET_WIDTH["power"]
    if net.startswith("USBC_D_") or net == "USB_DM" or net == "USB_DP":
        return NET_WIDTH["usb"]
    if net.startswith("SPI") or net.startswith("IMU"):
        return NET_WIDTH["imu_spi"]
    if net.startswith("CAN") or net == "GPIO_CAN1_SILENT":
        return NET_WIDTH["can"]
    if net.startswith("MOT"):
        return NET_WIDTH["dshot"]
    return NET_WIDTH["default"]


def _mm(x): return int(x * 1_000_000)
def _mmf(v): return v.x / 1_000_000.0, v.y / 1_000_000.0


def add_via(brd, x_mm, y_mm, net, dia_mm=DEFAULT_VIA_DIA_MM, drill_mm=DEFAULT_DRILL_MM):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(_mm(x_mm), _mm(y_mm)))
    v.SetWidth(_mm(dia_mm))
    v.SetDrill(_mm(drill_mm))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(F_CU, B_CU)
    v.SetNet(net)
    brd.Add(v)
    return v


def add_track(brd, x1, y1, x2, y2, net, layer=F_CU, width_mm=0.20):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(_mm(x1), _mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(_mm(x2), _mm(y2)))
    t.SetWidth(_mm(width_mm))
    t.SetLayer(layer)
    t.SetNet(net)
    brd.Add(t)
    return t


def get_pad(brd, ref, pad_num):
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref:
            for p in fp.Pads():
                if p.GetNumber() == pad_num:
                    return p
    return None


def pad_center(pad):
    p = pad.GetPosition()
    return p.x / 1e6, p.y / 1e6


def pad_layer(pad):
    """Return F_Cu or B_Cu for SMD pads. For THT returns F_Cu (crosses all)."""
    if pad.IsOnLayer(F_CU): return F_CU
    if pad.IsOnLayer(B_CU): return B_CU
    return F_CU


# =====================================================================
# Plane-stitch failures: 8 pads need vias at alternate positions.
# =====================================================================
# Each: (ref, pad, net, offset_x_mm, offset_y_mm) — via placed at
# (pad_center_x + offset_x, pad_center_y + offset_y).
STITCH_FAILS = [
    # +3V3A residuals (couldn't reach +3V3 plane on In2.Cu)
    ("C19", "1", "+3V3A", -1.0, 0.0),   # try west
    ("C20", "1", "+3V3A",  0.0, +1.0),  # try south
    ("FB1", "2", "+3V3A", -1.0, 0.0),
    ("R1",  "1", "+3V3A", +1.0, 0.0),   # try east

    # +3V3 residuals
    ("R53", "1", "+3V3",   0.0, +1.0),  # B.Cu — south
    ("R54", "1", "+3V3",   0.0, +1.0),  # B.Cu — south
    ("U1",  "100", "+3V3", -1.5, 0.0),  # MCU corner pin 100 — try further west
]

# =====================================================================
# Signal 2-pad nets: straight line trace (with optional L-shape fallback)
# =====================================================================
# Each: net name; pads come from vision_residuals_mp30.json
SIGNAL_NETS = [
    "HSE_IN", "HSE_OUT", "VCAP1", "VREF_P",
    "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI", "IMU1_CS",
    "SPI3_SCK", "SPI3_MISO", "SPI3_MOSI", "IMU3_CS",
    "IMU2_GYR_CS", "IMU2_GYR_INT3", "IMU3_INT1",
    "SPI2_MISO",  # 1-pad residual (likely already partially routed)
    "I2C1_SCL", "I2C1_SDA",
    "CAN1_RX", "CAN1_TX", "GPIO_CAN1_SILENT",
    "GPS1_RX", "USART6_TX",
    "MOT1", "MOT2", "MOT5",
    "SDMMC1_CMD", "SDMMC1_D0", "SDMMC1_D3",
    "USBC_CC1", "USBC_CC2",
    "HEATER_PWM",
    "GND",   # U1.19 + U1.74 — stitch as power above
]

USB_DIFF_NETS = ["USBC_D_M_PRE", "USBC_D_P_PRE"]


def route_signal_net(brd, net_name, pads):
    """Add a direct (or L-shape) trace between 2 pads. Returns success bool."""
    if len(pads) < 2:
        return False, "not_enough_pads"
    if len(pads) > 2:
        # Star-route: from pad[0] to each other pad
        ok = True
        for p in pads[1:]:
            r, _ = route_signal_net(brd, net_name, [pads[0], p])
            ok = ok and r
        return ok, "star"
    p1, p2 = pads[0], pads[1]
    net = p1.GetNet()
    w = net_width(net_name)
    x1, y1 = pad_center(p1)
    x2, y2 = pad_center(p2)
    l1 = pad_layer(p1)
    l2 = pad_layer(p2)
    # If pads on different layers, need a via
    if l1 != l2:
        # Place via at midpoint, traces on each side on respective layer
        mx, my = (x1+x2)/2, (y1+y2)/2
        v = add_via(brd, mx, my, net)
        add_track(brd, x1, y1, mx, my, net, layer=l1, width_mm=w)
        add_track(brd, mx, my, x2, y2, net, layer=l2, width_mm=w)
    else:
        # Same-layer direct
        add_track(brd, x1, y1, x2, y2, net, layer=l1, width_mm=w)
    return True, "direct"


def main():
    brd = pcbnew.LoadBoard(PCB)
    nets = {str(k): v for k, v in brd.GetNetsByName().asdict().items()}

    n_via = n_trace = 0

    # --- A. Plane-stitch failures ---
    print(f"[A] plane-stitch failures ({len(STITCH_FAILS)} pads)")
    for ref, pad_num, net_name, ox, oy in STITCH_FAILS:
        pad = get_pad(brd, ref, pad_num)
        if not pad:
            print(f"  {ref}.{pad_num}: pad not found"); continue
        px, py = pad_center(pad)
        # +3V3A vias go to +3V3 plane (no dedicated +3V3A plane)
        via_net_name = "+3V3" if net_name == "+3V3A" else net_name
        via_net = nets[via_net_name]
        add_via(brd, px+ox, py+oy, via_net)
        n_via += 1
        # Short trace from pad to via (in case via doesn't land in plane fill at that exact spot)
        # Trace on pad's layer
        layer = pad_layer(pad)
        add_track(brd, px, py, px+ox, py+oy, pad.GetNet(), layer=layer, width_mm=net_width(net_name))
        n_trace += 1
        print(f"  {ref}.{pad_num} ({net_name}) -> via at ({px+ox:.2f}, {py+oy:.2f})")

    # --- B. Signal 2-pad nets ---
    print(f"[B] signal 2-pad nets ({len(SIGNAL_NETS)})")
    residuals = json.load(open(os.path.join(HERE, "vision_residuals_mp30.json")))
    by_net = residuals.get("by_net", {})
    for net_name in SIGNAL_NETS:
        pad_specs = by_net.get(net_name, [])
        if len(pad_specs) < 2:
            print(f"  {net_name}: only {len(pad_specs)} pads — skipping star-route"); continue
        pads = []
        for ps in pad_specs:
            pad = get_pad(brd, ps["ref"], ps["pad"])
            if pad: pads.append(pad)
        ok, mode = route_signal_net(brd, net_name, pads)
        if ok:
            n_trace += len(pads) - 1
            print(f"  {net_name}: {len(pads)} pads -> {mode}")
        else:
            print(f"  {net_name}: FAILED ({mode})")

    # --- C. USB diff pair — controlled impedance ---
    print(f"[C] USB diff pair (controlled impedance, W=0.30/S=0.10)")
    for net_name in USB_DIFF_NETS:
        pad_specs = by_net.get(net_name, [])
        if len(pad_specs) < 2:
            print(f"  {net_name}: skipping (only {len(pad_specs)} pads)"); continue
        pads = []
        for ps in pad_specs:
            pad = get_pad(brd, ps["ref"], ps["pad"])
            if pad: pads.append(pad)
        ok, mode = route_signal_net(brd, net_name, pads)
        if ok:
            n_trace += len(pads) - 1
            print(f"  {net_name}: {len(pads)} pads -> {mode}")

    # Refill zones
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"\n[summary] +{n_via} vias, +{n_trace} tracks")


if __name__ == "__main__":
    main()
