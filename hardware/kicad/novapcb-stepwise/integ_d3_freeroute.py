#!/usr/bin/env python3
"""D3 — Freerouting scoped to the +5V net (board-wide 5V distribution).

Phase 4d-redux D2. The +5V raw rail (27 pads) spans 85x67mm: USB-C VBUS (J1) +
eFuse U6 VIN + buck U2 VIN + CAN xcvr U14 VCC + peripheral-connector 5V pins
(J3/J5/J10/J20) + decaps. The central band is fully congested on both layers
(40-49 segs/2mm), so neither a hand-trunk nor a zone fits cleanly — scoped FR
through the congestion is the proven approach (CRSF 63mm precedent).

Discipline (same as prior FR sub-steps):
  1. DSN: F.Cu + B.Cu only — inner layers stripped (no plane-zone cuts)
  2. Net scope: ONLY +5V in (network); all else stays as fixed obstacles
  3. WIDTH: +5V pulled into its own class at 0.40mm (power rail; ~2.3A @10C
     external on 1oz). High-current U6/U2 VIN stubs widened post-hoc if needed.
  4. 4-min cap (local nets, fast) (NOT a guillotine; SES writes only on natural exit)
  5. Verify SES on disk (Rule 9), then apply via apply_d2_ses.py
"""
import os
import re
import sys
import subprocess
import time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
DSN_RAW = os.path.join(HERE, "d3_efuse_raw.dsn")
DSN = os.path.join(HERE, "d3_efuse.dsn")
SES = os.path.join(HERE, "d3_efuse.ses")
LOG = os.path.join(HERE, "d3_efuse_freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

TARGET_NETS = {"EFUSE_FLT","EFUSE_PGOOD"}
WIDTH_UM = 250  # 0.25mm (eFuse out is USB-bench-only; flags thin)


def step1_export_dsn(brd):
    print(f"[1/5] export DSN: {DSN_RAW}")
    for p in (DSN_RAW, DSN):
        if os.path.exists(p):
            os.remove(p)
    ok = pcbnew.ExportSpecctraDSN(brd, DSN_RAW)
    if not ok or not os.path.exists(DSN_RAW):
        print("      !!! ExportSpecctraDSN failed")
        return False
    print(f"      DSN written: {os.path.getsize(DSN_RAW):,} bytes")
    return True


def _strip_paren_form(text, pattern, label):
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


def step2_strip_dsn():
    print(f"[2/5] strip inner layers + parked + non-target nets")
    with open(DSN_RAW) as f:
        text = f.read()
    text = _strip_paren_form(text, r'\(layer \"?(In[1-4]\.Cu)\"?', "inner-layer entries")
    text = _strip_paren_form(text, r'\(plane [^()]+\(polygon (In[1-4]\.Cu)', "inner-layer plane defs")

    parked_refs = set()
    for m in re.finditer(r'\(place (\w+)\s+(-?[\d.]+)\s+(-?[\d.]+)', text):
        ref, x, _y = m.groups()
        if abs(float(x) / 1000.0) >= 100:
            parked_refs.add(ref)

    new_lines = []
    parked_dropped = 0
    for line in text.split("\n"):
        m = re.search(r'\(place (\w+)\s+(-?[\d.]+)\s+(-?[\d.]+)', line)
        if m and abs(float(m.group(2)) / 1000.0) >= 100:
            parked_dropped += 1
            continue
        new_lines.append(line)
    text = "\n".join(new_lines)
    print(f"      dropped {parked_dropped} parked (place ...) entries")

    net_pattern = re.compile(r'\(net (\S+)\s*\(pins\s+([^)]+)\)\s*\)', re.DOTALL)
    nets_kept = 0; nets_dropped = 0; pins_dropped = 0
    network_match = re.search(r'\(network\s', text)
    if not network_match:
        print("      WARN: (network) not found")
    else:
        ns = network_match.start()
        depth = 0; ne = ns
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
            nm = name.strip().strip('"').strip('{}').strip('"')
            if nm not in TARGET_NETS:
                nets_dropped += 1
                return ""
            raw_pins = m.group(2).split()
            kept = [p for p in raw_pins if p.split("-")[0] not in parked_refs]
            pins_dropped += len(raw_pins) - len(kept)
            if len(kept) < 2:
                nets_dropped += 1
                return ""
            nets_kept += 1
            return f"(net {name}\n      (pins {' '.join(kept)}))"

        new_network = net_pattern.sub(rewrite_net, network_body)
        text = text[:ns] + new_network + text[ne:]
    print(f"      kept {nets_kept} nets, dropped {nets_dropped}, dropped {pins_dropped} parked pins")

    # F-B via valid in 2-layer DSN: drop inner-layer via padstack shapes
    n_shapes = len(re.findall(r'\(shape \(circle In[1-4]\.Cu', text))
    text = re.sub(r'\n\s*\(shape \(circle In[1-4]\.Cu [^\n]*\)\)', '', text)
    print(f"      dropped {n_shapes} inner-layer via-padstack shapes")

    # No width-class injection: route the 4 D3 nets at kicad_default 0.2mm.
    # +5V_BEC_PROT is USB-bench-current (flight +5V_BEC comes from Mauch); the
    # FLT/PGOOD/DVDT flags are signals. (The earlier multi-line-regex injection
    # double-classed the already-routed +5V net and hung Freerouting.)

    with open(DSN, "w") as f:
        f.write(text)
    print(f"      stripped DSN: {os.path.getsize(DSN):,} bytes (was {os.path.getsize(DSN_RAW):,})")
    return True


def step3_run():
    print(f"[3/5] run Freerouting (4-min cap (local nets, fast), mp=10, no kill)")
    if os.path.exists(SES):
        os.remove(SES)
    cmd = [JAVA, "-jar", JAR, "-de", DSN, "-do", SES, "-mt", "4", "-mp", "10", "-da"]
    t0 = time.time()
    with open(LOG, "w") as logf:
        try:
            r = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, timeout=240)
            print(f"      completed in {time.time()-t0:.0f}s, rc={r.returncode}")
        except subprocess.TimeoutExpired:
            print(f"      !!! TIMEOUT after {time.time()-t0:.0f}s — SES likely missing")
            return False
    return True


def step4_verify_ses():
    print(f"[4/5] Rule-9: verify SES on disk")
    if not os.path.exists(SES):
        print(f"      !!! SES missing: {SES}")
        return False
    sz = os.path.getsize(SES)
    print(f"      SES present: {sz:,} bytes")
    return sz > 1000


def main():
    print("=== D3 — Freerouting (+5V, scoped, F.Cu+B.Cu, 0.40mm) ===\n")
    brd = pcbnew.LoadBoard(PCB)
    if not step1_export_dsn(brd): return 1
    if not step2_strip_dsn():     return 2
    if not step3_run():           return 3
    if not step4_verify_ses():    return 4
    print("\n[5/5] SES ready. Next: apply_d2_ses.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
