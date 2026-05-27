# PR — D3 eFuse U6 protection routing (Phase-4d-redux D3)

> Branch `hw/d3-efuse` off `sch/option-b-buck`. Closes the eFuse U6 (TPS25940A)
> protection nets — the third power-tree domain. **+5V_BEC_PROT fully routed**
> via a root-cause passive re-place; FLT/PGOOD v2-deferred (autonomous protection).

## 1. What landed

| Net | result |
|---|---|
| **+5V_BEC_PROT** (10 pads: U6.9-13 OUT, Q2.3 pass-FET, C8 decap, D1 TVS, R7.1/R9.1) | **routed, 0 unconnected** |
| **EFUSE_EN** (R7.2↔R8.1↔U6.14) | re-tapped after R7 move, 0 unconnected |
| **EFUSE_OVP** (R9.2↔R10.1↔U6.15) | re-tapped after R9 move, 0 unconnected |
| **EFUSE_DVDT** (U6.18↔C7.1) | closed (missing B.Cu→F.Cu via at C7.1) |
| **EFUSE_FLT** (U6.20↔R13.1), **EFUSE_PGOOD** (U6.2↔R5.1) | **v2-deferred** — see §3 |

Real-latent: 37 → 31 → **27** (then −2 from FLT/PGOOD deferral).

## 2. The root-cause unlock (R4 re-place — master option-b + broadened pre-auth)

The eFuse output region is walled off from its own output components by the
eFuse *config* traces: the EN/OVP F.Cu verticals (X30.5/31.3) + the **EFUSE_ILIM
B.Cu diagonal** (28.75,14.5→33.49,22) bisecting the pocket + USART6/CRSF + GND
pads. Scoped FR thrashed (240 s timeout, 0 progress).

**Fix (Rule-20 / root-cause-not-patch):**
- **R4** (ILIM-set µA bias resistor) re-placed 6 mm N → lifts the EFUSE_ILIM B.Cu
  diagonal entirely out of the Y17–22 band. This single move opened the corridor.
- **R7** (EN pull-up) + **R9** (OVP divider) re-placed out of the saturated
  X37-44/Y22-25 band toward the U6 output cluster (per master option-b).
- +5V_BEC_PROT then routed clean: W-crossing (B.Cu under the EN/OVP wall, now
  ILIM-free), C8→D1, E-tie (B.Cu under USART6, E of the ILIM end), R7-R9 tie,
  Q2.3 (B.Cu under the +5V VIN → W-crossing via).
- EN/OVP re-tapped to R8/R10; EFUSE_DVDT via added.

All re-placed passives (R4/R7/R9) **surveyed-first and verified clear of D1's
courtyard** — final courtyard-overlap count = baseline 2 (J20↔J19, U6↔C9), **0
net-new**.

## 3. FLT / PGOOD — v2 defer (not a defect)

`docs/EFUSE_STATUS_V1_DEFER.md`. The TPS25940A protection (OC/OV/thermal/reverse)
is **autonomous** — pass-FET cutoff fires regardless of MCU awareness. FLT/PGOOD
are open-drain *status* outputs (firmware-awareness only); Nova v1 has no
fault-handling pipeline consuming them, and the nets have no MCU-GPIO node.
Added to `INTENDED_DEFERRED` in `scripts/audit_unconnected_per_net.py` (same
pattern as Telem/SWD).

## 4. Verification (master's gate set)

- **Per-net audit:** +5V_BEC_PROT / EN / OVP / DVDT all **0 unconnected**;
  FLT/PGOOD classified intended-deferred (not real-latent).
- **DRC: 12 = baseline exactly** (2 courtyard + 5 drill + 5 via, all
  `.kicad_dru`-covered), **0 electrical** (clearance/shorting/crossing = 0),
  **0 net-new**.
- **`waf copter`: PASS** (board-only; hwdef byte-identical — see build log).
- **No flight-critical collateral:** net track-count diff vs base shows only
  +5V_BEC_PROT / EFUSE_EN / EFUSE_OVP / EFUSE_DVDT / GND changed; USB diff pair,
  SPI, CAN, microSD, MOT*, CRSF all byte-identical.
- **Cluster-walk:** all routed D3 nets continuous; R4/R7/R9 nets re-walked clean
  after the moves.

## 5. Scope

Closes **Phase-4d-redux D3**. Next: D4 (MCU core power). Sim 1 / Sim 5 re-gate
after D4 closes the MCU core.
