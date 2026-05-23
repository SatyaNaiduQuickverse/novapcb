#!/usr/bin/env python3
"""+3V3_IMU rail routing — Freerouting scoped to single net (1 net,
17 endpoints).

Per master 2026-05-23 (3 decisions confirmed): F.Cu trace network,
0.25mm uniform width, trunk through bridge column X=63±5mm.

Reuses scoped-DSN pattern from sense/D-routing sub-steps.
"""
import os
import re
import subprocess
import sys
import time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
DSN_RAW = os.path.join(HERE, "3v3_imu_raw.dsn")
DSN = os.path.join(HERE, "3v3_imu.dsn")
SES = os.path.join(HERE, "3v3_imu.ses")
LOG = os.path.join(HERE, "3v3_imu_freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

TARGET_NET = "+3V3_IMU"


def strip_paren_form(text, pattern, label):
    out = []
    i = 0
    n = 0
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
        n += 1
        i = j
    print(f"      dropped {n} {label}", flush=True)
    return "".join(out)


def main():
    print("=== +3V3_IMU rail — Freerouting scoped to single net ===\n", flush=True)
    brd = pcbnew.LoadBoard(PCB)

    print(f"[1/3] export DSN: {DSN_RAW}", flush=True)
    for p in (DSN_RAW, DSN):
        if os.path.exists(p):
            os.remove(p)
    if not pcbnew.ExportSpecctraDSN(brd, DSN_RAW):
        print("      !!! export failed")
        return 1
    print(f"      DSN: {os.path.getsize(DSN_RAW):,} bytes", flush=True)

    print(f"[2/3] strip DSN: inner layers + planes + parked + non-+3V3_IMU nets", flush=True)
    with open(DSN_RAW) as f:
        text = f.read()
    text = strip_paren_form(text, r'\(layer \"?(In[1-4]\.Cu)\"?', "inner-layer entries")
    text = strip_paren_form(text, r'\(plane [^()]+\(polygon (In[1-4]\.Cu)', "inner-layer plane defs")

    parked = set()
    on_board = set()
    for m in re.finditer(r'\(place (\w+)\s+(-?[\d.]+)\s+(-?[\d.]+)', text):
        ref, x, _y = m.groups()
        (parked if abs(float(x) / 1000.0) >= 100 else on_board).add(ref)
    print(f"      placed: {len(on_board)} on-board, {len(parked)} parked", flush=True)

    new_lines = []
    parked_dropped = 0
    for line in text.split("\n"):
        m = re.search(r'\(place (\w+)\s+(-?[\d.]+)', line)
        if m and abs(float(m.group(2)) / 1000.0) >= 100:
            parked_dropped += 1
            continue
        new_lines.append(line)
    text = "\n".join(new_lines)
    print(f"      dropped {parked_dropped} parked entries", flush=True)

    # Trim (network) to only +3V3_IMU
    network_match = re.search(r'\(network\s', text)
    if network_match:
        ns = network_match.start()
        depth = 0
        ne = ns
        while ne < len(text):
            if text[ne] == "(":
                depth += 1
            elif text[ne] == ")":
                depth -= 1
                if depth == 0:
                    ne += 1
                    break
            ne += 1
        network_body = text[ns:ne]
        nets_kept = 0
        nets_dropped = 0
        net_pattern = re.compile(r'\(net (\S+)\s*\(pins\s+([^)]+)\)\s*\)', re.DOTALL)

        def rewrite_net(m):
            nonlocal nets_kept, nets_dropped
            name = m.group(1)
            raw_pins = m.group(2).split()
            kept = [p for p in raw_pins if p.split("-")[0] not in parked]
            if len(kept) < 2:
                nets_dropped += 1
                return ""
            name_clean = name.strip('"')
            if name_clean != TARGET_NET:
                nets_dropped += 1
                return ""
            nets_kept += 1
            return f"(net {name}\n      (pins {' '.join(kept)}))"

        new_network = net_pattern.sub(rewrite_net, network_body)
        text = text[:ns] + new_network + text[ne:]
        print(f"      kept {nets_kept} net (+3V3_IMU), dropped {nets_dropped}", flush=True)

    with open(DSN, "w") as f:
        f.write(text)
    print(f"      stripped DSN: {os.path.getsize(DSN):,} bytes", flush=True)

    print(f"[3/3] Freerouting (autosave, no timeout-kill)", flush=True)
    if os.path.exists(SES):
        os.remove(SES)
    cmd = [JAVA, "-jar", JAR, "-de", DSN, "-do", SES,
           "-mt", "4", "-mp", "50", "-da"]
    t0 = time.time()
    with open(LOG, "w") as logf:
        try:
            r = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT,
                               timeout=600)
            print(f"      completed in {time.time()-t0:.0f}s, rc={r.returncode}", flush=True)
        except subprocess.TimeoutExpired:
            print(f"      !!! TIMEOUT")
            return 2
    if not os.path.exists(SES) or os.path.getsize(SES) < 1000:
        print(f"      !!! SES missing/tiny")
        return 3
    print(f"      SES: {os.path.getsize(SES):,} bytes", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
