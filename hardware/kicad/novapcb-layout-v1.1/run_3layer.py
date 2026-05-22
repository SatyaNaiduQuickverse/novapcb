#!/usr/bin/env python3
"""3-signal-layer Freerouting run (master 2026-05-22 layer-rebalance).

NEW stackup: L1 (F.Cu) signal / L2 (In1) GND / L3 (In2) +3V3 /
L4 (In3) SIGNAL / L5 (In4) GND / L6 (B.Cu) signal.

Patches DSN to:
  - KEEP In3.Cu as a signal layer (was previously stripped)
  - REMOVE In1.Cu, In2.Cu, In4.Cu (still planes)
  - +5V is no longer a plane — Freerouting routes it as a signal net.
  - GND and +3V3 remain plane nets (excluded from class list as before).

Master's expectation: ~100% completion. Fallback if not: convert L3
too (4-signal).
"""
import os, sys, time, re, subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")
DSN = os.path.join(HERE, "novapcb-layout-v1.1.dsn")
SES = os.path.join(HERE, "novapcb-layout-v1.1.ses")
LOG = os.path.join(HERE, "freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
FR_JAR = os.path.expanduser("~/local/freerouting/versions/freerouting-2.2.3.jar")

# Now only In1/In2/In4 are stripped — In3 stays as routable signal layer.
STRIP_LAYERS = ["In1.Cu", "In2.Cu", "In4.Cu"]
PLANE_NETS = ["GND", "+3V3"]   # +5V is NO LONGER a plane net
TIMEOUT = 3300


def patch_3layer(dsn_path):
    with open(dsn_path) as f:
        text = f.read()
    n_layer = 0
    for L in STRIP_LAYERS:
        pat = (r"\s*\(layer " + re.escape(L) +
               r"\s*\n\s*\(type signal\)\s*\n\s*\(property\s*\n\s*"
               r"\(index \d+\)\s*\n\s*\)\s*\n\s*\)")
        text, n = re.subn(pat, "", text)
        n_layer += n
    n_plane = 0
    for L in STRIP_LAYERS:
        pat = r"\s*\(plane \S+ \(polygon " + re.escape(L) + r"[\s\S]*?\)\)"
        text, n = re.subn(pat, "", text)
        n_plane += n
    for L in STRIP_LAYERS:
        text = re.sub(r"\s*\(shape \([^()]+\b" + re.escape(L) + r"\b[^()]*\)\)",
                      "", text)
    # Drop plane nets (GND, +3V3 only — +5V is NOT a plane now)
    m = re.search(
        r"(\(class kicad_default\s+)([^()]+?)(\s*\(circuit[\s\S]*?\)\s*"
        r"\(rule[\s\S]*?\)\s*)\)",
        text)
    if not m:
        print("    !! could not locate kicad_default class"); return 0
    nets_raw = m.group(2)
    kept = [t for t in nets_raw.split() if t not in PLANE_NETS]
    n_dropped = len(nets_raw.split()) - len(kept)
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
    text = text.replace(m.group(0),
                        m.group(1) + "\n" + fmt(kept) + m.group(3) + ")")
    n_net = 0
    for N in PLANE_NETS:
        pat = r"\s*\(net " + re.escape(N) + r"\s*\(pins[\s\S]*?\)\s*\)"
        text, n = re.subn(pat, "", text)
        n_net += n
    print(f"    patch: -{n_layer} layers, -{n_plane} planes, "
          f"-{n_dropped} plane nets, -{n_net} (net) blocks")
    with open(dsn_path, "w") as f: f.write(text)
    return 1


def main():
    print("[1] load + strip routes")
    brd = pcbnew.LoadBoard(PCB)
    nt = nv = 0
    for t in list(brd.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA):
            brd.Remove(t); nv += 1
        else:
            brd.Remove(t); nt += 1
    pcbnew.ZONE_FILLER(brd).Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"    removed {nt} tracks + {nv} vias")

    print("[2] export DSN")
    if os.path.exists(DSN): os.remove(DSN)
    ok = pcbnew.ExportSpecctraDSN(brd, DSN)
    if not ok: print("    !! DSN export failed"); sys.exit(2)
    print(f"    DSN: {os.path.getsize(DSN)} bytes")

    print("[3] 3-layer patch DSN")
    if patch_3layer(DSN) != 1: sys.exit(3)
    print(f"    patched: {os.path.getsize(DSN)} bytes")

    print(f"[4] Freerouting -mt 4 -mp 30 (timeout {TIMEOUT}s) — 3 signal layers")
    if os.path.exists(SES): os.remove(SES)
    t0 = time.time()
    with open(LOG, "w") as logf:
        try:
            subprocess.run([JAVA, "-Xmx6g", "-Dgui.enabled=false", "-jar", FR_JAR,
                            "-de", DSN, "-do", SES, "-mt", "4", "-mp", "30"],
                           stdout=logf, stderr=subprocess.STDOUT, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            print(f"    TIMEOUT at {TIMEOUT}s"); sys.exit(10)
    elapsed = (time.time() - t0) / 60
    ses_size = os.path.getsize(SES) if os.path.exists(SES) else 0
    print(f"    elapsed {elapsed:.1f} min, ses={ses_size} bytes")

    with open(LOG) as f: log = f.read()
    passes = re.findall(r"Auto-router pass #(\d+).*?\((\d+) unrouted\)", log)
    if passes:
        last = passes[-1]
        print(f"    last pass #{last[0]}: {last[1]} unrouted")
    else:
        print("    no pass info — possible hang")

    if not os.path.exists(SES) or ses_size < 1000:
        print(f"  VERDICT: no usable SES"); sys.exit(11)

    print("[5] import SES + DRC")
    brd2 = pcbnew.LoadBoard(PCB)
    pcbnew.ImportSpecctraSES(brd2, SES)
    pcbnew.ZONE_FILLER(brd2).Fill(list(brd2.Zones()))
    pcbnew.SaveBoard(PCB, brd2)
    nt = sum(1 for t in brd2.GetTracks() if not isinstance(t, pcbnew.PCB_VIA))
    nv = sum(1 for t in brd2.GetTracks() if isinstance(t, pcbnew.PCB_VIA))
    print(f"    post-import: {nt} tracks, {nv} vias")
    drc_out = os.path.join(HERE, "drc_3layer.txt")
    subprocess.run(["kicad-cli","pcb","drc","--severity-error","--format","report",
                    "--output",drc_out,"--units","mm",PCB],
                   capture_output=True)
    with open(drc_out) as f: t = f.read()
    err = re.search(r"Found (\d+) DRC violation", t)
    unc = re.search(r"Found (\d+) unconnected pad", t)
    print(f"    DRC: {err.group(1) if err else '?'} errors, "
          f"{unc.group(1) if unc else '?'} unconnected")


if __name__ == "__main__":
    main()
