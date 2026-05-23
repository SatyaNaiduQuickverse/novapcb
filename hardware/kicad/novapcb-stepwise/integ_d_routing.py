#!/usr/bin/env python3
"""D↔C/B routing sub-step — route SPI buses + INT lines + HEATER_PWM
to IMU island after stackup-fix PR merge.

Pattern reuses sense-sub-step workflow (proven in sha d82f08a):
1. Export DSN
2. Strip DSN: inner layers + planes + parked components + non-D nets
3. Freerouting (15-min cap, autosave, no timeout-kill)
4. Custom SES parser → apply only D nets to board

Per master 2026-05-23 D↔C/B routing sequence:
- SPI3 wraparound: B.Cu (now references In4.Cu GND, correct)
- SPI1 + SPI2 + INT + HEATER on F.Cu/B.Cu per Freerouting's pick
- +3V3_IMU rail: deferred to separate sub-step (not plane-served — In3
  is +3V3 not +3V3_IMU)

D-routing target nets (17 signal):
- SPI1: SCK/MISO/MOSI + IMU1_CS (4)
- SPI2: SCK/MISO/MOSI + IMU2_ACC_CS + IMU2_GYR_CS (5)
- SPI3: SCK/MISO/MOSI + IMU3_CS (4)
- INTs: IMU2_ACC_INT1 + IMU2_GYR_INT3 + IMU3_INT1 (3)
- HEATER_PWM (1)
"""
import os
import re
import subprocess
import sys
import time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
DSN_RAW = os.path.join(HERE, "d_routing_raw.dsn")
DSN = os.path.join(HERE, "d_routing.dsn")
SES = os.path.join(HERE, "d_routing.ses")
LOG = os.path.join(HERE, "d_routing_freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

D_NETS = {
    "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI", "IMU1_CS",
    "SPI2_SCK", "SPI2_MISO", "SPI2_MOSI", "IMU2_ACC_CS", "IMU2_GYR_CS",
    "SPI3_SCK", "SPI3_MISO", "SPI3_MOSI", "IMU3_CS",
    "IMU2_ACC_INT1", "IMU2_GYR_INT3", "IMU3_INT1",
    "HEATER_PWM",
}

INNER_LAYERS = ("In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu")


def step1_export_dsn(brd):
    print(f"[1/3] export DSN: {DSN_RAW}", flush=True)
    for p in (DSN_RAW, DSN):
        if os.path.exists(p):
            os.remove(p)
    ok = pcbnew.ExportSpecctraDSN(brd, DSN_RAW)
    if not ok or not os.path.exists(DSN_RAW):
        print("      !!! ExportSpecctraDSN failed")
        return False
    print(f"      DSN written: {os.path.getsize(DSN_RAW):,} bytes", flush=True)
    return True


def step2_strip_dsn():
    print(f"[2/3] strip DSN: inner layers + planes + parked + non-D nets", flush=True)
    with open(DSN_RAW) as f:
        text = f.read()

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

    text = strip_paren_form(text, r'\(layer \"?(In[1-4]\.Cu)\"?', "inner-layer entries")
    text = strip_paren_form(text, r'\(plane [^()]+\(polygon (In[1-4]\.Cu)', "inner-layer plane defs")

    # Strip parked components (X >= 100mm)
    parked = set()
    on_board = set()
    for m in re.finditer(r'\(place (\w+)\s+(-?[\d.]+)\s+(-?[\d.]+)', text):
        ref, x, _y = m.groups()
        if abs(float(x) / 1000.0) >= 100:
            parked.add(ref)
        else:
            on_board.add(ref)
    print(f"      placed: {len(on_board)} on-board, {len(parked)} parked", flush=True)

    new_lines = []
    parked_dropped = 0
    for line in text.split("\n"):
        m = re.search(r'\(place (\w+)\s+(-?[\d.]+)\s+(-?[\d.]+)', line)
        if m and abs(float(m.group(2)) / 1000.0) >= 100:
            parked_dropped += 1
            continue
        new_lines.append(line)
    text = "\n".join(new_lines)
    print(f"      dropped {parked_dropped} parked (place ...) entries", flush=True)

    # Trim non-D nets in (network)
    out = []
    i = 0
    net_pattern = re.compile(r'\(net (\S+)\s*\(pins\s+([^)]+)\)\s*\)', re.DOTALL)
    nets_kept = 0
    nets_dropped = 0
    pins_dropped = 0
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

        def rewrite_net(m):
            nonlocal nets_kept, nets_dropped, pins_dropped
            name = m.group(1)
            raw_pins = m.group(2).split()
            kept = []
            for p in raw_pins:
                ref = p.split("-")[0]
                if ref in parked:
                    pins_dropped += 1
                    continue
                kept.append(p)
            if len(kept) < 2:
                nets_dropped += 1
                return ""
            # Only KEEP this net if it's a D-routing target
            # (otherwise Freerouting tries to route it too)
            name_clean = name.strip('"')
            if name_clean not in D_NETS:
                nets_dropped += 1
                return ""
            nets_kept += 1
            return f"(net {name}\n      (pins {' '.join(kept)}))"

        new_network = net_pattern.sub(rewrite_net, network_body)
        text = text[:ns] + new_network + text[ne:]
    print(f"      kept {nets_kept} D nets, dropped {nets_dropped} (non-D + no-pin-pair), "
          f"dropped {pins_dropped} parked-pin refs", flush=True)

    with open(DSN, "w") as f:
        f.write(text)
    print(f"      stripped DSN: {os.path.getsize(DSN):,} bytes "
          f"(was {os.path.getsize(DSN_RAW):,})", flush=True)
    return True


def step3_run_freerouting():
    print(f"[3/3] run Freerouting (15-min cap, autosave, no timeout-kill)", flush=True)
    if os.path.exists(SES):
        os.remove(SES)
    cmd = [
        JAVA, "-jar", JAR,
        "-de", DSN,
        "-do", SES,
        "-mt", "4",
        "-mp", "50",
        "-da",
    ]
    t0 = time.time()
    with open(LOG, "w") as logf:
        try:
            r = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT,
                               timeout=900)
            elapsed = time.time() - t0
            print(f"      completed in {elapsed:.0f}s, returncode={r.returncode}", flush=True)
        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            print(f"      !!! TIMEOUT after {elapsed:.0f}s — Freerouting did NOT exit naturally", flush=True)
            return False
    if not os.path.exists(SES) or os.path.getsize(SES) < 1000:
        print(f"      !!! SES missing/tiny on disk: {SES}")
        return False
    print(f"      SES: {os.path.getsize(SES):,} bytes", flush=True)
    return True


def main():
    print("=== D↔C/B routing — Freerouting scoped to 17 D nets ===\n", flush=True)
    brd = pcbnew.LoadBoard(PCB)
    if not step1_export_dsn(brd):
        return 1
    if not step2_strip_dsn():
        return 2
    if not step3_run_freerouting():
        return 3
    print("\n=== Freerouting done — run apply_d_ses.py to apply wires ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
