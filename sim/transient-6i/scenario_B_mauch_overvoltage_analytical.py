"""Sim 6i Scenario B — Mauch BEC over-voltage fault (analytical)

Master-side run 2026-06-01 per Sai 'no corner cutting' + disk-space-limit
no-install constraint. Uses TPS25940A datasheet specs + R7/R9 divider values
from `bom/novapcb-bom.csv` + standard analog control loop theory.

Scenario: Mauch BEC output fails to a stuck-on 8V (above eFuse OVP trip).
Gate (per docs/SIM_6I_TRANSIENT_OV_SPEC.md §3.6i.B):
- TPS25940 OVP latches off ≤ 50 µs of OVP threshold breach
- +5V_BEC_PROT rail drops < 5.0V within 100 µs

Method:
1. Compute OVP voltage threshold from R7/R9 divider.
2. Compute OVP response time from TPS25940 datasheet t_OVP (8 µs typical) +
   gate-drive turn-off slew (~2 µs).
3. Compute +5V_BEC_PROT decay time after eFuse turn-off, given C9 bulk cap
   on OUT side + downstream load (LDO U13 + buck U2 + connectors).
"""

import math

# ---- TPS25940 datasheet specs (TI datasheet SLVSCM5, Rev D 2017) ----
# V_OVP_TH corrected 2026-06-01: was 1.35V (datasheet misread); correct value
# is 0.99V per TPS25940A datasheet §6.6 Electrical Characteristics + DECISIONS.md §13
# "OVP threshold voltage on OVP pin" = 0.99V typ.
V_OVP_TH = 0.99          # V — internal OVP comparator threshold (typ)
T_OVP_RESPONSE = 8e-6    # s — TPS25940 OVP-to-FET-off response time (typ)
                         # Source: SLVSCM5 §6.6 Electrical Characteristics
                         # "OVP response time" t_OVP = 8 µs typ
T_GATE_DISCHARGE = 2e-6  # s — internal gate discharge slew (typ from datasheet)
                         # NMOS gate-off transition from V_GS=5V to V_GS=0V

# ---- novapcb divider values (per bom/novapcb-bom.csv lines 33+34) ----
# Per DECISIONS.md §13: R9 = 51 kΩ (top, between V_IN and OVP pin), R10 = 10 kΩ
# (bottom, OVP pin to GND). BOM ref labels are R7 (bot) + R9 (top) but DECISIONS
# uses R9/R10. Same physical components.
R_BOT = 10e3             # Ω — OVP pin to GND (BOM label R7, DECISIONS label R10)
R_TOP = 51e3             # Ω — V_IN to OVP pin (BOM label R9, DECISIONS label R9)
# OVP trips when V_OVP_pin = V_OVP_TH; V_OVP_pin = V_IN × R_BOT / (R_TOP + R_BOT)
# → V_IN_trip = V_OVP_TH × (R_TOP + R_BOT) / R_BOT
V_TRIP_IN = V_OVP_TH * (R_TOP + R_BOT) / R_BOT

# ---- novapcb +5V_BEC bulk cap (per board) ----
C_BULK_5V_BEC = 4.7e-6   # F — C9 = 4.7uF X7R 0805 per BOM (sensor of eFuse OUT)

# ---- Downstream load post-eFuse-off ----
# After eFuse turns off, +5V_BEC_PROT discharges through the buck U2 which KEEPS
# DRAWING because MCU+sensors are still running (buck doesn't shut off until
# V_IN drops below UVLO ~2.4V).
# Buck V_IN draw at 5V input + 400mA +3V3 load ≈ (400mA × 3.3V) / (5V × 0.92) ≈ 287 mA
# At 8V input (post-fault, pre-decay), buck draws even less ~180 mA (constant power).
# Use 250 mA as the worst-case range estimate during the 8V → 5V decay.
I_LOAD_OFF = 250e-3       # A — buck-mediated load (constant-power-ish during decay)

# Buck V_IN abs-max safety check (TPS62177DQC datasheet)
V_BUCK_VIN_ABSMAX = 17.0   # V — TPS62177DQC V_IN absolute maximum rating

# ---- Scenario inputs (Sai-defined per spec) ----
V_MAUCH_FAULT = 8.0       # V — Mauch BEC stuck-on fault output
V_RAIL_BROWNOUT = 5.0     # V — gate per spec §3.6i.B (below this = MCU brownout risk)


def run():
    print("=== Sim 6i.B — Mauch over-voltage 8V stuck-on (analytical) ===\n")

    print(f"## Inputs")
    print(f"  Mauch fault output: {V_MAUCH_FAULT} V (stuck-on, no spec violation by Mauch alone)")
    print(f"  TPS25940 OVP threshold: V_OVP_TH = {V_OVP_TH} V (datasheet typ)")
    print(f"  OVP divider: R_BOT={R_BOT/1e3:.0f}k, R_TOP={R_TOP/1e3:.0f}k → V_TRIP = {V_TRIP_IN:.2f} V at +5V_BEC")
    print(f"  C9 bulk (+5V_BEC): {C_BULK_5V_BEC*1e6:.1f} µF")
    print(f"  Post-off load: {I_LOAD_OFF*1e6:.0f} µA")
    print()

    print("## Step 1 — Mauch fault propagates into +5V_BEC")
    print(f"  Mauch output = {V_MAUCH_FAULT} V → +5V_BEC = {V_MAUCH_FAULT} V (D1 ORFET on, low Rds, no V drop)")
    overshoot = V_MAUCH_FAULT - V_TRIP_IN
    print(f"  Overshoot above OVP trip = {V_MAUCH_FAULT} − {V_TRIP_IN:.2f} = {overshoot:.2f} V")
    if overshoot <= 0:
        print(f"  ⚠ FAIL — Mauch fault below trip threshold, OVP would not engage")
        return False
    print()

    print("## Step 2 — TPS25940 OVP response")
    print(f"  Datasheet OVP-to-FET-off response: {T_OVP_RESPONSE*1e6:.0f} µs (typ)")
    print(f"  Gate discharge slew: {T_GATE_DISCHARGE*1e6:.0f} µs (typ)")
    t_total_response = T_OVP_RESPONSE + T_GATE_DISCHARGE
    print(f"  Total OVP-to-off time: {t_total_response*1e6:.0f} µs")
    print()

    print("## Step 3 — +5V_BEC_PROT rail decay after eFuse off")
    # V(t) = V_initial × exp(-t / (R_load × C))
    # R_load = V / I_LOAD_OFF (we assume initially 8V, will drop)
    # Approximate as constant-I discharge: dV/dt = -I/C → V(t) = V_0 - I·t/C
    # for short-time, large bulk this gives faster decay estimate
    v_initial = V_MAUCH_FAULT  # +5V_BEC at moment eFuse turns off
    # Time to decay to 5.0V brownout threshold:
    dv = v_initial - V_RAIL_BROWNOUT
    t_decay = dv * C_BULK_5V_BEC / I_LOAD_OFF
    print(f"  V_initial post-eFuse-off: {v_initial} V (bulk cap retains)")
    print(f"  Brownout threshold: {V_RAIL_BROWNOUT} V")
    print(f"  Decay current: {I_LOAD_OFF*1e3:.0f} mA (buck-mediated, MCU+sensors keep running)")
    print(f"  Time to {V_RAIL_BROWNOUT}V: {t_decay*1e6:.1f} µs (linear-I model)")
    print(f"  Buck V_IN safety: 8V peak < {V_BUCK_VIN_ABSMAX}V abs-max → safe overstress margin {V_BUCK_VIN_ABSMAX - V_MAUCH_FAULT:.1f}V")
    print()

    print("## Step 4 — gate check")
    gate_a = t_total_response * 1e6 <= 50  # ≤ 50 µs OVP latch
    gate_b = (t_total_response + abs(t_decay)) * 1e6 <= 100  # ≤ 100 µs to recover
    print(f"  Gate 6i.B.a: OVP latch ≤ 50 µs? response={t_total_response*1e6:.0f} µs → {'✅ PASS' if gate_a else '❌ FAIL'}")
    # gate b is "rail drops below 5V within 100 µs" — but actually we want the OPPOSITE:
    # MCU rail recovers BELOW the brownout threshold so it stops being abused?
    # Re-reading spec §3.6i.B: "eFuse latches off within 50 µs; +5V_BEC_PROT rail drops < 5.0V within 100 µs"
    # That means TURN OFF + RAIL DECAY both happen fast.
    # +5V_BEC_PROT (after eFuse): once eFuse off, the rail is isolated from Mauch.
    # The rail then decays per load. We want it BELOW 5V quickly (downstream MCU brownout protection).
    # With 4.7µF + 200µA, time to discharge from 8V → 5V = 3V × 4.7µF / 200µA = 70.5 µs
    # Combined with 10 µs OVP response → 80.5 µs total. Within 100 µs gate.
    total_t = (t_total_response + abs(t_decay)) * 1e6
    print(f"  Gate 6i.B.b: Total OVP+decay ≤ 100 µs? total={total_t:.0f} µs → {'✅ PASS' if total_t <= 100 else '❌ FAIL'}")
    print()

    overall_pass = gate_a and total_t <= 100
    print(f"## Verdict: {'✅ PASS' if overall_pass else '❌ FAIL'}\n")

    if not overall_pass:
        print("## Fail-fix proposals (per spec §7)")
        if total_t > 100:
            print("  - Reduce C9 bulk: 4.7µF → 1µF lowers decay time by 4.7×")
            print("  - Increase OVP divider precision: tighter R9 (0.1% vs 1%) reduces V_TRIP variance, improves overhead")
        if not gate_a:
            print("  - Replace TPS25940 with faster-response part (TPS25928 has 4 µs OVP)")

    return overall_pass


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
