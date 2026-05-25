#!/usr/bin/env python3
"""
Accumulating Freerouting iteration — preserves prior routing.

Per master directive 2026-05-21: "Run -> import the SES -> run again,
accumulating passes to drive the 38 down."

Unlike run_pristine_2layer.py which strips tracks before each export
(fresh start each time), this script PRESERVES the current routed
state — Freerouting sees existing tracks as pre-routed and works on
the remaining unrouted nets.

Workflow per invocation:
  1. Load current board (with prior routes + plane vias)
  2. Strip plane-net vias only (will be re-added at end)
  3. Export DSN (existing signal tracks preserved as "wiring")
  4. Pristine-patch DSN (remove inner-layer/plane decls)
  5. Freerouting -Xmx 6g -mp 10 (stable bounded run)
  6. Import SES — merges new routing with existing
  7. Re-apply plane stitch via run_stitch_plane_nets.py logic
  8. Apply fix_stitch_violations.py
  9. Report unrouted count

Stable: never -mp 100 (OOM lesson). Always Xmx 6g.
"""
import os, sys, time, re, subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DSN = os.path.join(HERE, "novapcb-layout-v1.1.dsn")
SES = os.path.join(HERE, "novapcb-layout-v1.1.ses")
LOG = os.path.join(HERE, "freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
FR_JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")
PLANE_NETS = ["GND", "+3V3", "+3V3A", "+5V"]
TIMEOUT = 1500


def patch_pristine(dsn_path):
    """Patch DSN: remove inner-layer + plane decls + plane nets."""
    with open(dsn_path) as f: text = f.read()
    inner = ["In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu"]
    for L in inner:
        pat = (r"\s*\(layer " + re.escape(L) +
               r"\s*\n\s*\(type signal\)\s*\n\s*\(property\s*\n\s*"
               r"\(index \d+\)\s*\n\s*\)\s*\n\s*\)")
        text = re.sub(pat, "", text)
    for L in inner:
        pat = r"\s*\(plane \S+ \(polygon " + re.escape(L) + r"[\s\S]*?\)\)"
        text = re.sub(pat, "", text)
    for L in inner:
        text = re.sub(r"\s*\(shape \([^()]+\b" + re.escape(L) + r"\b[^()]*\)\)", "", text)
    m = re.search(
        r"(\(class kicad_default\s+)([^()]+?)(\s*\(circuit[\s\S]*?\)\s*"
        r"\(rule[\s\S]*?\)\s*)\)", text)
    if m:
        nets_raw = m.group(2)
        kept = [t for t in nets_raw.split() if t not in PLANE_NETS]
        def fmt(nets, indent=6):
            out, line = "", " " * indent
            for n in nets:
                piece = (" " if line.strip() else "") + n
                if len(line) + len(piece) > 75:
                    out += line + "\n"; line = " " * indent + n
                else: line += piece
            if line.strip(): out += line + "\n"
            return out
        new_block = m.group(1) + "\n" + fmt(kept) + m.group(3) + ")"
        text = text.replace(m.group(0), new_block)
    for N in PLANE_NETS:
        pat = r"\s*\(net " + re.escape(N) + r"\s*\(pins[\s\S]*?\)\s*\)"
        text = re.sub(pat, "", text)
    with open(dsn_path, "w") as f: f.write(text)


def strip_plane_vias_only(brd):
    """Remove only plane-net vias (preserve signal-route tracks + vias)."""
    n = 0
    for t in list(brd.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA):
            netname = t.GetNetname() or ""
            if netname in PLANE_NETS:
                brd.Remove(t); n += 1
    return n


def main():
    print(f"[1] load current board (preserve existing routing)")
    brd = pcbnew.LoadBoard(PCB)
    n_tracks_before = sum(1 for t in brd.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))
    n_vias_before = sum(1 for t in brd.GetTracks() if isinstance(t, pcbnew.PCB_VIA))
    print(f"    pre-iter: {n_tracks_before} tracks, {n_vias_before} vias")
    print(f"[2] strip plane-net vias (will re-stitch at end)")
    nv = strip_plane_vias_only(brd)
    print(f"    stripped {nv} plane vias")
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)

    print(f"[3] export DSN (preserves signal routes as 'wiring')")
    if os.path.exists(DSN): os.remove(DSN)
    brd2 = pcbnew.LoadBoard(PCB)
    ok = pcbnew.ExportSpecctraDSN(brd2, DSN)
    print(f"    DSN: {os.path.getsize(DSN)} bytes, ok={ok}")
    print(f"[4] pristine-patch DSN")
    patch_pristine(DSN)
    print(f"    patched: {os.path.getsize(DSN)} bytes")

    print(f"[5] run Freerouting -Xmx 6g -mp 10 (stable bounded)")
    if os.path.exists(SES): os.remove(SES)
    t0 = time.time()
    cmd = [JAVA, "-Xmx6g", "-Dgui.enabled=false", "-jar", FR_JAR,
           "-de", DSN, "-do", SES, "-mt", "4", "-mp", "10"]
    with open(LOG, "w") as logf:
        try:
            result = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            print(f"    TIMEOUT at {TIMEOUT}s — Pi capacity issue, stopping")
            sys.exit(1)
    elapsed = time.time() - t0
    print(f"    elapsed {elapsed/60:.1f} min, ses={os.path.getsize(SES) if os.path.exists(SES) else 0} bytes")
    with open(LOG) as f: log = f.read()
    m = re.findall(r"Auto-router pass #(\d+) .*?score of ([\d.]+) \((\d+) unrouted\)", log)
    if m:
        last = m[-1]
        print(f"    last pass: #{last[0]} unrouted={last[2]}")

    if not os.path.exists(SES) or os.path.getsize(SES) < 1000:
        print(f"    no usable SES — Pi capacity issue, stopping"); sys.exit(2)

    print(f"[6] import SES")
    brd3 = pcbnew.LoadBoard(PCB)
    pcbnew.ImportSpecctraSES(brd3, SES)
    pcbnew.ZONE_FILLER(brd3).Fill(list(brd3.Zones()))
    pcbnew.SaveBoard(PCB, brd3)
    n_tracks = sum(1 for t in brd3.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))
    n_vias = sum(1 for t in brd3.GetTracks() if isinstance(t, pcbnew.PCB_VIA))
    print(f"    post-import: {n_tracks} tracks, {n_vias} vias (delta: +{n_tracks - n_tracks_before} tracks, +{n_vias - (n_vias_before - nv)} vias)")

    print(f"[7] re-apply plane stitch")
    subprocess.run(["python3", os.path.join(HERE, "run_stitch_plane_nets.py")], check=False)
    print(f"[8] re-apply stitch violation fixes")
    subprocess.run(["python3", os.path.join(HERE, "fix_stitch_violations.py")], check=False)

    print(f"[9] final DRC")
    out = subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "report",
                          "--output", "/tmp/v1.1_drc_iter.txt", "--units", "mm", PCB],
                         capture_output=True, text=True)
    for L in out.stdout.split("\n"):
        if "Found" in L: print(f"    {L.strip()}")


if __name__ == "__main__":
    main()
