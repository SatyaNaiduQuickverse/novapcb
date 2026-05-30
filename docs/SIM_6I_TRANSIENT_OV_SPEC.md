# Sim 6i — Transient Over-Voltage on +5V_BEC input (spec)

> **Status:** SPEC 2026-05-30 by master per Sai T8 raise-the-bar directive.
> **Worker action:** implement + run + commit results to `docs/SIM_6I_TRANSIENT_OV_RESULT.md`.
> **Purpose:** validate +5V_BEC protection topology (SMAJ6.0A TVS + U6 TPS25942 eFuse OVP + Mauch RC anti-alias) against realistic transient events. Closes the Phase 6i gate item CONFIDENCE_MAP row 11 committed to.

---

## 1. Scenarios to simulate

| Scenario | Insult source | Why it matters |
|---|---|---|
| **A. Lightning-coupled surge** | IEC 61000-4-5 surge waveform: 1.2/50 µs voltage, 8/20 µs current, 30V/100A peak coupled to +5V_BEC line via 50 Ω source impedance | Realistic EMC compliance baseline; SMAJ6.0A spec'd at 6V V_WM + 10.3V clamp |
| **B. Mauch BEC fault (over-voltage stuck-on)** | Mauch BEC fails to 8V steady-state (above eFuse OVP trip at 6.04V) | TPS25942 OVP should latch off ≤ 50 µs |
| **C. Hot-swap from second Mauch (J19)** | Live insertion of J19 with J4 already powered: di/dt from cable inductance + bus cap charging spike | ORFET U11/U12 hot-swap dynamic; how long is the +5V_BEC dip before settle? |
| **D. Reverse polarity at J4 (Mauch lead flipped)** | -12V applied to +5V_BEC | LM74700-Q1 ORFET (U11) must block reverse current; how fast does the FET turn off? |
| **E. Mauch ESC switching spike feed-through** | DShot600 600 kHz switching with 100mV pk-pk feeding back through Mauch | Worst-case ripple Mauch lets through; tests RC anti-alias on V/I sense + Mauch's own filtering |

## 2. Models needed

- **SMAJ6.0A**: V_BR = 6.67V (min), V_C = 10.3V @ 100A I_PP, junction capacitance ~3000pF. SPICE model from Littelfuse appnotes.
- **TPS25942 TI eFuse**: Texas Instruments PSPICE model (downloadable from ti.com — TPS25942 product page → Models tab). Has built-in OVP, ILIM, DVDT behaviour.
- **LM74700-Q1 ORFET**: TI PSPICE model. Critical: capture the gate-charge transient on FET turn-off.
- **+5V_BEC bus inertia**: lumped 100 µF (sum of bulk caps on bus) + 22 µH parasitic (Mauch cable + connector inductance)
- **Mauch source**: ideal 5V source behind 50 mΩ output impedance + 50 µH cable inductance

## 3. Pass criteria

| # | Gate | Why |
|---|---|---|
| 6i.A | Scenario A: MCU +3V3 rail stays within ±5% of 3.30V (3.135V–3.465V) during the 50 µs surge event | MCU unaffected by upstream surge |
| 6i.B | Scenario B: eFuse latches off within 50 µs of OVP threshold breach; +5V_BEC_PROT rail drops < 5.0V within 100 µs | OVP responsive |
| 6i.C | Scenario C: +5V_BEC dip during hot-swap stays > 4.6V (MCU brown-out is 4.6V via the buck +3V3 ride-through) | Hot-swap doesn't brown out MCU |
| 6i.D | Scenario D: ORFET turn-off complete within 1 ms; no current flows from +5V_BEC_PROT back to J4 | Reverse polarity contained |
| 6i.E | Scenario E: Mauch V/I ADC sense reads within ±10mV of true value during ESC switching | Anti-alias works |

## 4. Tool

- **ngspice** with TI/Littelfuse SPICE models. Run on worker (sim tooling already there per Sai's "sims on the Pi" memory).
- Optional: cross-validate Scenario A against an LTspice run if a contributor has the surge generator macro.

## 5. Output

Worker commits `docs/SIM_6I_TRANSIENT_OV_RESULT.md` with:
- Each scenario PASS/FAIL + trace plot (PNG embedded or linked from sim output dir)
- For any FAIL: root cause analysis + fix proposal (typically: more bulk cap, faster TVS, different eFuse setpoint)
- Summary table mirroring §3 above
- Update CONFIDENCE_MAP row 11 to HIGH if all 5 scenarios PASS

## 6. If a scenario fails

**No corner cuts** — fix the design, don't relax the gate. Likely fixes:
- **6i.A fail**: add 2.2 µF X7R bulk on +5V_BEC near the TVS (improves dV/dt response)
- **6i.B fail**: increase R9 OVP divider precision (lower trip threshold to 5.7V for faster response)
- **6i.C fail**: increase ORFET gate pull-down resistor (faster turn-on of incoming Mauch)
- **6i.D fail**: re-verify LM74700-Q1 SPICE model parameters; physical board may differ
- **6i.E fail**: increase C-anti-alias from 100 nF to 220 nF (drops cutoff from 1.59 kHz to 720 Hz)

Per Sai directive: any fail triggers design iteration, not gate relaxation.
