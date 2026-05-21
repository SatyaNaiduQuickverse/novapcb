#!/usr/bin/env python3
"""Step 6 precursor — vias-first re-route per master 2026-05-21 directive.

Order matters: power/ground vias are constrained (need spots near each
plane pad); signals are flexible (route around things). So:

  1. Strip signal routing (629 tracks + 70 vias from prior pristine run).
  2. On BARE board, place all ~141 plane-net stitch vias at pad centers.
     With no signal traces in the way, all get short connections under
     U1's dense pin grid too.
  3. Re-pour plane fills around the new vias.
  4. Re-run pristine 2-layer Freerouting for signals. Vias from step 2
     are in the DSN's (wiring) section -> Freerouting routes signals
     around them.
  5. Re-pour fills.

Result: clean by construction. Better PDN (every plane pad gets a SHORT
via right at the pad, no long stub-traces-around-obstacles).
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

PLANE_NETS = ["GND", "+3V3", "+3V3A", "+5V"]
VIA_OUTER_MM = 0.60
VIA_DRILL_MM = 0.30
FREEROUTING_TIMEOUT = 900


def strip_signal_only(brd):
    """Remove every track + via on signal nets. KEEP plane-net tracks."""
    n_t = n_v = kept = 0
    for t in list(brd.GetTracks()):
        net = t.GetNet()
        net_name = str(net.GetNetname()) if net else ""
        if net_name in PLANE_NETS:
            kept += 1; continue
        if isinstance(t, pcbnew.PCB_VIA):
            brd.Remove(t); n_v += 1
        else:
            brd.Remove(t); n_t += 1
    return n_t, n_v, kept


def place_plane_stitch_vias(brd):
    """For each plane-net SMD pad on outer layers, place a through-via
    at the pad center. On a bare board this trivially has no collisions."""
    placed = 0
    skipped_th = 0
    fps = list(brd.GetFootprints())
    print(f"    iterating {len(fps)} footprints", flush=True)
    for fp_idx, fp in enumerate(fps):
        ref = fp.GetReference()
        print(f"    fp{fp_idx}/{len(fps)} {ref}", flush=True)
        pads = list(fp.Pads())
        for pad_idx, pad in enumerate(pads):
            if not pad.GetNet(): continue
            net_name = str(pad.GetNet().GetNetname())
            if net_name not in PLANE_NETS: continue
            if not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)):
                continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                skipped_th += 1
                continue
            bb = pad.GetBoundingBox()
            cx = bb.GetX() + bb.GetWidth() // 2
            cy = bb.GetY() + bb.GetHeight() // 2
            try:
                via = pcbnew.PCB_VIA(brd)
                via.SetPosition(pcbnew.VECTOR2I(cx, cy))
                via.SetWidth(int(VIA_OUTER_MM * 1e6))
                via.SetDrill(int(VIA_DRILL_MM * 1e6))
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                via.SetNet(pad.GetNet())
                brd.Add(via)
                placed += 1
                if placed % 30 == 0:
                    print(f"    ... placed {placed}", flush=True)
            except Exception as e:
                print(f"    EXC at {fp.GetReference()}.{pad.GetNumber()} ({net_name}): {e}",
                      flush=True)
                raise
    return placed, skipped_th


def pristine_patch_dsn(dsn_path):
    """Same as run_pristine_2layer.py patch: omit inner layers + plane
    nets from DSN. The plane vias placed in step 2 go into (wiring) as
    F.Cu+B.Cu vias on plane nets — those plane nets are removed from
    the DSN class but their (wiring) entries should still register as
    obstacles via the placed-component pads or via decls.

    Returns 1 on success."""
    with open(dsn_path) as f:
        text = f.read()
    inner = ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]
    n_layer = 0
    for L in inner:
        pat = (r"\s*\(layer " + re.escape(L) +
               r"\s*\n\s*\(type signal\)\s*\n\s*\(property\s*\n\s*"
               r"\(index \d+\)\s*\n\s*\)\s*\n\s*\)")
        text, n = re.subn(pat, "", text)
        n_layer += n
    n_plane = 0
    for L in inner:
        pat = r"\s*\(plane \S+ \(polygon " + re.escape(L) + r"[\s\S]*?\)\)"
        text, n = re.subn(pat, "", text)
        n_plane += n
    for L in inner:
        text = re.sub(r"\s*\(shape \([^()]+\b" + re.escape(L) + r"\b[^()]*\)\)",
                      "", text)
    m = re.search(
        r"(\(class kicad_default\s+)([^()]+?)(\s*\(circuit[\s\S]*?\)\s*"
        r"\(rule[\s\S]*?\)\s*)\)",
        text)
    if not m: return 0
    nets_raw = m.group(2)
    kept_nets = [t for t in nets_raw.split() if t not in PLANE_NETS]
    def fmt(nets, indent=6):
        out, line = "", " " * indent
        for n in nets:
            piece = (" " if line.strip() else "") + n
            if len(line) + len(piece) > 75:
                out += line + "\n"; line = " " * indent + n
            else:
                line += piece
        if line.strip(): out += line + "\n"
        return out
    new_block = m.group(1) + "\n" + fmt(kept_nets) + m.group(3) + ")"
    text = text.replace(m.group(0), new_block)
    n_net = 0
    for N in PLANE_NETS:
        pat = r"\s*\(net " + re.escape(N) + r"\s*\(pins[\s\S]*?\)\s*\)"
        text, n = re.subn(pat, "", text)
        n_net += n
    # ALSO strip (wire (via ...) ...) entries on plane nets so Freerouting
    # doesn't see plane-net vias as belonging to unknown nets — keep them
    # as obstacles only via the keepout / clearance from the via shape.
    # Actually for via-as-obstacle: KEEP the via in the (wiring) section
    # but make it (type fix) so Freerouting treats it as an immovable
    # F.Cu+B.Cu obstacle. The plane-net name in the via entry is OK
    # because Freerouting will just ignore the net (no class with that net).
    print(f"      pristine patch: -{n_layer} layers, -{n_plane} planes, "
          f"-{len(nets_raw.split()) - len(kept_nets)} plane nets from class, "
          f"-{n_net} (net ...) blocks")
    if n_layer != 4 or n_plane != 4 or n_net != 4:
        return 0
    with open(dsn_path, "w") as f:
        f.write(text)
    return 1


def drc_summary():
    out = "/tmp/drc_vfr.txt"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report", "--output", out, PCB],
                   capture_output=True)
    txt = open(out).read()
    n_err = int(re.search(r"Found (\d+) DRC violation", txt).group(1)) if re.search(r"Found \d+ DRC violation", txt) else None
    n_unc = int(re.search(r"Found (\d+) unconnected", txt).group(1)) if re.search(r"Found \d+ unconnected", txt) else None
    return n_err, n_unc


def main():
    print("[1+2+3] single board lifecycle: strip + place vias + fill + save", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    nt, nv, kept = strip_signal_only(brd)
    print(f"    stripped {nt} signal tracks + {nv} signal vias; kept {kept} plane tracks/vias",
          flush=True)
    placed, th = place_plane_stitch_vias(brd)
    print(f"    placed {placed} plane vias; skipped {th} TH pads", flush=True)
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    # Also export DSN now while we have the in-memory board (KiCad 9 SWIG
    # corrupts the BOARD object on LoadBoard-after-SaveBoard in the same
    # process — do the DSN export here, then save.
    if os.path.exists(DSN): os.remove(DSN)
    if not pcbnew.ExportSpecctraDSN(brd, DSN):
        sys.exit(2)
    pcbnew.SaveBoard(PCB, brd)
    print(f"    saved board + exported DSN ({os.path.getsize(DSN)} bytes)", flush=True)

    print("[3b] check post-via DRC", flush=True)
    n_err, n_unc = drc_summary()
    print(f"    DRC: {n_err} errors, {n_unc} unconnected", flush=True)
    if n_err > 0:
        print(f"    !! placing vias introduced DRC errors — investigate first 5:")
        with open("/tmp/drc_vfr.txt") as f:
            for line in [l for l in f if l.startswith("[")][:5]:
                print(f"      {line.strip()}")
        sys.exit(3)

    print("[4] pristine patch DSN (signals only)", flush=True)
    if not pristine_patch_dsn(DSN):
        sys.exit(4)

    print(f"[5] run Freerouting -mt 4 -mp 100 (timeout {FREEROUTING_TIMEOUT}s)", flush=True)
    if os.path.exists(SES): os.remove(SES)
    t0 = time.time()
    cmd = [JAVA, "-Dgui.enabled=false", "-jar", FR_JAR,
           "-de", DSN, "-do", SES, "-mt", "4", "-mp", "100"]
    timed_out = False
    with open(LOG, "w") as logf:
        try:
            result = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT,
                                    timeout=FREEROUTING_TIMEOUT)
            rc = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True; rc = -1
    elapsed = time.time() - t0
    print(f"    elapsed {elapsed/60:.1f} min, rc={rc}")
    if timed_out or not os.path.exists(SES) or os.path.getsize(SES) < 1000:
        print("    !! Freerouting hang/fail with vias as obstacles")
        sys.exit(6)

    print("[7] import SES + refill + save")
    brd3 = pcbnew.LoadBoard(PCB)
    if not pcbnew.ImportSpecctraSES(brd3, SES):
        sys.exit(7)
    pcbnew.ZONE_FILLER(brd3).Fill(list(brd3.Zones()))
    pcbnew.SaveBoard(PCB, brd3)
    nt2 = sum(1 for t in brd3.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))
    nv2 = sum(1 for t in brd3.GetTracks() if isinstance(t, pcbnew.PCB_VIA))
    print(f"    post-import: {nt2} tracks, {nv2} vias")

    print("[8] final DRC")
    n_err, n_unc = drc_summary()
    print(f"    DRC: {n_err} errors, {n_unc} unconnected")
    print("\n  Next: USB hand-route + geometry verification.")


if __name__ == "__main__":
    main()
