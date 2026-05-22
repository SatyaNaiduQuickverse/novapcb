# Locked v1 decisions (2026-05-18)

All 9 scoping decisions for the v1 FC, signed off 2026-05-18. Each section shows the resolution line on top; the original options and discussion are kept below so the reasoning isn't lost. New open questions go in `OPEN_QUESTIONS.md`, not here. Owner: Sai.

## 1. MCU

**Resolved 2026-05-18:** STM32H743VIT6 — the **Holybro Pixhawk 6X (the autopilot currently flying)** uses STM32H743xx per the `Pixhawk6X` ArduPilot hwdef, so H743 keeps full ArduCopter parity with what the surrounding stack already talks to. MatekH743 is the closest single-PCB H743 reference to fork for v1's functional-drop-in scope; Pixhawk6X hwdef is the reference for v2.

**Options on the table:**

- **STM32H743VIT6** — what the Holybro Pixhawk 6X uses (and MatekH743, Pixhawk 6C, and several others). Highest software path-of-least-resistance; existing board defs to fork. Note: CubeOrange/CubeOrangePlus are H757 (dual-core); not the right reference for novapcb.
- **STM32H753** — cryptographic peripherals; nice if we ever want signed firmware, otherwise overkill.
- **STM32H723** — cheaper, smaller flash; tight for ArduCopter.
- **RP2350** — interesting because we're already a Pi house, dual-core M33, but ArduPilot doesn't target it; would need a non-ArduPilot firmware path (INAV / Betaflight / custom MAVLink shim). Punts on ArduCopter parity.

**Recommendation:** start with H743 unless there's a strong reason not to. It keeps the firmware story trivial.

## 2. Form factor

**SUPERSEDED 2026-05-20 (Sai pivot, mid-Phase-4)**: the 36×36 / 30.5×30.5 M3 v1 spec is set aside. New direction:

**v1.1 = 105 × 85 mm RECTANGULAR** (LOCKED 2026-05-23 by master after corrected gate12 v3 + rigorous-powers thermal sweep). A new airframe tray is required (v1 is functional drop-in, not mechanical).

**v1.1 outline evolution (kept for full traceability):**

| Iteration | Outline | Driver | Status |
|---|---|---|---|
| Original v1 | 36 × 36 mm | Pixhawk mini-FC standard | Superseded 2026-05-20 (Sai pivot — density drove Phase 6 P0 failures) |
| STEP4 Path B | 80 × 60 mm | First Elmer-arbitrated grown size | Superseded 2026-05-23 (gate12 v3 finding — MATC bbox formulation was mesh-divergent → Path B 75.2°C was a sim artifact; corrected MCU = 84°C → FAILS 80°C) |
| Interim v1.1 | 90 × 70 mm | Sai 2026-05-23 ("90×70 is final, no mechanical-fit check") | Superseded same-day (gate12 v3 + rigorous powers showed MCU=83.86°C on this size → FAILS 80°C target by 3.86°C) |
| **v1.1 final** | **105 × 85 mm** | **gate12 v3 board-size sweep, master sign-off 2026-05-23** | **LOCKED** |

**Reliability mandate** (Sai 2026-05-20, verbatim: "it working 100% is the priority", "strong resilient stuff that won't fail"): use the freed board area for generous spacing, clean subsystem separation, robust margins — design so EMI/EMC/thermal failure modes simply don't arise. Quality + real workability over time-to-build.

**v1.1 final dimensions (105 × 85 mm — locked 2026-05-23):**
- Board outline: 105 × 85 mm
- Aspect ratio: 21:17 (consequence of outline)
- Layer count: 4 vs 6 — still OPEN (Phase 0.6 pivot Step 3 assesses, see `OPEN_QUESTIONS.md pivot-2026-05-20` items 1-3)
- **Mounting pattern: 4× M3 corner-inset holes** (master decision 2026-05-23): **3.25 mm edge inset, c-to-c 98.5 × 78.5 mm**, positions (3.25, 3.25), (101.75, 3.25), (3.25, 81.75), (101.75, 81.75). Hole spec per `PLACEMENT_STRATEGY.md §5.2`: 3.2mm drilled NPTH, through-plated, **5.5 mm** GND-pad land to chassis GND. (Originally specified as 3.0mm inset / 99×79 c-to-c / 5.0mm pad; on apply discovered the actual mounting-hole footprint uses 5.5mm pads, which at 3.0mm inset leaves only 0.25mm to board edge — violates 0.5mm edge-clearance rule. Shifted to 3.25mm inset; mechanical mounting tolerance accommodates the 0.5mm c-to-c shift.)
  - +2 mid-long-edge holes (6 total) gated on Phase 6 vibration sim. Placement RESERVES keep-out at mid-edge positions (3.25, 42.5) and (101.75, 42.5) — 8mm circular keep-out for free sim-driven add later.
  - Pixhawk-standard 30.5×30.5 M3 pattern formally dropped.

**v1.1 thermal verification (the basis for the 105 × 85 sizing):**

Board-size sweep with gate12 v3 (per-body Body Force assignment + energy-balance gate + min-mesh-density gate — see `hardware/kicad/novapcb-stepwise/gate12_thermal.py` commit `3f80f3b`) + rigorous powers (MCU = 0.700 W realistic-worst per `docs/MCU_POWER_BUDGET.md`; U2 LDO = 0.642 W absolute-worst per `docs/THERMAL_3V3_BUDGET.md`; Q5 IMU heater = 0 W hot-case thermostatic; all v1.1 sources):

| Board | Area mm² | Tj_MCU °C | Margin to 80°C |
|-------|----------|-----------|-----------------|
| 90 × 70   | 6300  | 83.86 | -3.86 FAIL |
| 95 × 75   | 7125  | 81.72 | -1.72 FAIL |
| 100 × 80  | 8000  | 77.25 | +2.75 TIGHT |
| **105 × 85** | **8925** | **73.98** | **+6.02 LOCK ≥5°C ✓** |
| 110 × 90  | 9900  | 74.52 | +5.48 LOCK |
| 115 × 95  | 10925 | 75.23 | +4.77 (sampling noise) |
| 120 × 100 | 12000 | 74.04 | +5.96 LOCK |

MCU asymptote ~74°C reached at ~9000 mm² (heat-spreading length scale of MCU at given k_xy reached). Sweep log: `sims/thermal-step4/runs/v11_sweep_2026-05-23.log`.

**LDO survives at 105 × 85**: U2 Tj = 73.03°C (margin +6.97°C to 80°C). LDO → buck escalation **CLOSED** (see `OPEN_QUESTIONS.md phase5-thermal-ldo-vs-buck`).

**v2 = FMUv6X mechanical drop-in** — still deferred (separate FMU + isolated-IMU boards, exact 6X mechanical match); see OPEN_QUESTIONS.

**Original-v1 record kept here for traceability:**
- *Resolved 2026-05-18; mechanical specs disambiguated 2026-05-20 (Phase 2.5 P1.1)*: v1 = Pixhawk-standard mini-FC single-PCB — board outline 36 × 36 mm, mounting holes 30.5 × 30.5 mm center-to-center M3 (4 holes; the "30.5×30.5 M3" Pixhawk-standard pattern, matching MatekH743 reference). Functional drop-in against the Holybro Pixhawk 6X. **Superseded by 2026-05-20 pivot above** because density on the 36×36 mini-FC drove the Phase 6 P0 findings (PDN anti-resonance at 100 kHz, AP2112K LDO Tj=88°C, inrush 3.39A, EMC harmonic intersections in GPS L1). Roomier rectangle + reliability mandate addresses all four.

- **Pixhawk standard 30.5×30.5 mm M3, single-PCB** (chosen for v1) — well-trodden form factor; closest reference design is MatekH743 (36×36 board, 30.5×30.5 c-to-c M3 holes). Functional swap only; the airframe needs a new tray since the Pixhawk 6X uses the FMUv6X pattern, not the 30.5×30.5 mini-FC pattern.
- **FMUv6X form factor, two-board (FMU + isolated IMU)** (chosen for v2) — true mechanical drop-in against the 6X. Significantly more complex (vibration isolation, exact connector pin-out, dual-board assembly); not worth blocking v1 on.
- **Custom outline** — only if there's a frame-fit problem with both of the above.

**Recommendation:** v1 = Pixhawk standard for fastest path to a flying custom FC; v2 = FMUv6X once v1 proves out.

## 3. ESC channel count

**Resolved 2026-05-18:** 8 channels (DShot300/600, PWM fallback) — H7 has the timers for free; 4 spare lines cover hex/gimbal/payload contingencies without a re-spin, at the cost of connector real-estate only.

4 / 6 / 8. Depends on the airframe — the current Nova drone is a quad (4 motors), but we may want headroom for a hex or for gimbal/payload PWM. 8 channels of DShot is cheap on H7 (timer-rich) so this is mostly a connector-real-estate question.

**Recommendation:** 8 channels — DShot on H7 is timer-cheap; gives headroom for hex/gimbal/payload without a re-spin. Cost is connector real estate.

## 4. ELRS RX integration

**Resolved 2026-05-18:** External RX module + on-board CRSF UART — skips RF layout risk for v1 while still retiring the ESP32-C6 bridge; the integrated-RF option is a v2 conversation.

- **Off-board** (status quo): RP4TD on USB, ESP32-C6 bridge, FC consumes CRSF over UART from the bridge.
- **On-board CRSF UART**: skip the ESP32, route ELRS RX directly to an FC UART. Saves a USB port and ~15 g.
- **On-board ELRS module socket** (SX1280 + STM32 daughterboard): all-in-one. Higher PCB risk — RF layout.

**Recommendation:** v1 on-board CRSF UART, RX module stays external. Skip the integrated RF for now.

## 5. Voltage / current monitoring

**Resolved 2026-05-18:** External Mauch power module via FC ADC input — matches what the existing airframe already runs; no on-board high-side current sensor to calibrate.

- Onboard hall-effect current sensor (e.g. ACS758) vs external power module (Mauch / Holybro).
- Mauch 200 A is what the current frame uses.

**Recommendation:** match what the airframe already has — external Mauch, FC just provides the analog input.

## 6. Logging / SD card

**Resolved 2026-05-18:** Yes, microSD slot for ArduPilot `.bin` logs — post-incident analysis is non-negotiable; cost is one connector and a few traces. Mechanical placement deferred to layout time.

ArduPilot wants a microSD slot for `.bin` logs. Yes/no and where it sits mechanically.

## 7. Connector standard

**Resolved 2026-05-18:** JST-GH (Pixhawk family) — matches every harness on the existing airframe; bring-up must not also require re-crimping cables.

JST-GH (Pixhawk standard) vs JST-SH 1.0 vs solder pads. JST-GH is bulky but matches all our existing harnesses.

## 8. PCB stack-up

**SUPERSEDED 2026-05-20 (Sai pivot)**: 4-layer was right for the tight 36×36 board; the new rectangular roomier outline reopens the 4 vs 6 question. Phase 0.6 pivot Step 3 (placement) assesses which is appropriate given:
- The reliability mandate ("won't fail") favors 6-layer if it materially reduces SI/EMI failure modes.
- Phase 6k EMC analytical found 4 harmonics above -40 dB in GPS L1 / ELRS bands — a 6-layer with a second clean GND or split power plane can reduce those.
- 6-layer ~25-40% more expensive at JLCPCB but trivial against the resilience priority.

**Recommendation pending Step-3 analysis**: lean 6-layer if it provides quantifiable EMI/SI improvement; stay 4-layer if 6 only adds cost without measurable failure-mode reduction.

**Original v1 record:**
- *Resolved 2026-05-18*: 4-layer for v1 — clean ground plane under the IMU is the load-bearing requirement; 6-layer is reserved for a v2 spin only if on-board RF lands.

## 9. USB VID/PID for the FC

**Resolved 2026-05-18:** ArduPilot allocation (option a) — request via the ArduPilot forum when the time comes; meanwhile firmware can set `USB_VENDOR_STRING` starting with `ArduPilot` since udev only requires the string prefix to match.

The FC's USB descriptor must include strings that produce `/dev/serial/by-id/usb-ArduPilot_*-if00` on the drone Pi (see INTERFACE_CONTRACT.md §3.1). udev does not require a specific VID/PID, but some ground-station / downstream consumers filter on VID/PID, so we should pick deliberately rather than re-use a random vendor's allocation.

**Options:**

- **(a) ArduPilot allocation** — ask on the ArduPilot forum / dev channel for a VID/PID assigned to this board. Matches the convention used by the Pixhawk 6X and other Pixhawk-family boards; downstream filters that whitelist ArduPilot-family devices will accept it without changes.
- **(b) pid.codes free pool** — request a PID under the `0x1209` (pid.codes) free VID for open-source hardware. Fast, no permission needed beyond a PR to pid.codes, but downstream Ardu-family VID/PID filters won't recognise it.

**Recommendation:** (a). Aligning with the ArduPilot allocation keeps us inside the family that downstream tools already expect; pid.codes is a fine fallback only if the ArduPilot path stalls.

Note: udev by-id resolution only requires the *string* prefix to match (`USB_VENDOR_STRING` starting with `ArduPilot`), not the VID/PID. So even before VID/PID is locked, firmware bring-up that depends only on the by-id symlink will work.

---

## 10. Reliability-first design priority (Sai pivot 2026-05-20)

**Resolved 2026-05-20 — Sai's directive, verbatim:** "it working 100% is the priority", "strong resilient stuff that won't fail", "quality + real workability over everything; time is not a constraint."

This is a **design principle**, not a specific component choice. Applied across the entire post-pivot design:

- **Spacing**: generous, not packed. The freed board area from the §2 form-factor pivot is spent on margin, not features.
- **Subsystem separation**: power tree at one end, sensitive analog+IMU at the far end, MCU central, connectors on edges. EMI / thermal / mechanical-cable-strain failure modes don't arise if the physical layout prevents them.
- **Failure-mode mitigation over justification**: when a Phase 6 sim surfaces a CAUTION (e.g. inrush 3.39A over the <2A criterion; AP2112K Tj=88°C borderline), the design FIXES it. We don't argue why the failure mode "probably won't trigger in practice." See §11 (inrush) for the first instance.
- **Worst-case boundary conditions**: thermal modeling at 50-60°C ambient (drone bay / sun-soaked), still-air convection (no airflow assumed). If it works there, it works in flight.
- **Deterministic over heuristic**: prefer designs whose failure-recovery behavior is predictable + repeatable. E.g. MOSFET-based soft-start beats NTC thermistor for inrush limiting because NTC has reliability caveats (steady-state voltage drop; fails to reset on fast warm power-cycle).
- **No premature optimization for cost / area / BOM count**: if a small upgrade materially reduces a failure mode, it lands.

This principle resolves design forks where reliability and another axis (cost, board area, BOM count) conflict — reliability wins.

---

## 11. +5V BEC input-protection front-end (pivot Step 2 — complete-front-end design)

**Resolved 2026-05-21** (iter 4, after Sai's adjudication of options + augmentation):
Active eFuse (TI TPS25940A) with programmable inrush-rate dV/dt + adjustable current
limit + UVLO + OVP + thermal shutdown + fault flag, preceded by a P-MOSFET
reverse-polarity guard and shunted by a unidirectional TVS for fast transients.
This replaces the four-iteration discrete-MOSFET soft-start exploration documented
in the archived iteration record below.

### Background

Phase 6a found inrush peak ~3.39 A at power-on (over the <2A SIMULATION_PLAN §6a criterion; likely over a typical 3A BEC's transient tolerance). Per §10 reliability mandate ("won't fail"), this is fixed in the design — not justified away. Sai's verbatim direction on the front-end: *"I want the best possible solution there."* That converted Step 2 from "discrete MOSFET soft-start" to "complete, best-in-class +5V input-protection front-end as one coherent resilient stage."

### Topology (iter 4 — three-stage front-end)

```
  +5V_BEC (Mauch J4 pins 1+2 — raw BEC output)
       |
       +─── Q2 (AO3401A P-FET, body-diode reversed) — reverse-polarity guard
       |    Q2.S = +5V_BEC, Q2.G to GND, Q2.D = +5V_BEC_PROT
       |    Normal polarity → body diode forward → Vgs=-5V → FET conducts (low loss)
       |    Reversed polarity → body diode reverse → Vgs≥0 → FET off (blocks reverse)
       v
  +5V_BEC_PROT
       |
       +─── D1 (SMAJ6.0A TVS, K=+5V_BEC_PROT, A=GND) — fast clamp on transients
       |    V_WM = 6.0V (no leakage in normal 5V±5% operation)
       |    V_BR_min = 6.67V (> eFuse OVP trip — TVS only fires for ns transients)
       v
  U6 (TI TPS25940A eFuse — IN side, pins 9-13)
       │   • Inrush dV/dt programmed via C_dVdT on dVdT pin (C7 = 100nF)
       │   • Current limit programmed via R_ILIM on ILIM pin (R4 = 42.2kΩ → 2.08A)
       │   • UVLO via R7/R8 divider on EN/UVLO pin (turn-on at V_IN ≈ 4.0V)
       │   • OVP via R9/R10 divider on OVP pin (cut at V_IN = 6.04V, lowered from 6.5V)
       │   • Thermal shutdown built-in (junction T > 150°C)
       │   • FLT/PGOOD open-drain outputs with R5/R13 pull-ups (MCU GPIO observable)
       v
  +5V (filtered, post-eFuse) → AP2112K-3.3 LDO U2 → +3V3
```

### Stage-by-stage rationale

**Q2 — reverse-polarity guard (P-MOSFET, body-diode reversed)**
- AO3401A P-FET, Source on +5V_BEC, Drain on +5V_BEC_PROT, Gate to GND.
- Normal polarity: body diode forward-biases first, then Vgs=-5V drives FET fully on → Rds(on)=50mΩ → 18 mV drop at 360 mA (negligible).
- Reversed polarity: body diode reverse-biases (blocks), Vgs is ≥0 (no enhancement) → FET stays off → reverse current cannot flow. Protects all downstream silicon from polarity-reversed Mauch insertion.
- Closes the deferred "+5V reverse-polarity / input protection" item flagged for Phase 6.5.

**D1 — fast-transient TVS clamp (SMAJ6.0A)**
- V_WM = 6.0V > 5.25V rail max → no leakage in normal operation (SMAJ5.0A's 5.0V V_WM was right at the rail nominal; lifted to SMAJ6.0A per master config-coordination review 2026-05-21).
- V_BR_min = 6.67V is ABOVE the eFuse OVP trip (6.04V) → OVP handles sustained over-voltage as the primary mechanism; TVS only conducts for ns-scale events too fast for the OVP comparator (datasheet 2µs response).
- V_C_max = 10.3V at 114A peak surge (worst-case lightning-class). For realistic drone-board transients (motor inductive kicks, hot-plug spikes, ESD, ~5-10A), V_C tracks much closer to V_BR (~7V). Phase 6.5 forum review can evaluate whether a tighter-clamp TVS is warranted given AP2112K's 6.5V V_IN abs-max; current design accepts that the LDO's brief overshoot tolerance plus the eFuse OVP cut-off cover the gap.

**U6 — TPS25940A eFuse (5 V, programmable inrush + current limit + UVLO + OVP + thermal + FLT/PGOOD)**
- The eFuse provides genuine **current-limit-by-construction**: the internal control loop holds I_OUT ≤ I_LIM by modulating the internal pass FET into current-source mode, regardless of upstream BEC ramp profile. This was option (b) in the iter-3 adjudication — Sai chose (b), and Sai's "best possible solution" augmentation expanded it into the full front-end above.
- Configuration values (R_ILIM, R_dVdT, R_UVLO, R_OVP) are set per the datasheet's design equations; the resulting operating points are tabulated in "Configuration values" below.

### Configuration values (datasheet-formula derived)

| Parameter | Pin | Component | Value | Result |
|---|---|---|---|---|
| Current limit (OC ceiling — see "OC vs inrush" note below) | ILIM (17) | R4 | 42.2 kΩ | I_LIM = K_ILIM / R_ILIM = 88000 / 42200 = **2.08 A** |
| Output ramp time (controlled by dVdT pin) | dVdT (18) | C7 = 100 nF | — | TPS25940A datasheet Eq: T_RISE = (V_OUT × C_dVdT) / I_dVdT = (5 V × 100 nF) / 10 µA = **50 ms ramp**. dV/dt = V_OUT / T_RISE = 5 V / 50 ms = **100 V/s** (= 0.1 V/ms). I_dVdT taken at datasheet typical (10 µA) — production range is ~9–11 µA, putting T_RISE between 45 and 56 ms. |
| UVLO turn-on | EN/UVLO (14) | R7 = 30.1 kΩ (top), R8 = 10 kΩ (bot) | — | V_UVLO_on ≈ 1.0 V × (R7+R8)/R8 = **4.00 V** (turns on after BEC has settled past brownout) |
| OVP threshold | OVP (15) | R9 = 51 kΩ (top), R10 = 10 kΩ (bot) | — | V_OVP_trip = 0.99 V × (R9+R10)/R10 = **6.04 V** (8% margin under AP2112K V_IN abs-max 6.5V; below TVS V_BR_min 6.67V so OVP fires first) |
| FLT pull-up | FLT (20) | R5 = 10 kΩ | — | Open-drain → MCU GPIO can observe fault assertions |
| PGOOD pull-up | PGOOD (2) | R13 = 10 kΩ | — | Open-drain → MCU GPIO can observe "good" status |
| PGOOD threshold ref | PGTH (3) | tied to OUT via R-divider (TBD Phase 6.5 if firmware needs it) | — | Optional; current schematic ties PGTH to OUT directly (PGOOD = OUT > 90% nominal) |
| IN bypass | IN (9-13) | C8 = 100 nF | — | Decoupling close to IN pins |
| OUT bypass | OUT (4-8) | C9 = 1 µF | — | Decoupling on the protected rail (in addition to existing post-stage caps) |

### OC ceiling vs power-on inrush — clarification

These are **two different quantities**; conflating them was the framing error master flagged in the iter-3 adjudication:

| Quantity | Magnitude | Derivation |
|---|---|---|
| **Cap-charge component of inrush** | **0.67 mA** | `I_charge = C_+5V × dV/dt`. C_+5V on the post-eFuse rail = C9 (1µF) + C31 (1µF) + C32 (4.7µF) = **6.7 µF**. dV/dt = 100 V/s (from C7 = 100 nF, per Configuration table above). 6.7 µF × 100 V/s = 0.67 mA. |
| **LDO + board operating-draw component (during ramp)** | **ramps 0 → ~360 mA** over the last ~14.5 ms of the 50 ms ramp | AP2112K LDO's V_UVLO ≈ 3.55 V (datasheet). The eFuse output crosses 3.55 V at t ≈ 35.5 ms into the 50 ms ramp; from there to t = 50 ms the LDO regulates 3.3 V and the board's full quiescent + load draw (≈ 360 mA worst case) flows through the eFuse. |
| **Total power-on inrush peak through the eFuse** | **≈ 360 mA at end-of-ramp** (load-dominated, not cap-charge-dominated) | Sum: 0.67 mA (cap) + 360 mA (LDO + board) ≈ 360 mA. The cap-charge is two orders of magnitude smaller than the operating-draw component and does not set the peak. |
| **OC ceiling** (eFuse hard current-limit; fires only on faults — short circuit, downstream silicon failure, etc., NOT on power-on) | **2.08 A** (R4 = 42.2 kΩ) | eFuse internal control loop |

**The §6a <2 A criterion is met by the inrush peak (~360 mA at end-of-ramp), with 5.5× margin.** The 2.08 A OC ceiling is the *protection ceiling for fault conditions*, deliberately set well above normal operating + inrush so the eFuse does not false-trip on legitimate cold-start. The two values serve different roles and must not be conflated.

This corrects the iter-3 framing where "0.81 A from C×dV/dt" was offered as the inrush peak — that was off by 1000× (dimensional error: 16.3µF × 50 V/s = 0.815 **mA**, not 0.81 A). The current iter-4 design produces ~0.7 mA cap-charge + load-dominated peak of ~360 mA, plus a 2.08 A fault ceiling — all three numbers serve distinct purposes and are mutually arithmetic-consistent (verifiable from C × dV/dt with the values stated in the Configuration table above).

### Protection-stage coordination (non-conflict check)

The three protection mechanisms must coordinate so they don't fight each other or leave a gap. Verified numerically:

| Event class | Time scale | Active stage | Why other stages don't interfere |
|---|---|---|---|
| Normal operation (4.75–5.25 V, ≤360 mA) | steady | none — straight pass-through | TVS V_WM=6.0V (above rail max → no leakage). eFuse I_OUT=360 mA (well below 2.08 A I_LIM → no current-limit regulation). eFuse V_IN=5V (below OVP 6.04V → no OVP trip). Q2 body diode forward → low-Rds path. |
| Cold-start inrush (5V applied to discharged caps) | full output ramp ≈ 50 ms | eFuse dV/dt-controlled ramp on OUT (100 V/s) | Q2 conducts immediately. TVS doesn't conduct (V < V_WM). eFuse OUT ramps slowly per C7=100nF → ~50 ms; OC ceiling never approached (peak ≈ 360 mA at end-of-ramp). UVLO holds OUT off until V_IN > 4 V. |
| Sustained over-voltage (e.g. 6S battery accidentally on 5V port, BEC fault) | ms+ | **OVP cut-off at 6.04 V** | OVP trips at V_IN=6.04 V — *below* TVS V_BR_min=6.67V (TVS doesn't conduct) and *below* AP2112K V_IN abs-max 6.5V (downstream protected). eFuse disconnects OUT, asserts FLT. |
| Fast transient / surge (lightning, ESD, hot-plug spike, ns–µs scale) | ns–µs | **TVS clamp at ~7–10 V** | Faster than eFuse OVP comparator's 2 µs response. TVS absorbs the transient energy; eFuse OVP then catches any residual sustained component. AP2112K's abs-max is for *DC* — short ns/µs overshoots above 6.5V are within the LDO's transient survival envelope (per Diodes Inc. app-note guidance). |
| Reversed polarity (Mauch installed backwards) | DC | **Q2 body diode blocks** | Q2 Vgs=0 → FET off, body diode reverse-biased. eFuse IN sees ~0 V — never enters reverse-current regulation. TVS sees 0 V. Downstream silicon protected. |
| Downstream short / over-current (DSP load fault) | µs+ | **eFuse current limit at 2.08 A** | eFuse modulates pass FET to hold I_OUT ≤ 2.08 A; if condition persists, thermal shutdown trips at T_J > 150°C; FLT asserted. Q2 and TVS don't see the fault (it's downstream of U6). |

The coordination is non-conflicting: each stage's activation threshold is *outside* the next stage's normal operating envelope, so they don't false-trigger each other.

### Verification basis (honest accounting)

- **TPS25940A SPICE model**: TI does **not** publish a usable PSpice/SPICE model for the TPS25940A. The closest TI eFuse families (TPS25946x, TPS25985x) have models, but the TPS25940A specifically is not in TI's standard model library distribution (verified via the SLVMxxx-zip search pattern; the matched zips contain unrelated parts like TPS62080A). Therefore the verification basis for U6's design is **the datasheet's design equations + parametric guarantees** (I_LIM accuracy, V_OVP_REF, V_UVLO_REF, dV/dt formula). These are hardware guarantees the silicon meets at the IC level — not a behavioral SPICE approximation that could mis-model.
- **Per master directive 2026-05-21**: a hand-built behavioral SPICE model of an eFuse is circular (it would just confirm the equations we used to build it). If no usable official model exists, datasheet-formula configuration verification IS the honest verification. We do not pretend otherwise.
- **Phase 6.5 forum review** (deferred but required before fab): post the configuration values to the ArduPilot / PX4 hardware Discord/forum for sanity-check by EEs who have shipped TPS25940-based boards. Specifically ask: (1) is R4=42.2kΩ → I_LIM=2.08A appropriate given downstream load profile; (2) is C7=100nF dV/dt rate appropriate; (3) is TVS V_BR coordination with OVP acceptable given AP2112K abs-max headroom.
- **Phase 6a re-sim**: the original simulation that found the 3.39 A inrush peak is now invalidated for this design — that sim modeled a discrete MOSFET soft-start that no longer exists. A new Phase 6a-rev sim can model the front-end's overall behavior (Q2 + TVS modeled as passive, U6 as a current-limit + dV/dt-controlled output) but is not load-bearing for merge approval given the verification basis above.
- **Phase 9 bench**: real-board oscilloscope measurement at power-on (V_IN, V_OUT, FLT, PGOOD) is the definitive verification. The eFuse's parametric guarantees + datasheet formulas are the *design-time* basis; bench is the *delivery-time* basis.

### Implementation (iter 4)

- `hardware/kicad/novapcb/sheets/power_3b.py`: Q2 + D1 + U6 inserted between +5V_BEC and +5V. Old iter-3 Q1/R6/C5 (Miller MOSFET) removed.
- `hardware/kicad/novapcb/sheets/power_sd_swd_3h.py`: Mauch connector pins 1+2 are `+5V_BEC` (unchanged from iter 3).
- Net hierarchy: `+5V_BEC` → Q2 → `+5V_BEC_PROT` → (D1 to GND) + U6.IN → U6.OUT → `+5V` → AP2112K U2.
- Netlist regenerated: 83 components total.
- BOM updated: +U6 (TPS25940ARVCR), +Q2 (AO3401A), +D1 (SMAJ6.0A), +R4 (42.2kΩ), +R7 (30.1kΩ), +R9 (51kΩ), grouped 10kΩ row for R5/R8/R10/R13 + I2C-pullup R11/R12, +C7/C8 (100nF), +C9 (1µF reuses existing).

### Topology evolution record (archived — four iterations 2026-05-21)

The discrete-MOSFET path explored in iters 1-3 was abandoned at iter 4 because Sai's "best possible solution" augmentation made the eFuse the cleaner choice. The discrete iterations are preserved here only for archaeology — they are NOT the current design.

| Iter | Topology | Issue caught by master | Outcome |
|---|---|---|---|
| 1 | R6 G→S, C5 G→GND | Gate held LOW at power-up → Vgs=-5V instant → FET ON → no soft-start | INSTANT-ON, 8A peak |
| 2 | C5 G→S, R6 G→GND | Delayed turn-on, not controlled ramp; output dumped fast at FET wake | DELAYED-DUMP, 0.305A at 20ms delay but 0.1ms ramp |
| 3 | C5 G→D (Miller), R6 S→G | Miller plateau engages, output tracks BEC ramp; but does NOT bound absolute inrush — only bounds drain dV/dt relative to source dV/dt. Fails at artificially fast BEC ramps (10µs → 8.68 A peak); passes at realistic Mauch profile (370µs → 0.51 A peak). Sai adjudicated: option (b) "active current-limit IC", augmented with "best possible solution" → iter 4. | SUPERSEDED |
| **4 (current)** | **eFuse (U6) + reverse-polarity P-FET (Q2) + TVS (D1)** | — | **Current design.** Output ramp 50 ms @ dV/dt = 100 V/s (C7=100nF). Cap-charge inrush 0.67 mA + LDO/board load-dominated peak ≈ 360 mA at end-of-ramp. OC ceiling 2.08 A (eFuse I_LIM, fault-only). OVP 6.04 V. UVLO 4.00 V. TVS V_BR_min 6.67V. Reverse-polarity blocked by Q2. |

Lesson: the "deterministic over heuristic" §10 principle required current-limit-by-construction (eFuse), not RC-shape heuristics that depend on upstream ramp profile. The iter-3 Miller design was a working *dV/dt-shaping* device but not a current limiter; iter 4 is both.

## 12. Freeze-at-fab-ready + post-freeze shrink optimization (Sai 2026-05-21)

Two-phase strategy for getting to a fab order from a position of safety. Persisted here durable, conversation-only is not enough.

### Sai's verbatim intent

1. **FREEZE-AT-FAB-READY**: when the design reaches the Phase 7 gate (fab-ready — Steps 5+6 done, gerbers exportable, design validated), FREEZE and SAVE that design — a git tag on the fab-ready commit (e.g. `v1.0-fab-ready-frozen`). This is the validated, generously-margined 80×60 baseline — the surely-works fallback. The actual fab ORDER remains Sai's hard-stop sign-off (the freeze is at fab-READY, not order-placed).

2. **POST-FREEZE SHRINK-OPTIMIZATION** (a new phase — Sai's wording: "call it Phase 8: Optimization"; recorded in DESIGN_PHASES as Phase 7.5 to keep Assembly = 8 and Bring-up = 9 unchanged): AFTER the freeze, begin incrementally shrinking the board as small as it can go. Step by step, sim-driven — re-run the relevant sims (thermal especially: shrinking re-tightens the convection-limited regime; also SI, DRC) at each shrink step, discovering constraints as you go. KEEP FACTOR OF SAFETY and avoid conflicts — the shrink stops where margins (thermal, clearance) or DRC would be compromised. Not shrink-to-the-edge; shrink-while-still-safe. The frozen baseline is the fallback, so the shrink can be pursued from a position of safety.

### How this binds future decisions

- Phase 7a freeze must produce a git tag; the tag is immutable. Phase 7.5 shrink work MAY NOT delete or rewrite it.
- Phase 7b fab-order is bounded by Sai sign-off; master cannot place an order.
- The shrink stops at first margin-or-DRC violation; the doc-trail must show which margin was the binding constraint (so the chosen final dimension is defensible).
- If the shrink fails to improve materially, the frozen baseline ships. That is an acceptable outcome — the freeze exists precisely to make this safe.

### Cross-refs

- DESIGN_PHASES.md §Phase 7 (split 7a freeze / 7b order) and §Phase 7.5 (shrink optimization).
- The thermal sim regime that gates each shrink step is defined in SIMULATION_PLAN.md; shrink-step sims re-use that protocol.
