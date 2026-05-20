#!/usr/bin/env python3
"""
Phase 4d2 — 17-net headless routing completion.

>>> RESULT: 0 of 17 nets routed cleanly. 345 DRC violations introduced by
>>> the naive L-shape Manhattan approach below — ZERO obstacle awareness.
>>> See phase-4d2-results.md for the full diagnosis.
>>> This is a DOCUMENTED DEAD-END. Don't re-attempt this approach on the
>>> 96%-routed board. Hand back to ROUTING_HANDOFF.md GUI flow per master's
>>> Rule-13 stop adjudication.
>>>
>>> Kept committed so a future Claude can SEE the failed approach + its
>>> reasoning, rather than trying it again.

One honest attempt per net. API-measured pad positions. Treat the existing
96%-Freerouted 771 tracks + 153 vias as fixed obstacles (they're not locked,
but we DO NOT TOUCH them — we only ADD new tracks).

Approach per net:
  1. Get pad positions via API (pcbnew.PAD.GetPosition + .GetLayerSet).
  2. Plan a simple Manhattan or 2-segment route from pad A to pad B (with
     a via if A and B are on different copper layers).
  3. Add tracks to the board; set IsLocked()=True so future routing knows.
  4. Move on. NO zigzagging.

Per-net hints from ROUTING_HANDOFF.md applied via NET_PLAN below.

The routes are NOT impedance-controlled (except USB_DP which uses the
class width=0.25mm); a GUI pass post-router can tune impedance/length if the
DRC indicates needed.
"""

import json
import subprocess
from pathlib import Path
import pcbnew

HERE = Path(__file__).parent.resolve()
PCB_PATH = HERE / "novapcb-layout.kicad_pcb"

F_CU = pcbnew.F_Cu
B_CU = pcbnew.B_Cu

# Net class default widths/clearances from .kicad_pro
NETCLASS_WIDTH = {
    "USB_diffpair": 0.25,
    "IMU_SPI":      0.15,
    "SDMMC":        0.15,
    "DShot":        0.20,
    "Power_3V3":    0.20,
    "Power_5V":     0.30,
    "Power_GND":    0.30,
    "Power_VBAT":   0.40,
    "Default":      0.15,
}

# Net → class mapping (matches .kicad_pro net assignments)
NET_TO_CLASS = {
    "USB_DP":      "USB_diffpair",
    "SDMMC1_CLK":  "SDMMC", "SDMMC1_CMD": "SDMMC",
    "SDMMC1_D0":   "SDMMC", "SDMMC1_D1":  "SDMMC",
    "SDMMC1_D2":   "SDMMC", "SDMMC1_D3":  "SDMMC",
    "MOT1": "DShot", "MOT2": "DShot", "MOT3": "DShot",
    # everything else → Default
}


def mm(v):
    return pcbnew.FromMM(v)


def pad_lookup(brd, ref_padname):
    """Find a footprint pad by 'REFDES.PADNAME' string."""
    ref, padname = ref_padname.rsplit(".", 1)
    for fp in brd.GetFootprints():
        if fp.GetReference() == ref:
            for p in fp.Pads():
                if p.GetPadName() == padname:
                    return p
    raise ValueError(f"pad {ref_padname} not found")


def pad_layer(pad):
    ls = pad.GetLayerSet()
    if ls.Contains(F_CU): return F_CU
    if ls.Contains(B_CU): return B_CU
    return None


def add_track(brd, start_xy_mm, end_xy_mm, layer, width_mm, net_code):
    """Add a single PCB_TRACK segment. Returns the track object."""
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(mm(start_xy_mm[0]), mm(start_xy_mm[1])))
    t.SetEnd(pcbnew.VECTOR2I(mm(end_xy_mm[0]), mm(end_xy_mm[1])))
    t.SetLayer(layer)
    t.SetWidth(mm(width_mm))
    t.SetNetCode(net_code)
    t.SetLocked(True)
    brd.Add(t)
    return t


def add_via(brd, xy_mm, net_code, drill_mm=0.25, diam_mm=0.45):
    """Add a through via (F.Cu↔B.Cu). Returns the via object."""
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pcbnew.VECTOR2I(mm(xy_mm[0]), mm(xy_mm[1])))
    v.SetWidth(mm(diam_mm))
    v.SetDrill(mm(drill_mm))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(F_CU, B_CU)
    v.SetNetCode(net_code)
    v.SetLocked(True)
    brd.Add(v)
    return v


def route_L_path(brd, pad_a, pad_b, net_code, width_mm, prefer_horizontal_first=True):
    """L-shaped two-segment route in the SAME layer as pad_a (= pad_b layer).
    pad_a, pad_b on same layer. Returns the new track list."""
    pa = pad_a.GetPosition(); pb = pad_b.GetPosition()
    ax, ay = pcbnew.ToMM(pa.x), pcbnew.ToMM(pa.y)
    bx, by = pcbnew.ToMM(pb.x), pcbnew.ToMM(pb.y)
    layer = pad_layer(pad_a)
    if prefer_horizontal_first:
        knee = (bx, ay)
    else:
        knee = (ax, by)
    tracks = []
    tracks.append(add_track(brd, (ax, ay), knee, layer, width_mm, net_code))
    tracks.append(add_track(brd, knee, (bx, by), layer, width_mm, net_code))
    return tracks


def route_cross_layer(brd, pad_a, pad_b, net_code, width_mm, via_position=None):
    """Route from pad_a (on layer La) to pad_b (on layer Lb), Lb ≠ La.
    Place a via at via_position (defaults to pad_b XY)."""
    pa = pad_a.GetPosition(); pb = pad_b.GetPosition()
    ax, ay = pcbnew.ToMM(pa.x), pcbnew.ToMM(pa.y)
    bx, by = pcbnew.ToMM(pb.x), pcbnew.ToMM(pb.y)
    la = pad_layer(pad_a); lb = pad_layer(pad_b)
    if via_position is None:
        # Place via at pad_b XY by default — short B.Cu hop, longer F.Cu route
        vx, vy = bx, by
    else:
        vx, vy = via_position

    tracks = []
    # Segment 1: pad_a's layer from pad_a to (vx, vy)
    # Use L-shape on layer A
    tracks.append(add_track(brd, (ax, ay), (vx, ay), la, width_mm, net_code))
    if abs(vy - ay) > 0.01:
        tracks.append(add_track(brd, (vx, ay), (vx, vy), la, width_mm, net_code))
    # Via at (vx, vy)
    via = add_via(brd, (vx, vy), net_code)
    tracks.append(via)
    # Segment 2: pad_b's layer from via to pad_b
    if abs(vx - bx) > 0.01 or abs(vy - by) > 0.01:
        tracks.append(add_track(brd, (vx, vy), (bx, by), lb, width_mm, net_code))
    return tracks


def route_simple(brd, net_name, plan):
    """plan = list of pad-refdes strings; route consecutive pairs.
    Returns (status, added_items, note)."""
    net = brd.GetNetsByName().asdict().get(net_name)
    if net is None:
        # try string-keyed lookup
        for k, v in brd.GetNetsByName().asdict().items():
            if str(k) == net_name:
                net = v
                break
    if net is None:
        return "skip", [], f"net {net_name} not in netlist"
    net_code = net.GetNetCode()
    cls = NET_TO_CLASS.get(net_name, "Default")
    width = NETCLASS_WIDTH.get(cls, 0.15)

    pads = [pad_lookup(brd, p) for p in plan]
    added = []
    try:
        for a, b in zip(pads[:-1], pads[1:]):
            la, lb = pad_layer(a), pad_layer(b)
            if la == lb:
                added += route_L_path(brd, a, b, net_code, width)
            else:
                added += route_cross_layer(brd, a, b, net_code, width)
        return "routed", added, f"net_class={cls} width={width}mm via {len(plan)} pads"
    except Exception as e:
        return "fail", added, f"{type(e).__name__}: {e}"


# ============================================================================
# NET PLAN — per ROUTING_HANDOFF.md, API-measured pad positions
# (positions verified earlier; the plan here is the connection order)
# ============================================================================
NET_PLAN = {
    # Simple F.Cu shorts
    "HSE_OUT":    ["U1.13", "Y1.3", "C25.1"],     # MCU → crystal → load cap
    "USART1_RX":  ["U1.69", "J3.3"],               # MCU east → telem connector E
    "MOT1":       ["U1.34", "J11.1"],              # MCU N pin → ESC1 south
    "MOT2":       ["U1.35", "J12.1"],              # MCU N pin → ESC2 south
    "MOT3":       ["U1.22", "J13.1"],              # MCU W pin (long N→S)
    # F.Cu critical impedance — long, controlled geometry
    "USB_DP":     ["U5.6",  "U1.71"],              # USBLC6 → MCU; 90Ω diff geom via class
    # Cross-layer F.Cu↔B.Cu (vias)
    "I2C2_SDA":   ["U1.47", "R11.2", "U4.3"],      # F.Cu MCU + F.Cu pullup → B.Cu baro
    "I2C2_SCL":   ["U1.46", "R12.2", "U4.4"],      # same pattern
    "SWDIO":      ["U1.72", "J9.2"],               # F.Cu MCU → B.Cu SWD pin 2
    "SWCLK":      ["U1.76", "J9.4"],               # F.Cu MCU → B.Cu SWD pin 4
    "NRST":       ["U1.14", "C26.1", "J9.10"],     # F.Cu MCU+cap → B.Cu SWD pin 10
    # SDMMC family — hardest cluster
    "SDMMC1_CLK": ["U1.80", "J2.5"],               # MCU south → microSD on B.Cu
    "SDMMC1_CMD": ["U1.83", "J2.2", "R51.2"],      # MCU south → microSD + pullup
    "SDMMC1_D0":  ["U1.65", "J2.7", "R52.2"],
    "SDMMC1_D1":  ["U1.66", "J2.8", "R53.2"],
    "SDMMC1_D2":  ["U1.78", "J2.9", "R54.2"],
    "SDMMC1_D3":  ["U1.79", "J2.1", "R55.2"],
}


def main():
    print(f"[4d2] loading {PCB_PATH.name}")
    brd = pcbnew.LoadBoard(str(PCB_PATH))
    print(f"      pre-routed: {sum(1 for t in brd.GetTracks() if isinstance(t, pcbnew.PCB_TRACK))} tracks")

    results = []
    for net_name, plan in NET_PLAN.items():
        print(f"\n[4d2] routing {net_name}: {plan}")
        status, added, note = route_simple(brd, net_name, plan)
        print(f"      → {status}: {note} ({len(added)} items added)")
        results.append({"net": net_name, "plan": plan, "status": status,
                        "items_added": len(added), "note": note})

    # Save board
    print(f"\n[4d2] saving board with new locked tracks")
    pcbnew.SaveBoard(str(PCB_PATH), brd)
    print(f"      saved {PCB_PATH}")

    # Run DRC
    print(f"\n[4d2] kicad-cli pcb drc")
    drc = subprocess.run(
        ["kicad-cli", "pcb", "drc", "--severity-error", "--exit-code-violations",
         "--units", "mm", str(PCB_PATH)],
        capture_output=True, text=True,
    )
    print(drc.stdout.strip().splitlines()[-1] if drc.stdout else "(no DRC output)")

    # Cleanup DRC report
    drc_rpt = HERE / "novapcb-layout-drc.rpt"
    if drc_rpt.exists():
        drc_text = drc_rpt.read_text()
        drc_rpt.unlink()
    else:
        drc_text = ""

    n_routed = sum(1 for r in results if r["status"] == "routed")
    n_failed = sum(1 for r in results if r["status"] == "fail")
    summary = {
        "total_nets": len(NET_PLAN),
        "routed_attempted": n_routed,
        "fail_during_add": n_failed,
        "drc_exit_code": drc.returncode,
        "drc_violations_summary": [l for l in drc.stdout.splitlines() if "violations" in l.lower() or "errors" in l.lower()][:5],
    }

    out = {"per_net": results, "summary": summary, "drc_excerpt": drc_text[:2000]}
    (HERE / "phase-4d2-results.json").write_text(json.dumps(out, indent=2))
    print(f"\nSUMMARY: {summary}")
    print(f"Details: {HERE / 'phase-4d2-results.json'}")
    return out


if __name__ == "__main__":
    main()
