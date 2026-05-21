#!/usr/bin/env python3
"""Step 6 precursor — final tool-side attempt before going manual.

Per master 2026-05-21 guidance: a TRULY pristine 2-layer DSN with NO
leftover wiring, NO plane nets, NO inner layers, NO inner-layer padstack
shapes. Test if Freerouting reaches Pass #1 in <15 min. If yes → use the
SES. If hang → kill + go to manual per-net.

Pristine recipe:
  1. Strip EVERY track + via on the board (signal AND plane).
  2. Save board, export DSN.
  3. Patch DSN:
     - Delete In1..In4 layer declarations.
     - Delete (plane ... InN.Cu ...) declarations.
     - Remove plane nets (GND, +3V3, +3V3A, +5V) from the kicad_default
       class net list AND delete their (net NETNAME (pins ...)) blocks.
     - Strip inner-layer shapes from every padstack.
  4. Run Freerouting -mt 4 -mp 100 with a 15-min hard timeout.
  5. If SES present + non-trivial → import + refill zones + DRC.
  6. After signal routing: separately re-add plane stitch vias for
     plane-net pads on F.Cu/B.Cu (handled by a follow-up script).
"""
import os
import sys
import time
import re
import subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DSN = os.path.join(HERE, "novapcb-layout-v1.1.dsn")
SES = os.path.join(HERE, "novapcb-layout-v1.1.ses")
LOG = os.path.join(HERE, "freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
FR_JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

PLANE_NETS = ["GND", "+3V3", "+3V3A", "+5V"]
FREEROUTING_TIMEOUT = 900  # 15 min hard cap per master


def strip_everything(brd):
    """Remove every track + via. Keep zones + footprints intact."""
    n_t = n_v = 0
    for t in list(brd.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA):
            brd.Remove(t); n_v += 1
        else:
            brd.Remove(t); n_t += 1
    return n_t, n_v


def patch_pristine(dsn_path):
    """Delete inner layers, inner planes, plane nets, inner padstack shapes."""
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
    # Drop inner-layer shapes from padstacks
    for L in inner:
        text = re.sub(r"\s*\(shape \([^()]+\b" + re.escape(L) + r"\b[^()]*\)\)",
                      "", text)
    # Drop plane nets from kicad_default class. The class is in the
    # network block as `(class kicad_default <net-tokens-space-or-newline> (circuit ...) (rule ...))`.
    # We tokenize the net list, remove the plane net names, write back.
    m = re.search(
        r"(\(class kicad_default\s+)([^()]+?)(\s*\(circuit[\s\S]*?\)\s*"
        r"\(rule[\s\S]*?\)\s*)\)",
        text)
    if not m:
        print(f"      !! could not locate kicad_default class")
        return 0
    nets_raw = m.group(2)
    kept_nets = [t for t in nets_raw.split() if t not in PLANE_NETS]
    n_dropped = len(nets_raw.split()) - len(kept_nets)
    # Re-format with line breaks at ~70 chars
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
    # Drop (net NETNAME (pins ...)) blocks for plane nets — these
    # blocks declare the pin lists for each net to Freerouting; without
    # them, Freerouting won't see plane-net pads at all.
    n_net = 0
    for N in PLANE_NETS:
        pat = r"\s*\(net " + re.escape(N) + r"\s*\(pins[\s\S]*?\)\s*\)"
        text, n = re.subn(pat, "", text)
        n_net += n
    print(f"      pristine patch: -{n_layer} layers, -{n_plane} planes, "
          f"-{n_dropped} plane nets from class, -{n_net} (net ...) blocks")
    if n_layer != 4 or n_plane != 4 or n_dropped != 4 or n_net != 4:
        print(f"      !! expected 4 each; got {n_layer}/{n_plane}/{n_dropped}/{n_net}")
        return 0
    with open(dsn_path, "w") as f:
        f.write(text)
    return 1


def main():
    print("[1] load board + strip every track/via")
    brd = pcbnew.LoadBoard(PCB)
    n_t, n_v = strip_everything(brd)
    print(f"    removed {n_t} tracks + {n_v} vias")
    # Refill zones on same board object (proven to work)
    zones = list(brd.Zones())
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(zones)
    pcbnew.SaveBoard(PCB, brd)

    print("[2] export DSN")
    if os.path.exists(DSN): os.remove(DSN)
    ok = pcbnew.ExportSpecctraDSN(brd, DSN)
    if not ok:
        print("    !! export failed"); sys.exit(2)
    print(f"    DSN: {os.path.getsize(DSN)} bytes")

    print("[3] pristine patch DSN")
    if patch_pristine(DSN) != 1:
        sys.exit(3)
    print(f"    patched DSN: {os.path.getsize(DSN)} bytes")

    print(f"[4] run Freerouting -mt 4 -mp 100 (hard timeout {FREEROUTING_TIMEOUT}s)")
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
            print(f"    !! TIMEOUT at {FREEROUTING_TIMEOUT}s — Freerouting hung again")
            timed_out = True
            rc = -1
    elapsed = time.time() - t0
    print(f"    elapsed {elapsed/60:.1f} min, rc={rc}, ses_size="
          f"{os.path.getsize(SES) if os.path.exists(SES) else 0}")

    # Parse pass log
    with open(LOG) as f:
        log = f.read()
    passes = re.findall(
        r"Auto-router pass #(\d+) .*?completed in [^.]+\..*?score of ([\d.]+) ?(?:\((\d+) unrouted\))?",
        log)
    if passes:
        last = passes[-1]
        print(f"    last pass: #{last[0]} score={last[1]} unrouted={last[2] or 'unknown'}")
    else:
        print(f"    NO PASS LOGS — Freerouting hung in pre-route phase")

    if timed_out or not os.path.exists(SES) or os.path.getsize(SES) < 1000:
        print(f"\n  ★ VERDICT: Freerouting unusable. Go to manual per-net post-process.")
        sys.exit(10)

    print("[5] import SES + refill zones + save")
    brd2 = pcbnew.LoadBoard(PCB)
    ok = pcbnew.ImportSpecctraSES(brd2, SES)
    if not ok:
        print("    !! ImportSpecctraSES failed"); sys.exit(5)
    fzones = list(brd2.Zones())
    pcbnew.ZONE_FILLER(brd2).Fill(fzones)
    pcbnew.SaveBoard(PCB, brd2)
    nt = sum(1 for t in brd2.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))
    nv = sum(1 for t in brd2.GetTracks() if isinstance(t, pcbnew.PCB_VIA))
    print(f"    post-import: {nt} tracks, {nv} vias")

    print("[6] DRC")
    out = os.path.join(HERE, "drc_report.txt")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--format", "report", "--output", out, PCB],
                   capture_output=True)
    txt = open(out).read()
    m_err = re.search(r"Found (\d+) DRC violation", txt)
    m_unc = re.search(r"Found (\d+) unconnected item", txt)
    n_err = int(m_err.group(1)) if m_err else 0
    n_unc = int(m_unc.group(1)) if m_unc else 0
    print(f"    DRC: {n_err} errors, {n_unc} unconnected (note: plane nets unconnected too — re-stitch separately)")

    print(f"\n  ★ VERDICT: signal-route done. NEXT: re-stitch plane nets to plane fills + USB hand-route check + geometry verification.")


if __name__ == "__main__":
    main()
