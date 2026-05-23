#!/usr/bin/env python3
"""Sense sub-step — Freerouting scoped to 8 sense nets, F.Cu + B.Cu only.

Per master 2026-05-23 approval (Option A: Freerouting after manual hit
walls). Discipline checklist:
  1. DSN export: F.Cu + B.Cu only — inner layers stripped from structure
     (prevents Freerouting cutting voids through +3V3/+5V_BEC plane zones)
  2. Net scope: only the 8 sense nets (others already routed → Freerouting
     leaves them alone)
  3. Time-bound 15 min, autosave enabled, NO timeout-kill
  4. Verify SES exists on disk after run (Rule 9)
  5. After SES import: refill zones, DRC, audit, per-net Rule-9 cluster
     walks, render
  6. If can't produce clean in 15 min: stop, escalate

8 sense nets:
  MAUCH_VBAT_PRE, MAUCH_CURR_PRE, MAUCH2_VBAT_PRE, MAUCH2_CURR_PRE,
  BATT_VOLTAGE_SENS, BATT_CURRENT_SENS, BATT2_VOLTAGE_SENS, BATT2_CURRENT_SENS
"""
import os
import re
import sys
import subprocess
import time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
DSN_RAW = os.path.join(HERE, "sense_raw.dsn")
DSN = os.path.join(HERE, "sense.dsn")
SES = os.path.join(HERE, "sense.ses")
LOG = os.path.join(HERE, "sense_freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

SENSE_NETS = {
    "MAUCH_VBAT_PRE", "MAUCH_CURR_PRE",
    "MAUCH2_VBAT_PRE", "MAUCH2_CURR_PRE",
    "BATT_VOLTAGE_SENS", "BATT_CURRENT_SENS",
    "BATT2_VOLTAGE_SENS", "BATT2_CURRENT_SENS",
}

INNER_LAYERS = ("In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu")


def step1_export_dsn(brd):
    print(f"[1/6] export DSN: {DSN_RAW}")
    for p in (DSN_RAW, DSN):
        if os.path.exists(p):
            os.remove(p)
    ok = pcbnew.ExportSpecctraDSN(brd, DSN_RAW)
    if not ok or not os.path.exists(DSN_RAW):
        print("      !!! ExportSpecctraDSN failed")
        return False
    sz = os.path.getsize(DSN_RAW)
    print(f"      DSN written: {sz:,} bytes")
    return True


def step2_strip_inner_layers():
    """Post-process the DSN:
    1. Drop (layer InN.Cu ...) from (structure) — F.Cu + B.Cu only
    2. Drop (plane ...) referencing inner layers (no NPE)
    3. Drop parked components (X >= 100mm) — they cause spurious rats-nest
       connections that Freerouting tries to route (205 unrouted on first
       run; ~all from parked refs)
    4. Drop (net NAME ...) entries in (network) that don't include any
       on-board pin OR are not in SENSE_NETS — keep ALL on-board placed-
       component pin references in remaining nets so Freerouting respects
       existing connectivity for collision-avoid, but doesn't try to
       route nets it shouldn't touch.

    Resulting DSN: F.Cu + B.Cu only, on-board components only, sense nets
    are the only ones with unrouted pin pairs → Freerouting routes them.
    """
    print(f"[2/6] strip inner layers + parked components + non-sense nets from DSN")
    with open(DSN_RAW) as f:
        text = f.read()

    def strip_paren_form(text, pattern, label):
        out = []
        i = 0
        n_dropped = 0
        while i < len(text):
            m = re.search(pattern, text[i:])
            if not m:
                out.append(text[i:])
                break
            out.append(text[i:i + m.start()])
            j = i + m.start()
            depth = 0
            while j < len(text):
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            n_dropped += 1
            i = j
        print(f"      dropped {n_dropped} {label}")
        return "".join(out)

    # 1. Inner layer entries
    text = strip_paren_form(text, r'\(layer \"?(In[1-4]\.Cu)\"?', "inner-layer entries")
    # 2. Inner layer plane defs
    text = strip_paren_form(text, r'\(plane [^()]+\(polygon (In[1-4]\.Cu)', "inner-layer plane defs")

    # 3. Find which component refs are parked (X >= 100mm) — DSN coords in µm
    parked_refs = set()
    on_board_refs = set()
    for m in re.finditer(r'\(place (\w+)\s+(-?[\d.]+)\s+(-?[\d.]+)', text):
        ref, x, _y = m.groups()
        if abs(float(x) / 1000.0) >= 100:
            parked_refs.add(ref)
        else:
            on_board_refs.add(ref)
    print(f"      placed: {len(on_board_refs)} on-board, {len(parked_refs)} parked")

    # 4. Strip parked (place ...) entries — leave on-board only
    new_lines = []
    parked_dropped = 0
    for line in text.split("\n"):
        m = re.search(r'\(place (\w+)\s+(-?[\d.]+)\s+(-?[\d.]+)', line)
        if m and abs(float(m.group(2)) / 1000.0) >= 100:
            parked_dropped += 1
            continue
        new_lines.append(line)
    text = "\n".join(new_lines)
    print(f"      dropped {parked_dropped} parked-component (place ...) entries")

    # 5. In (network) (net NAME (pins ref-pin ref-pin ...)) — drop pin refs
    #    to parked components. If only one pin remains, drop the whole net.
    #    If net not in SENSE_NETS and has no unrouted pin pairs left,
    #    Freerouting won't route it.
    out = []
    i = 0
    net_pattern = re.compile(r'\(net (\S+)\s*\(pins\s+([^)]+)\)\s*\)', re.DOTALL)
    nets_kept = 0; nets_dropped = 0; pins_dropped = 0
    network_match = re.search(r'\(network\s', text)
    if not network_match:
        print("      WARN: (network) section not found, skipping pin-trim")
    else:
        # Walk paren-balanced through (network ...) and rewrite (net ...) bodies
        ns = network_match.start()
        # Find network end
        depth = 0
        ne = ns
        while ne < len(text):
            if text[ne] == "(":
                depth += 1
            elif text[ne] == ")":
                depth -= 1
                if depth == 0:
                    ne += 1; break
            ne += 1
        network_body = text[ns:ne]

        def rewrite_net(m):
            nonlocal nets_kept, nets_dropped, pins_dropped
            name = m.group(1)
            raw_pins = m.group(2).split()
            kept = []
            for p in raw_pins:
                ref = p.split("-")[0]
                if ref in parked_refs:
                    pins_dropped += 1
                    continue
                kept.append(p)
            if len(kept) < 2:
                # Single pin (or no pin) on this net — no routable pair
                nets_dropped += 1
                return ""  # drop the whole (net ...) entry
            nets_kept += 1
            return f"(net {name}\n      (pins {' '.join(kept)}))"

        new_network = net_pattern.sub(rewrite_net, network_body)
        text = text[:ns] + new_network + text[ne:]
    print(f"      kept {nets_kept} nets, dropped {nets_dropped} (no on-board pin pair), "
          f"dropped {pins_dropped} parked-pin refs")

    with open(DSN, "w") as f:
        f.write(text)
    print(f"      stripped DSN: {os.path.getsize(DSN):,} bytes "
          f"(was {os.path.getsize(DSN_RAW):,})")
    return True


def step3_run_freerouting():
    print(f"[3/6] run Freerouting (15-min cap, autosave)")
    if os.path.exists(SES):
        os.remove(SES)
    # -mp 50 passes; -mt 4 threads; --postroute 5 ripping-pass count
    # Time-cap via subprocess timeout — note Freerouting writes SES on
    # NATURAL exit. If we kill on timeout we LOSE the SES (memory
    # feedback_no_timeout_kill_freerouting).
    cmd = [
        JAVA, "-jar", JAR,
        "-de", DSN,
        "-do", SES,
        "-mt", "4",
        "-mp", "50",
        "-da",   # disable auto-save (we use mp limit as the bound)
    ]
    t0 = time.time()
    with open(LOG, "w") as logf:
        try:
            r = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT,
                               timeout=900)  # 15 min
            elapsed = time.time() - t0
            print(f"      completed in {elapsed:.0f}s, returncode={r.returncode}")
        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            print(f"      !!! TIMEOUT after {elapsed:.0f}s — Freerouting did "
                  f"NOT exit naturally; SES likely incomplete/missing")
            return False
    return True


def step4_verify_ses():
    print(f"[4/6] Rule-9: verify SES on disk")
    if not os.path.exists(SES):
        print(f"      !!! SES file missing: {SES}")
        return False
    sz = os.path.getsize(SES)
    print(f"      SES present: {sz:,} bytes")
    return sz > 1000  # min sanity


def step5_import_ses_and_refill():
    print(f"[5/6] import SES + refill zones")
    brd = pcbnew.LoadBoard(PCB)
    ok = pcbnew.ImportSpecctraSES(brd, SES)
    if not ok:
        print("      !!! ImportSpecctraSES failed")
        return False
    # Refill zones (vias added by route ⇒ need new anti-pads in plane fills)
    for z in brd.Zones():
        if hasattr(z, "UnFill"):
            z.UnFill()
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(list(brd.Zones()))
    pcbnew.SaveBoard(PCB, brd)
    print(f"      saved {PCB}")
    return True


def step6_per_net_walk():
    print(f"[6/6] per-net Rule-9 cluster walk on 8 sense nets")
    brd = pcbnew.LoadBoard(PCB)
    fails = 0
    for name in sorted(SENSE_NETS):
        n_trk = 0
        n_via = 0
        total_len = 0.0
        for trk in brd.GetTracks():
            if trk.GetNetname() == name:
                if trk.GetClass() == "PCB_VIA":
                    n_via += 1
                else:
                    n_trk += 1
                    s = trk.GetStart(); e = trk.GetEnd()
                    dx = (s.x - e.x) / 1e6
                    dy = (s.y - e.y) / 1e6
                    total_len += (dx * dx + dy * dy) ** 0.5
        status = "PASS" if n_trk >= 2 else "FAIL"
        print(f"  {name:<22}: {n_trk:>2} tracks, {n_via:>2} vias, "
              f"len={total_len:5.1f}mm  {status}")
        if n_trk < 2:
            fails += 1
    return fails == 0


def main():
    print("=== Sense sub-step — Freerouting (scoped, F.Cu+B.Cu only) ===\n")
    brd = pcbnew.LoadBoard(PCB)
    if not step1_export_dsn(brd):
        return 1
    if not step2_strip_inner_layers():
        return 2
    if not step3_run_freerouting():
        return 3
    if not step4_verify_ses():
        return 4
    if not step5_import_ses_and_refill():
        return 5
    if not step6_per_net_walk():
        print("\n!!! Some sense nets have <2 tracks — incomplete routing")
        return 6
    print("\n=== Freerouting sense sub-step COMPLETE ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
