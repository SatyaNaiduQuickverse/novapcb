# T22.2 partial — EFUSE_PGOOD LED only (master γ pick + error #3 ack)

> **Master pick 2026-06-02:** γ (partial — single EFUSE_PGOOD LED) over
> α (full 5 LEDs) / β (drop entirely). Per worker recommendation after
> Rule-13 catch on master framing error #3.

## Master framing error #3 today

I framed T22.2 as "5 LEDs reuse R41-R44" in my T22 sub-task plans (master
burst-1 and earlier T22 docs). That was WRONG.

**Reality (worker verified via SKiDL):**
- `power_sd_swd_3h.py:260` — R41 = r_vbat (BATT_V_SENSE 1kΩ series in Mauch ADC RC filter)
- `power_sd_swd_3h.py:271` — R42 = r_curr (BATT_I_SENSE 1kΩ series in RC filter)
- `power_sd_swd_3h.py:236` — R43 = r_vbat2 (BATT2_V_SENSE 1kΩ series in RC filter)
- `power_sd_swd_3h.py:246` — R44 = r_curr2 (BATT2_I_SENSE 1kΩ series in RC filter)

R41-R44 are the 1k-series part of the 1k+100nF Mauch RC anti-alias filter
(per CONFIDENCE_MAP row 11 + Phase 3h schematic capture). They are NOT
LED current-limiting resistors. The BOM note saying "LED current-limiting
resistors (status LEDs — Phase 3 schematic)" is STALE — likely from an
early Phase 3 plan that was reverted before R41-R44 got re-purposed for
Mauch RC.

## Master error pattern today (all 3 errors)

| # | Cited claim | Reality | How caught |
|---|---|---|---|
| 1 | PB14/PB15 free per PR #170 | PB14/PB15 held by SPI2 IMU2 (the survey said USED) | Worker pre-exec Rule-13 |
| 2 | CRSF PR #120 = fab-blocker bug | Copper physically connects PA0/PA1 to J10 correctly; net labels stale | Worker post-investigation Rule-13 |
| 3 | R41-R44 reuse for LEDs | R41-R44 are Mauch ADC RC filter resistors per SKiDL | Worker pre-exec Rule-13 |

Common pattern: cited BOM/doc claim without verifying SKiDL source.

**Discipline correction for future master dispatches:**
- Quote the source content directly (line numbers)
- Reference the file path + line that verifies the claim
- If can't verify quickly, say "needs verification" instead of asserting

## Master γ pick rationale

Three options worker proposed for T22.2:

| Option | What | Cost | Value |
|---|---|---|---|
| α | Add full 5 LEDs (+5V, +3V3, +5V_BEC, +3V3_IMU, EFUSE_PGOOD) | ~10 new components, scope-creep cap risk, schematic + placement + routing | Visual status for all 5 rails (but USB-CDC console covers same info for the 4 power rails) |
| β | Drop T22.2 entirely | 0 | Lose all visual status indication |
| **γ** | **Only EFUSE_PGOOD LED** | **+2 components (D26 + R49), minimal scope** | **Visible eFuse fault indication at boot — REAL debug value** |

**γ wins** because:
- EFUSE_PGOOD is the ONE rail where visual indication has clear debug value (eFuse fault = board doesn't power; LED tells you immediately)
- Other 4 rails: power-on means working, power-off means dead — USB-CDC enumeration tells you the same thing
- Honest scope reduction: 1 useful LED vs 5 mixed-value LEDs
- Not a defer in disguise — the SOTA goal was status visibility; γ delivers the highest-value status indicator

## Worker scope for γ execution

1. SKiDL: add 1 LED (D26) + 1 series-R (R49); wire EFUSE_PGOOD → R49 → D26 → GND
2. R49 value calc: (V_PGOOD - V_LED) / I_LED = (3.3V - 2.0V) / 2mA = 650Ω → standard 680Ω 0402
3. Netlist regen + PCB import
4. Place D26 + R49 in freed S area (near U6 eFuse if room)
5. Route short EFUSE_PGOOD trace + plane GND return
6. BOM: 2 new lines (D26, R49) with SAI-SOURCE TBD
7. Per-net audit + DRC + scope-creep cap pass

## Reference

- Worker SKiDL verification: `hardware/kicad/novapcb/sheets/power_sd_swd_3h.py:236-271`
- T3_REACH_FAILURE.md original "5 LED" full-scope attempt (reverted)
- BOM line 26 stale note (master process improvement candidate: BOM note re-audit needed when SKiDL changes happen)
