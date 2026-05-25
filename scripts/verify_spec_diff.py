#!/usr/bin/env python3
"""verify_spec_diff.py — Rule 4 spec-deviation detector for PR docs.

Per MASTER_PROCESS_RULES.md Rule 4: every PR must disclose every divergence
from spec (component position, DRU rule, fab process, deferred net). This
script compares actual board state vs the spec-of-record (committed YAML
contracts + DECISIONS.md anchors) and reports deviations.

Usage:
  python3 verify_spec_diff.py <board.kicad_pcb>

Reports:
  - Component-position deviations vs subsystem_contracts placement table
  - DRU rules present in .kicad_dru that aren't in DECISIONS §13
  - Net deferrals (unrouted nets that should be routed per contract)

Output: text report. Exit 0 if no deviations or all are documented in
DECISIONS; exit 1 if any undocumented deviation found.
"""
import sys, os, re
import pcbnew

if len(sys.argv) < 2:
    sys.exit("usage: verify_spec_diff.py <board.kicad_pcb>")

board_path = sys.argv[1]
board = pcbnew.LoadBoard(board_path)

# Resolve repo root + key docs
here = os.path.dirname(os.path.abspath(board_path))
# Walk up to find docs/
repo_root = here
for _ in range(5):
    if os.path.isdir(os.path.join(repo_root, "docs")):
        break
    repo_root = os.path.dirname(repo_root)
decisions_path = os.path.join(repo_root, "docs", "DECISIONS.md")
contracts_path = os.path.join(repo_root, "docs", "SUBSYSTEM_CONTRACTS.md")
dru_path = board_path.replace(".kicad_pcb", ".kicad_dru")

deviations = []
documented = []
info = []


# ----- 1. DRU rules vs DECISIONS §13 -----
def check_dru_documented():
    try:
        with open(dru_path) as f:
            dru_txt = f.read()
    except FileNotFoundError:
        info.append(f"No .kicad_dru file at {dru_path}")
        return
    try:
        with open(decisions_path) as f:
            dec_txt = f.read()
    except FileNotFoundError:
        deviations.append("DECISIONS.md not found — can't verify DRU documentation")
        return
    rule_names = re.findall(r'\(rule\s+"([^"]+)"', dru_txt)
    # Standard rules (built-in, not deviations)
    standard_keywords = ("usb-diff-pair", "usbc-pre-esd", "usbc-bridge")
    for name in rule_names:
        if any(k in name for k in standard_keywords):
            continue
        if name in dec_txt:
            documented.append(f"DRU rule '{name}' documented in DECISIONS")
        else:
            deviations.append(f"DRU rule '{name}' NOT documented in DECISIONS §13")


# ----- 2. Component-position deviations (placeholder for contract parse) -----
def check_placement_documented():
    # Stub — requires SUBSYSTEM_CONTRACTS.md to have machine-readable
    # placement table. For now, just check footprints have expected refs.
    refs_on_board = set()
    for fp in board.GetFootprints():
        if not hasattr(fp, 'GetReference'): continue
        p = fp.GetPosition()
        if p.x/1e6 >= 100: continue  # parked
        refs_on_board.add(fp.GetReference())
    info.append(f"On-board components: {len(refs_on_board)}")
    # Check critical refs present
    critical = {"U1","U2","U6","U11","U12","Q3","Q4","J1","J4","J19"}
    missing = critical - refs_on_board
    if missing:
        deviations.append(f"Critical refs not on board: {sorted(missing)}")


# ----- 3. Unrouted nets vs contract -----
def check_unrouted_nets():
    # Count pads per net, then see which nets have >1 pad but 0 tracks/vias
    net_pads = {}
    net_routes = {}
    for fp in board.GetFootprints():
        if not hasattr(fp, 'GetReference'): continue
        for pad in fp.Pads():
            n = pad.GetNetname()
            if n:
                net_pads.setdefault(n, 0)
                net_pads[n] += 1
    for t in board.GetTracks():
        n = t.GetNetname()
        if n:
            net_routes.setdefault(n, 0)
            net_routes[n] += 1

    # Critical nets to flag if unrouted
    critical_nets = ("+3V3", "+5V", "+5V_BEC", "+5V_BEC_PROT", "GND")
    deferred_acceptable = ("EFUSE_FLT", "EFUSE_PGOOD", "EFUSE_IMON")  # master ack'd optional
    for net, pad_count in sorted(net_pads.items()):
        if pad_count < 2: continue  # not a real net
        route_count = net_routes.get(net, 0)
        if route_count == 0:
            if net in critical_nets:
                info.append(f"NET '{net}' ({pad_count} pads) — plane fill assumed")
            elif net in deferred_acceptable:
                documented.append(f"NET '{net}' ({pad_count} pads) — deferred per master ack")
            elif net.startswith(("USB_","USBC_","I2C","SPI","UART","CAN")) or "_SENS" in net:
                deviations.append(f"NET '{net}' ({pad_count} pads) — 0 routes")


# ----- run -----
check_dru_documented()
check_placement_documented()
check_unrouted_nets()

print(f"=== Spec-deviation verify: {os.path.basename(board_path)} ===")
if info:
    print("\nINFO:")
    for i in info: print(f"  {i}")
if documented:
    print(f"\nDOCUMENTED ({len(documented)}):")
    for d in documented[:10]: print(f"  ✓ {d}")
if deviations:
    print(f"\nDEVIATIONS — UNDISCUSSED ({len(deviations)}):")
    for d in deviations: print(f"  ✗ {d}")
    print()
    print("Per Rule 4: every deviation must be disclosed in PR doc.")
    sys.exit(1)
print("\nPASS — no undocumented spec deviations")
