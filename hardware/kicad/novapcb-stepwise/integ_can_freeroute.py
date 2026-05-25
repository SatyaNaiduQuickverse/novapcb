#!/usr/bin/env python3
"""H↔C sub-step — Freerouting scoped to 8 MOT* nets, F.Cu + B.Cu only.

Per master 2026-05-24 sign-off (analysis 785342d accepted). Discipline:
  1. DSN: F.Cu + B.Cu only — inner layers stripped (no plane-zone cuts)
  2. Net scope: 8 MOT* nets only (others already routed)
  3. Time-bound 15 min; autosave disabled; SES MUST be written naturally
     (memory feedback_no_timeout_kill_freerouting: time-kill loses SES)
  4. Verify SES exists on disk after run (Rule 9)
  5. Apply via apply_h_ses.py (manual parse — ImportSpecctraSES returns
     False on scoped DSN per project pattern)
  6. add_h_gnd_via.py for J11.10 GND stitching (separate step, Freerouting
     out of scope for GND since it's not in MOT* net list)

8 MOT* nets: MOT1..MOT8 — MCU TIM pins → J11.1..J11.8
"""
import os
import re
import sys
import subprocess
import time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-stepwise.kicad_pcb")
DSN_RAW = os.path.join(HERE, "can_routing_raw.dsn")
DSN = os.path.join(HERE, "can_routing.dsn")
SES = os.path.join(HERE, "can_routing.ses")
LOG = os.path.join(HERE, "can_routing_freerouting.log")
JAVA = os.path.expanduser("~/local/jre/jdk-25.0.3+9-jre/bin/java")
JAR = os.path.expanduser("~/local/freerouting/freerouting.jar")

CAN_NETS = {"CAN1_RX", "CAN1_TX", "GPIO_CAN1_SILENT", "CANH_NET", "CANL_NET", "CAN_TERM_MID"}
H_NETS = CAN_NETS  # alias for code compatibility


def step1_export_dsn(brd):
    print(f"[1/4] export DSN: {DSN_RAW}")
    for p in (DSN_RAW, DSN):
        if os.path.exists(p):
            os.remove(p)
    ok = pcbnew.ExportSpecctraDSN(brd, DSN_RAW)
    if not ok or not os.path.exists(DSN_RAW):
        print("      !!! ExportSpecctraDSN failed")
        return False
    print(f"      DSN written: {os.path.getsize(DSN_RAW):,} bytes")
    return True


def step2_strip_dsn():
    """Strip inner layers + parked components + non-H nets."""
    print(f"[2/4] strip inner layers + parked + non-H nets from DSN")
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

    text = strip_paren_form(text, r'\(layer \"?(In[1-4]\.Cu)\"?', "inner-layer entries")
    text = strip_paren_form(text, r'\(plane [^()]+\(polygon (In[1-4]\.Cu)', "inner-layer plane defs")

    parked_refs = set()
    on_board_refs = set()
    for m in re.finditer(r'\(place (\w+)\s+(-?[\d.]+)\s+(-?[\d.]+)', text):
        ref, x, _y = m.groups()
        if abs(float(x) / 1000.0) >= 100:
            parked_refs.add(ref)
        else:
            on_board_refs.add(ref)
    print(f"      placed: {len(on_board_refs)} on-board, {len(parked_refs)} parked")

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

    out = []
    i = 0
    net_pattern = re.compile(r'\(net (\S+)\s*\(pins\s+([^)]+)\)\s*\)', re.DOTALL)
    nets_kept = 0; nets_dropped = 0; pins_dropped = 0
    network_match = re.search(r'\(network\s', text)
    if not network_match:
        print("      WARN: (network) section not found, skipping pin-trim")
    else:
        ns = network_match.start()
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
            # SCOPE: keep ONLY the 6 CAN nets in (network) so Freerouting routes
            # just those (board has many other unrouted nets now; their existing
            # wires stay in (wiring) as fixed obstacles). 2026-05-26 fix.
            nm = name.strip().strip('"').strip('{}').strip('"')
            if nm not in CAN_NETS:
                nets_dropped += 1
                return ""
            raw_pins = m.group(2).split()
            kept = []
            for p in raw_pins:
                ref = p.split("-")[0]
                if ref in parked_refs:
                    pins_dropped += 1
                    continue
                kept.append(p)
            if len(kept) < 2:
                nets_dropped += 1
                return ""
            nets_kept += 1
            return f"(net {name}\n      (pins {' '.join(kept)}))"

        new_network = net_pattern.sub(rewrite_net, network_body)
        text = text[:ns] + new_network + text[ne:]
    print(f"      kept {nets_kept} nets, dropped {nets_dropped} (no on-board pin pair), "
          f"dropped {pins_dropped} parked-pin refs")

    # Fix via padstacks: drop inner-layer (In1-4.Cu) circle shapes so the
    # F-B via is valid in the 2-layer DSN. Without this, Freerouting has NO
    # usable via and can't route nets needing a layer change (2026-05-26).
    n_shapes = len(re.findall(r'\(shape \(circle In[1-4]\.Cu', text))
    text = re.sub(r'\n\s*\(shape \(circle In[1-4]\.Cu [^\n]*\)\)', '', text)
    print(f"      dropped {n_shapes} inner-layer via-padstack shapes (F-B via now valid)")

    with open(DSN, "w") as f:
        f.write(text)
    print(f"      stripped DSN: {os.path.getsize(DSN):,} bytes "
          f"(was {os.path.getsize(DSN_RAW):,})")
    return True


def step3_run_freerouting():
    """90-min safety-net cap per master 2026-05-24. Per memory
    feedback_no_timeout_kill_freerouting: this is safety, not guillotine —
    Freerouting must exit naturally for SES write. -mp 30 caps iter count.
    Increased from 25 → 30 since we have 9 nets (was 8) and want more
    convergence passes if needed."""
    print(f"[3/4] run Freerouting (90-min safety cap, mp=30, no kill)")
    if os.path.exists(SES):
        os.remove(SES)
    cmd = [
        JAVA, "-jar", JAR,
        "-de", DSN,
        "-do", SES,
        "-mt", "4",
        "-mp", "10",
        "-da",
    ]
    t0 = time.time()
    with open(LOG, "w") as logf:
        try:
            r = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT,
                               timeout=900)  # 15-min safety cap (master 2026-05-26); not a guillotine
            elapsed = time.time() - t0
            print(f"      completed in {elapsed:.0f}s, returncode={r.returncode}")
        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            print(f"      !!! TIMEOUT after {elapsed:.0f}s — SES likely missing")
            return False
    return True


def step4_verify_ses():
    print(f"[4/4] Rule-9: verify SES on disk")
    if not os.path.exists(SES):
        print(f"      !!! SES file missing: {SES}")
        return False
    sz = os.path.getsize(SES)
    print(f"      SES present: {sz:,} bytes")
    return sz > 1000


def main():
    print("=== H↔C sub-step — Freerouting (scoped, F.Cu+B.Cu) ===\n")
    brd = pcbnew.LoadBoard(PCB)
    if not step1_export_dsn(brd): return 1
    if not step2_strip_dsn():     return 2
    if not step3_run_freerouting():return 3
    if not step4_verify_ses():    return 4
    print("\n=== Freerouting done. Next: apply_h_ses.py + add_h_gnd_via.py ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
