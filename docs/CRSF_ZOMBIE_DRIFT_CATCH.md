# CORRECTION 2026-06-02 — drift is NAMING ONLY, NOT functional

> **Master error #2 today + worker Rule-13 catch.** PR #179 (this doc) claimed CRSF was a fab-blocker functional bug. That was WRONG.
>
> Worker's deeper analysis: `crsf_usb_3g.py:142-143` shows SKiDL connects net `USART6_TX` to `mcu['PA0']` and net `USART6_RX` to `mcu['PA1']`. The COPPER physically connects pin 22 (PA0) and pin 23 (PA1) to J10 correctly. ArduPilot configures UART4 on PA0/PA1; the cable arrives at PA0/PA1; CRSF works.
>
> **What IS drifting: net LABELS.** The SKiDL author renamed CRSF from USART6 (PC6/PC7) to UART4 (PA0/PA1) for the MCU pin but kept the legacy net name `USART6_TX/RX`. Cosmetic, not functional.
>
> **Fix:** rename PCB nets `USART6_TX/RX` → `UART4_TX/RX` (cosmetic only; no copper change). Worker dispatched for this (c1) + the separate (c2-g) BATT2_SENS nudge for PE7/PE8 escape.
>
> **Master discipline note:** I called it a "fab-blocker bug" without verifying the SKiDL pin-bind line. Future error pattern to avoid: don't infer functional state from net names alone; verify against schematic-generation source.
>
> Original (incorrect-severity) text preserved below for traceability.

---

## Original (INCORRECT-SEVERITY) text — PRESERVED FOR TRACEABILITY

# CRSF zombie drift — Rule-9 catch (2026-06-02 worker)

> Worker session 2026-06-02 surfaced a critical fab-blocker bug while
> executing Option (c) of the T20 board-grow campaign. **PR #120 changed
> hwdef.dat (CRSF: USART6 PC6/PC7 → UART4 PA0/PA1) but the PCB CRSF
> routing was NEVER updated to match.**

## The bug

| Layer | What it says |
|---|---|
| `firmware/hwdef-novapcb/hwdef.dat` (since PR #120) | CRSF on UART4 PA0/PA1 |
| PCB routing (since PR #120 era) | CRSF cable to J10 still wired to PC6/PC7 (USART6) |
| Firmware behavior at boot | ArduPilot configures CRSF driver on PA0/PA1 |
| Physical reality | RC pulses arrive at PC6/PC7, MCU sees nothing on PA0/PA1 |

**Result on a fabricated board: CRSF receiver would visually appear connected (LED active) but RC channel data would not reach ArduPilot. Symptom at first-flight: "RC receiver detected but no input."**

This is a **fab-blocker bug** — the board as-is would not arm or accept RC input.

## How it slipped

PR #120 was scoped to firmware hwdef update only. Did not include PCB routing update. The 2-side update should have been atomic:
- hwdef change ✓ landed PR #120
- PCB routing change ✗ never done

The discrepancy was sitting since the PR #120 era (~ 2026-05-26).

## How it was caught

Worker session 2026-06-02 during T20 USART1→UART7 PE7/PE8 re-pin execution:
- Worker surveyed MCU south-bridge zone Y=37-42 X=37-46 for PE7/PE8 escape
- Found USART6_TX/RX segments at Y=39.5/39.75/40.0 occupying critical Y-bands
- Realized USART6_TX/RX shouldn't exist on PCB at all (hwdef says UART4 PA0/PA1)
- Cross-checked hwdef.dat — confirmed PR #120 era CRSF re-pin to UART4
- Confirmed UART4_TX/RX have 0 tracks on PCB

This is exactly the Rule-9 verify-the-artifact pattern that caught the
+3V3_IMU rail gap + the power-tree unrouted earlier in the project. Master
process win.

## Fix path

Master authorized Option (c) (2026-06-02 message thread):
1. Remove existing USART6_TX/RX traces (PC6/PC7) to J10
2. Add new UART4_TX/RX traces (PA0/PA1) to J10
3. USART6_TX/RX nets orphaned and removed from netlist
4. Per-net audit ABSOLUTE — USART6 should disappear from active nets

**Bonus:** removing USART6 routes from south-bridge zone frees Y-bands for
the in-flight T20 USART1→UART7 PE7/PE8 escape route. Two problems solved by
one cleanup.

## Lesson for process discipline

When changing hwdef.dat pin assignments:
- The PCB routing must update IN THE SAME PR (atomic change)
- Per-net audit at PR merge time should catch hwdef-PCB inconsistencies
- BOM critical-fix audit script (introduced 2026-05-30 PR #153) catches BOM
  drift but not net-routing drift; could be extended

Worker filed this caught-issue for permanent record. Process improvement
candidate for follow-up: hwdef ↔ PCB net consistency check in pre-merge
audit pipeline.
