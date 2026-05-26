# Phase 4d-redux — power-tree routing brief

> **Status:** master plan 2026-05-26. Awaiting fresh worker context to execute.
> **Trigger:** Rule 23 catch (`docs/POWER_TREE_DEFECT_SURVEY.md`) — board would NOT power up as currently routed. 64 latent unconnected across 22 power/critical nets, hidden in 213-total because plane-pour pads dominated.
> **Sai-gate:** none — pure execute against the defect-list spec. Master pre-merges gate-clean.
> **Priority:** THE freeze blocker. Nothing else moves Phase 7a until this completes.

---

## 1. Scope

Close all REAL LATENT unconnected on the power tree + the critical non-plane signals that the audit found. Reference: `docs/POWER_TREE_DEFECT_SURVEY.md` (per-net + per-pad).

**Out of scope:** signal rebuilds (CRSF/CAN/microSD/GPS/MOT1-6 already routed); plane fills (In1.Cu/In2.Cu/In3.Cu/In4.Cu already poured); intended-deferred (MOT7/8, Telem J3, SWD J9 — separate Sai-gates).

**In scope:** every net flagged REAL LATENT by `scripts/audit_unconnected_per_net.py`.

## 2. Domain breakdown + execution order (criticality)

| Domain | Nets | Pads | Why first |
|---|---|---|---|
| **D1 buck regulator** | U2_FB, U2_SW | 5 | Without these, NO +3V3 anywhere. Everything else depends on +3V3. |
| **D2 +5V input distribution** | +5V (24 of 27 unrouted) | 24 | Feeds D1 input + USB-C + connectors. Without this, no +5V → no buck → nothing. |
| **D3 eFuse U6** | +5V_BEC_PROT, EFUSE_FLT, EFUSE_PGOOD, EFUSE_DVDT | 13 | Protection between D2 and downstream loads. D3 sits between D2 and the +5V_BEC plane. |
| **D4 MCU core power** | VCAP1, VCAP2, +3V3A/VDDA, VREF_P, VBAT, BOOT0 | 17 | MCU will not clock without VCAP1/VCAP2. ADC won't read without VDDA/VREF. RTC needs VBAT. |
| **D5 +3V3_IMU rail gap-close** | 5 near-miss pads | 5 | IMU3 + IMU2 redundancy. Plan doc exists: `docs/3V3_IMU_RAIL_GAP_FIX_PLAN.md`. |
| **D6 USB-C + misc partials** | USBC_CC1/CC2, IMU3_INT1, HEATER_DRAIN, BATT_*_SENS partial, I2C2 partial | ~10 | USB-C CC pulldowns required for USB enumeration. Misc signal closures. |

**Recommended PR sequence:** D1 → D2 → D3 → D4 → D5 → D6. Each PR scoped to ONE domain, gated on per-net audit clean for that domain.

## 3. Per-domain execution notes

### D1 — Buck U2 (TPS62177)
- **U2_FB:** R47/R48 divider already placed near U2 SE (per Option-B placement PR #96). Route F.Cu short trace from R47.2/R48.1 to U2.5. Both passives are 0402; trace length ~3 mm; trivial.
- **U2_SW:** L1 inductor placed N of U2. Route F.Cu wide trace (0.40+ mm, high di/dt) from U2.9 to L1.1. Keep loop area tight against +5V_BEC plane below (low EMI). Worker should consult Option-B placement doc for L1 orientation.
- **Verify:** Sim 5 PDN re-run is optional but recommended after D1+D4 land (the buck output impedance feeds the PDN model).

### D2 — +5V input distribution
- The protected **+5V_BEC plane (In2.Cu)** IS already poured — that's NOT this work. The raw **+5V from USB-C VBUS → eFuse U6 input → buck U2 input** is what's missing.
- 24 pads: USB-C VBUS pads (J1.A4/A9/B4/B9), eFuse input pads (U6.3-8), buck input pads (U2.2/3/8), USB ESD/decap chain (U5.5, C31, C32, C9, C83, C85), JST-GH +5V pins (J3.1, J5.1, J10.1, J20.1), R5/R13/R61 pulls.
- **Approach:** likely a F.Cu trunk along the W edge (where the eFuse + buck live) with branches to the connectors. Could be a small filled-zone on F.Cu for the +5V trunk if width supports it. Consult the original B-power placement doc (#85 era) for intent.
- **Audit gate:** +5V per-net unconnected drops from 24 → 0.

### D3 — eFuse U6 (TPS25940A)
- 4 sub-nets: +5V_BEC_PROT (eFuse output before pass FET Q2), EFUSE_FLT/PGOOD (status flags to MCU), EFUSE_DVDT (slew-rate cap).
- **+5V_BEC_PROT** has 9 pads (R9, D1, U6.9-13, C8, Q2.3, R7) — needs a short F.Cu trace from U6 output to Q2 pass FET source.
- **EFUSE_FLT, EFUSE_PGOOD** — 2 nets, 2 pads each. Short routes to MCU GPIO pins (verify hwdef.dat for current pin assignments — pin remap may have changed PG/FLT mapping).
- **EFUSE_DVDT** — partial (3/1 trk/via, 1 gap). Stub closure to C7.1.

### D4 — MCU core power (the hardest)
- **VCAP1/VCAP2** — MCU pins 48 + 73; caps C17/C18 already placed adjacent. Route F.Cu stubs ≤3 mm. CRITICAL: VCAP1/VCAP2 traces must be SHORT + DIRECT — these regulate the MCU's internal core voltage; long traces = oscillation / clock failure.
- **+3V3A/VDDA** — pin 21 → FB1 ferrite → C19/C20 → tap from +3V3 plane. The FB1 ferrite isolates analog supply from digital noise. Route per ST AN4830 + STM32H7 reference design: short trace through FB1, then star-connect C19/C20.
- **VREF_P** — pin 20 → R1 (likely 0Ω or small) → C21/C22 → +3V3A. ADC reference; tight to VDDA topology.
- **VBAT** — pin 6 → C23 + R2. Battery backup for RTC; typically tied to +3V3 in production unless coin-cell present.
- **BOOT0** — pin 94 → R3 (pulldown to GND). Boot-mode strap. Single short trace.

### D5 — +3V3_IMU rail (5 gaps)
- Follow `docs/3V3_IMU_RAIL_GAP_FIX_PLAN.md` per-trace plan, easiest-first sequence (C93 → C92 → C91 → U9.5 → U9.8).
- Dense-pocket; worker should expect 1-2 DRC iters per gap.

### D6 — USB-C + misc partials
- **USBC_CC1/CC2** — J1.A5/B5 → 5.1 kΩ pulldowns R31/R32 → GND. Required for USB enumeration as a UFP (the Pi sees the FC). Short F.Cu traces.
- **IMU3_INT1** — U9.4 → U1.36 (MCU PB2 per hwdef post-remap). Single trace.
- **HEATER_DRAIN** — R61.2 → Q5.3 (heater FET drain). Single trace.
- **BATT_CURRENT_SENS / BATT_VOLTAGE_SENS partials** — close the 1-pad gap each.
- **I2C2_SCL/SDA partials** — close the 1-pad gap each (these mostly route from R11/R12 pulls to U4 DPS310 baro + MCU pins).

## 4. Verification gates (each PR + final)

**Per-PR (per domain):**
- [ ] `scripts/audit_unconnected_per_net.py` returns 0 latent for the domain's nets
- [ ] DRC total ≤ baseline + 0 net-new violations
- [ ] Per-net cluster walk on the new traces (F.Cu over In1.Cu/In3.Cu reference; B.Cu over In4.Cu)
- [ ] ArduPilot `waf configure --board novapcb-v1 && waf copter` succeeds (firmware build verify; same gate as PR #119, #120)
- [ ] No collateral damage: USB diff pair (PR #75), SPI1/2/3, CAN, microSD, MOT1-6, CRSF — none touched
- [ ] ERC clean (no schematic-side effect)

**Final (after D6 lands):**
- [ ] `scripts/audit_unconnected_per_net.py` returns 0 latent across ALL power + critical nets
- [ ] Total DRC unconnected = plane-pour-noise (139) + intended-deferred (10) + 0 latent
- [ ] **Sim 1 thermal re-run** (was invalidated; MCU now actually clocks)
- [ ] **Sim 5 PDN re-run** (was invalidated; local stubs now exist)
- [ ] Update `STATUS.md`, `PHASE_7A_FREEZE_CHECKLIST.md`, `pcb.html` — restore "all routing complete" + "flight-routable" with the artifact-verified evidence

## 5. Branch + PR conventions

- One branch per domain: `hw/d1-buck-routing`, `hw/d2-5v-distribution`, `hw/d3-efuse`, `hw/d4-mcu-core-power`, `hw/d5-3v3-imu-gaps`, `hw/d6-misc-partials`
- One PR per branch. Master pre-merges gate-clean.
- Each PR doc: 4-section template (Symptom / Fix / Root cause / Prevention)

## 6. Risk + fallbacks

- **D1 (buck FB/SW):** trivial layout; if any unexpected SI on SW node, route SW as polygon (per TPS62177 datasheet recommended layout).
- **D2 (+5V distribution):** if no clean F.Cu trunk possible across 24 pads, fall back to a +5V mini-zone on F.Cu (filled poly tied to +5V net). Check it doesn't conflict with +5V_BEC In2.Cu zone vertically.
- **D4 (MCU core power):** VCAP1/VCAP2 SHORT requirement is the constraint — if C17/C18 placement isn't already ≤3 mm to pins, re-place caps before routing (per Rule 20 move-passive-before-trace).
- **D5 (+3V3_IMU 5 gaps):** dense-pocket; fallback per plan doc — if 1+ fresh attempts fail, drop U9 LSM6DSV16X (true v2 defer, BOM + DECISIONS amendment, Sai ratifies).
- **D6 USB-C CC:** if pulldown placement is far from J1, can put pulldowns on B.Cu near J1 instead — small geometry change but cleaner routes.

## 7. After Phase 4d-redux

- Restore STATUS / freeze checklist / pcb.html "flight-routable" claim with artifact-side evidence
- Re-run Sim 1 + Sim 5 with the now-actually-powered MCU
- BOM final verify (R61 value + 9 LCSC — Sai-side at JLC portal)
- Telem v2-defer + SWD test-pads ratify (Sai)
- GUI DRC final verify on freeze head (Sai's Pi)
- Phase 7a freeze trigger (Sai)
- Phase 7b fab order (Sai $$)

---

**Brief author:** master 2026-05-26 (post worker PR #121 defect survey + Rule 23 tool).
**Execution dispatch:** next fresh worker context, sequential by domain D1→D6.
