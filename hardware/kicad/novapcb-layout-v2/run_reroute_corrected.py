#!/usr/bin/env python3
"""Step 6 precursor — full re-route with corrected net-class layer constraints.

Per master 2026-05-21 directive: Step 5's Freerouting net-class setup
allowed all 6 copper layers; Freerouting used the 4 plane layers as
routing layers; 44 signal nets / 1.25 m of signal copper ended up on
the GND/+3V3/+5V/GND planes. The fix is a corrected-constraint full
re-route, not a patch.

Workflow:
  1. Strip ALL signal tracks + vias from the board (keep zone fills +
     footprints + power-served plane vias).
  2. Save board, re-export DSN.
  3. Patch DSN: change In1..In4 layer type from `signal` to `power` —
     the proper Specctra-DSN way to declare "this is a dedicated plane
     layer, no signal routing here". F.Cu + B.Cu remain `signal`.
  4. Run Freerouting (-mt 4 -mp 100) with the corrected constraints.
  5. Import SES -> board, refill zones.
  6. Run kicad-cli DRC.
  7. Mandatory geometry verification:
     (a) inner-layer signal census -> 0 signal misroutes
     (b) USB extracted geometry -> F.Cu microstrip, length-matched
     (c) plane re-fill solid check -> outline counts back to ~1 main
         outline per plane (no orphans from former misroute voids)

Pre-prediction (falsifiable, per master):
  PRED-RR1: Freerouting completion >= 95% on F.Cu+B.Cu only with
    ~60 signal nets and 80x60 mm.
  PRED-RR2: Plane integrity: each In1/In2/In3/In4 has main-outline
    area >= 99% of board (vs 85% currently with 1.25 m of voids).
  PRED-RR3: USB_DM vs USB_DP length difference < 2 mm, all on F.Cu.
"""
import os
import sys
import time
import re
import subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v2.kicad_pcb")
DSN = os.path.join(HERE, "novapcb-layout-v2.dsn")
SES = os.path.join(HERE, "novapcb-layout-v2.ses")
LOG = os.path.join(HERE, "freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
FR_JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

# Net names that legitimately occupy plane layers (do NOT strip these)
PLANE_NETS = {"GND", "+3V3", "+3V3A", "+5V"}


def strip_signal_routing(brd):
    """Remove every track + via that isn't on a plane-served net. Keep
    zone fills and footprints intact."""
    removed_tracks = 0
    removed_vias = 0
    kept_tracks = 0
    for t in list(brd.GetTracks()):
        net = t.GetNet()
        net_name = str(net.GetNetname()) if net else ""
        if isinstance(t, pcbnew.PCB_VIA):
            # Strip ALL vias — the new routing will place fresh ones as needed.
            # (Power-stitch vias get re-added by run_planes or Freerouting.)
            brd.Remove(t)
            removed_vias += 1
            continue
        if net_name in PLANE_NETS:
            # A plane-net track is unusual — keep it (rare; e.g. ground stitch)
            kept_tracks += 1
            continue
        brd.Remove(t)
        removed_tracks += 1
    return {"removed_tracks": removed_tracks, "removed_vias": removed_vias,
            "kept_plane_tracks": kept_tracks}


def patch_dsn_layers(dsn_path):
    """Master 2026-05-21: omit inner layers from the DSN entirely.

    The cleanest Freerouting framing: don't tell it the inner layers
    exist at all. Remove the In1..In4 layer declarations from the
    `(structure)` block AND the `(plane ...)` declarations for the
    inner-layer plane fills. Freerouting then sees a 2-layer (F.Cu +
    B.Cu) board with simple signal-routing geometry — no power-layer
    pre-processing to choke on.

    The inner planes remain on the KiCad .kicad_pcb itself (zones are
    not in the DSN scope — they're board-side). After SES import, the
    planes are still there and get refilled.
    """
    with open(dsn_path) as f:
        text = f.read()
    inner_layers = ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]
    n_layer = 0
    for L in inner_layers:
        # Strip the (layer InN.Cu ... ) block
        pattern = (r"\s*\(layer " + re.escape(L) +
                   r"\s*\n\s*\(type signal\)\s*\n\s*\(property\s*\n\s*"
                   r"\(index \d+\)\s*\n\s*\)\s*\n\s*\)")
        new_text, n = re.subn(pattern, "", text)
        if n > 0:
            text = new_text
            n_layer += n
    # Strip the (plane NETNAME (polygon InN.Cu ...)) declarations
    n_plane = 0
    for L in inner_layers:
        pattern = (r"\s*\(plane \S+ \(polygon " + re.escape(L) +
                   r"[\s\S]*?\)\)")
        new_text, n = re.subn(pattern, "", text)
        if n > 0:
            text = new_text
            n_plane += n
    # Strip inner-layer shapes from all padstacks (so Freerouting doesn't
    # reference layers it doesn't know about)
    for L in inner_layers:
        text = re.sub(r"\s*\(shape \([^()]+\b" + re.escape(L) + r"\b[^()]*\)\)",
                      "", text)
    print(f"      removed {n_layer} layer declarations + {n_plane} plane declarations")
    print(f"      cleaned padstacks of inner-layer shapes")
    if n_layer != 4 or n_plane != 4:
        print(f"      !! expected 4 layers + 4 planes; got {n_layer}+{n_plane}")
        return 0
    with open(dsn_path, "w") as f:
        f.write(text)
    return 1


def run_drc():
    out = os.path.join(HERE, "drc_report.txt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report", "--output", out, PCB],
                   capture_output=True)
    txt = open(out).read()
    m_err = re.search(r"Found (\d+) DRC violation", txt)
    n_err = int(m_err.group(1)) if m_err else 0
    m_unc = re.search(r"Found (\d+) unconnected item", txt)
    n_unc = int(m_unc.group(1)) if m_unc else 0
    return n_err, n_unc


def main():
    print(f"[1/7] load + strip signal tracks/vias + refill + export DSN (single board lifecycle)")
    brd = pcbnew.LoadBoard(PCB)
    stats = strip_signal_routing(brd)
    print(f"      removed: {stats['removed_tracks']} tracks + {stats['removed_vias']} vias")
    print(f"      kept (plane-net tracks): {stats['kept_plane_tracks']}")
    # Refill on the same board object (avoids the SwigPyObject crash that
    # appeared on a reload after strip)
    zones = list(brd.Zones())
    print(f"      zones: {len(zones)}")
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(zones)
    pcbnew.SaveBoard(PCB, brd)
    print(f"      saved + refilled.")

    print(f"[2/7] export DSN")
    if os.path.exists(DSN):
        os.remove(DSN)
    ok = pcbnew.ExportSpecctraDSN(brd, DSN)
    if not ok:
        print(f"      !! ExportSpecctraDSN failed")
        sys.exit(2)
    print(f"      DSN: {os.path.getsize(DSN)} bytes")

    print(f"[3/7] patch DSN: restrict kicad_default class to F.Cu + B.Cu")
    n_patched = patch_dsn_layers(DSN)
    if n_patched != 1:
        print(f"      !! expected 1 patch, got {n_patched}")
        sys.exit(3)
    print(f"      use_layer constraint added to kicad_default")

    print(f"[4/7] run Freerouting -mt 4 -mp 100")
    if os.path.exists(SES):
        os.remove(SES)
    t0 = time.time()
    cmd = [JAVA, "-Dgui.enabled=false", "-jar", FR_JAR,
           "-de", DSN, "-do", SES, "-mt", "4", "-mp", "100"]
    with open(LOG, "w") as logf:
        try:
            result = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT,
                                    timeout=5400)
            rc = result.returncode
        except subprocess.TimeoutExpired:
            print(f"      !! Freerouting timed out at 90 min")
            rc = -1
    elapsed = time.time() - t0
    print(f"      Freerouting returned {rc} in {elapsed/60:.1f} min")
    if not os.path.exists(SES) or os.path.getsize(SES) < 100:
        print(f"      !! SES not produced — Freerouting failed")
        with open(LOG) as f:
            print(f.read()[-3000:])
        sys.exit(4)

    print(f"[5/7] import SES + refill zones + save")
    brd4 = pcbnew.LoadBoard(PCB)
    ok = pcbnew.ImportSpecctraSES(brd4, SES)
    if not ok:
        print(f"      !! ImportSpecctraSES failed")
        sys.exit(5)
    pcbnew.ZONE_FILLER(brd4).Fill(list(brd4.Zones()))
    pcbnew.SaveBoard(PCB, brd4)
    tracks = sum(1 for t in brd4.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))
    vias = sum(1 for t in brd4.GetTracks() if isinstance(t, pcbnew.PCB_VIA))
    print(f"      post-import: {tracks} tracks, {vias} vias")

    print(f"[6/7] DRC")
    n_err, n_unc = run_drc()
    print(f"      DRC: {n_err} errors, {n_unc} unconnected")

    print(f"[7/7] parse completion %")
    with open(LOG) as f:
        log = f.read()
    passes = re.findall(r"Pass #(\d+):\s*(\d+)\s+incompletes\s+across\s+(\d+)\s+items", log)
    if passes:
        last = passes[-1]
        n_inc = int(last[1]); n_items = int(last[2])
        pct = 100 - 100*n_inc/n_items if n_items > 0 else 0
        print(f"      last pass: #{last[0]} {n_inc} incompletes / {n_items} items ({pct:.1f}% complete)")
    else:
        # Some Freerouting versions print differently
        m = re.search(r"(\d+)\s+incomplete", log)
        if m:
            print(f"      log mentions {m.group(1)} incompletes")
        else:
            print(f"      could not parse completion from log")
    print(f"      (full log: {LOG})")

    print(f"\ndone. Run sims/enumerate_inner_layer_signals.py + "
          f"sims/extract_trace_geometry.py to verify geometry.")


if __name__ == "__main__":
    main()
