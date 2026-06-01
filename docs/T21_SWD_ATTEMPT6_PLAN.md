# T21 SWD J9 Attempt 6 plan — master pre-think (2026-06-01)

> Companion to `docs/T20_ATTEMPT6_PLAN.md`. Master ahead-of-time strategy
> doc for the SWD re-route campaign. Worker uses this when cycling to T21.
> Per Sai 2026-06-01 "no deferring, finish all now" mandate — must produce
> SWD physically routed in v1.

## Context

J9 SWD connector placed at (15, 35) B.Cu. SWDIO/SWCLK/NRST route from MCU
SW-corner pins to J9. First sweep walled 9 attempts (test-pads, J9 direct,
slow-net reroute, layer flip, J2 placement). Treated existing infrastructure
as fixed.

Worker T21 initial test 2026-06-01: 6 via-offset variants cascaded +55 to
+73 DRC delta. Under-MCU B.Cu corridor isn't actually clear.

Per Sai mandate: place-not-fixed; allow re-routing nearby B.Cu nets;
escalate until SWD routes; NO v2-defer.

## Attempt sequence (cheap → expensive)

### Attempt 6a — F.Cu narrow corridor between MCU and J2 (smallest change)
SWD is SLOW (1-10 MHz). 3 nets at 0.15mm trace width. Route on F.Cu through
narrow gaps in the MCU↔J2 corridor on the SW board side. No re-route of
existing nets needed if a clean path exists.

**Worker action:**
- Survey F.Cu open area between MCU LQFP-100 SW corner (PA13/PA14 pins
  at approx X=18-22, Y=42-46) and J9 at (15, 35)
- Try 3 candidate paths: direct diagonal, L-route via Y=40, L-route via X=18
- DRC delta per attempt logged
- First DRC-clean attempt wins

### Attempt 6b — Re-route 1-2 power-rail B.Cu nets near J9 (medium)
If 6a walls, identify which power-rail vias block the J9-MCU corridor.
Move 1-2 stitch vias 2-3 mm to free a clear path.

**Worker action:**
- Identify blocking vias via per-net audit in J9-MCU area
- Shift +5V_BEC / +3V3 stitch vias 2-3 mm
- Re-route SWD on the freed lane
- Sim 5 PDN spot-check (no margin change expected, plane still intact)

### Attempt 6c — Re-pin NRST only (SWDIO/SWCLK are fixed)
PA13/PA14 are dedicated SWD pins per ARM Cortex-M standard; CANNOT re-pin.
NRST is also dedicated. So this attempt is BLOCKED — skip.

### Attempt 6d — Re-place J9 to a less-walled location
J9 is the SWD connector itself. It can move anywhere within reachable
B.Cu radius of MCU SW corner. Candidates:
- (20, 25) — south of MCU
- (10, 40) — west of MCU  
- (25, 30) — diagonal from MCU
- (8, 35) — far west, but cable strain ok

**Worker action:**
- Survey 4 candidate XYs above
- For each: compute path from MCU PA13/PA14/NRST to J9 new XY
- Pick first DRC-clean candidate
- Update SKiDL placement + commit

### Attempt 6e — Touch SDMMC1 (hands-off) westward shift
Only if 6a-6d all wall. Same approach as T20 SDMMC1 wall-push but
focused on opening the SWD corridor instead of USART1 corridor.

**Worker action:**
- Coordinate with T20 if T20 already shifted SDMMC1; if so, use the
  freed space
- If T20 not yet done: do BOTH (SDMMC1 westward + SWD route in freed
  corridor)
- Mandatory Sim 3 SDMMC1 SI re-validation (≥95% margin per T20 contract)

## Process

- Per-net unconnected audit ABSOLUTE on every step
- Scope-creep cap watch (currently 4/4) — no NEW scope-creep exceptions
- Sim re-validation if SDMMC1 or IMU-island nets touched
- Multi-session WIP commits OK
- NO v2-defer outcome

## Gate

T21 closed when:
- SWDIO, SWCLK, NRST all routed cleanly from MCU pins to J9 pads
- audit_unconnected_per_net PASS, 0 real-latent on SWD nets
- DRC severity-error not increased beyond scope-creep cap
- If SDMMC1 touched: Sim 3 SI margin ≥ 95% confirmed

## Reference

- Original 9-wall analysis: `docs/SWD_PHYSICAL_DELIVERABLE.md`
- DFU first-flash backup (still works): `docs/DFU_BOOTLOAD_PROCEDURE.md`
- T20 SDMMC1 westward (related): `docs/attempt6/T20_ATTEMPT6_PLAN.md`
