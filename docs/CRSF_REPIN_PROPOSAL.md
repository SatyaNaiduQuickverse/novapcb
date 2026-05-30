# CRSF re-pin proposal — USART6 (PC6/PC7) → UART4 (PA0/PA1)

> **Status:** master-locked 2026-05-26 (worker-verified empirical pad audit + master-verified datasheet AF). Execution-ready.
> **Trigger:** task #56 — current CRSF UART pins are in the NE-saturated MCU east-edge zone and empirically unroutable (4 distinct routing attempts failed). Same surgical class as Telem + SWD east-edge escapes.
> **Triage outcome:** CRSF = flight-critical → re-pin. Telem = `docs/TELEM_V1_DEFER.md`. SWD = `docs/SWD_TEST_PADS_V1.md`.

---

## 1. Decision

**Move CRSF from USART6 (PC6 TX / PC7 RX, pads 63/64 east edge) → UART4 (PA0 TX / PA1 RX, pads 22/23 west edge), AF8.**

| Signal | Old pin | Old pad | Old MCU edge | New pin | New pad | New MCU edge | UART | AF |
|---|---|---|---|---|---|---|---|---|
| CRSF_TX | PC6 | 63 (52.67, 35.0) | EAST (saturated) | **PA0** | 22 (37.33, 39.5) | **WEST** (clear) | UART4 | AF8 |
| CRSF_RX | PC7 | 64 (52.67, 34.5) | EAST (saturated) | **PA1** | 23 (37.33, 40.0) | **WEST** (clear) | UART4 | AF8 |

Pad coordinates verified empirically by worker (read from `.kicad_pcb`, cross-checked against `MCU_ST_STM32H7.kicad_sym` STM32H743VITx variant; all anchor pins matched: PE9=pad39=MOT3, PB0=34=MOT1, PA9=68, PC6=63, PA13=72, PA14=76).

## 2. Why UART4 PA0/PA1 (vs alternatives)

| Candidate | MCU edge | Same-UART pair? | Escape clearance | Distance to J10 (54,8) | Verdict |
|---|---|---|---|---|---|
| **PA0/PA1 UART4 AF8** | WEST | YES | clearest (only NRST + SPI1 in west corridor) | ~36mm (W edge → N edge) | **CHOSEN** |
| PE7/PE8 UART7 AF7 | SOUTH (right beside MOT3 pad 39) | YES | clean (south edge has MOT1-6 already escaped cleanly) | ~36mm | Solid alternative |
| North-edge mixed-UART pair | NORTH (closest to J10, ~20mm) | NO — PD5 is the only north-edge UART-TX-capable free pin; PD5=USART2_TX but USART2 is already GPS1 | N/A | shortest but blocked by UART-instance conflict | Rejected |

**Why west edge wins:**
1. West edge has the lightest routing congestion (only NRST + SPI1 in the corridor — verified by worker eyes-on-board).
2. Same-UART pair preserves firmware simplicity (single peripheral, single AF, single ISR).
3. AF8 maps both pins cleanly (no per-pin AF mismatch).
4. The 36mm haul up the west side + across the top to J10 is electrically irrelevant — CRSF is 420 kbaud per CLAUDE.md §3.2 (round-trip << bit period at any practical length).
5. Avoids using south-edge UART7 pins that sit immediately beside the dense MOT3-6 fan-out (cleaner separation of motor switching from RC link).

## 3. Concrete delta

### Firmware — `firmware/hwdef-novapcb/hwdef.dat`

Remove (lines 139-140):
```
PC7 USART6_RX USART6
PC6 USART6_TX USART6
```

Add (location: after the UART8 block, before microSD):
```
# UART4 (CRSF) — re-pinned 2026-05-26 from USART6/PC6-PC7 (east-edge
# saturated, task #56 empirically unroutable across 4 distinct attempts).
# PA0/PA1 are WEST-edge MCU pads (cleanest escape; verified PR audit).
# AF8 maps both pins. CRSF is 420 kbaud so the ~36mm route is benign.
# UART4 was previously REMOVED 2026-05-24 (no board wiring after MOT7/8
# took PB8/PB9); re-introduced now on different pins for CRSF.
PA0 UART4_TX UART4
PA1 UART4_RX UART4
```

Update `SERIAL_ORDER` line 113 — **replace `USART6` with `UART4`**:
```
SERIAL_ORDER OTG1 USART1 USART2 USART3 UART8 UART4 OTG2
```

Update the USART6 commentary block (lines 134-138) to reflect that USART6 is now FREE again:
```
# USART6 — FREE as of 2026-05-26 (CRSF moved to UART4/PA0-PA1, see
# docs/CRSF_REPIN_PROPOSAL.md). PC6/PC7 reverted to unused GPIOs. The
# bdshot pattern note retained for v2 reference if RC ever returns here.
```

### Schematic — SKiDL crsf_usb_3g.py (or wherever CRSF JST-GH J10 is instantiated)

The J10 connector's net names CRSF_UART_TX / CRSF_UART_RX (or equivalent) need to map to **MCU pins PA0/PA1** instead of PC6/PC7. The connector geometry doesn't change — only the MCU net assignment.

Action: amend the SKiDL sheet to connect J10's UART pins to MCU PA0/PA1 nets. Regenerate netlist.

### Board — `.kicad_pcb`

1. Rip up any committed PC6/PC7 stub traces (the connector-side stubs to TVS D13/D14 at ~Y14.4 per `docs/CRSF_TELEM_SWD_ROUTING_ANALYSIS.md` Table 1).
2. Re-import netlist after SKiDL regenerate (pcbnew "update PCB from schematic" or scripted equivalent).
3. Route the 2 new nets (PA0/PA1 → J10) — west edge up + across top.

### Routing plan (estimate)

- PA0 pad (37.33, 39.5) → escape SW on F.Cu → via to B.Cu → north along W edge X=35 → up to Y=10 → east to J10 area (54, 8). Mostly B.Cu; F.Cu used for short escape.
- PA1 pad (37.33, 40.0) → mirror PA0 route on adjacent layer / lane.
- Single-layer-preference per pair, F↔B weave only if a horizontal wall blocks.
- Cluster walk: F.Cu over In1.Cu GND; B.Cu over In4.Cu GND. Both confirmed continuous post PR #76 stackup-fix.

### Docs to update

- `docs/PHASE_7A_FREEZE_CHECKLIST.md` Schematic+Firmware section — flip "SERIAL_ORDER correct (USART6 CRSF...)" to "UART4 CRSF".
- `docs/INTERFACE_CONTRACT.md` §3.2 — if the doc cites USART6 specifically, update to UART4. (CRSF wire-level spec unchanged: 420 kbaud, AF8.)
- `docs/MCU_PIN_MAP_AUDIT.md` — append the re-pin entry; PC6/PC7 now free, PA0/PA1 consumed by UART4.
- `docs/CRSF_TELEM_SWD_ROUTING_ANALYSIS.md` — append §6: "CRSF resolved via re-pin to UART4 PA0/PA1; Telem + SWD deferred per separate docs."

## 4. Verification gates (per Rule 9 / Rule 17)

- [ ] `waf configure --board novapcb-v1 && waf copter` succeeds (no PB12/PA0 redefine; UART4 builds cleanly). Same gate that caught dead OSD remnants in PR #119.
- [ ] DRC ≤ baseline + 3 (per master process rule).
- [ ] Per-net cluster walk on PA0 and PA1 — F.Cu over In1.Cu GND continuous, B.Cu over In4.Cu GND continuous.
- [ ] Net inspection: PC6/PC7 are now unconnected GPIO (no dangling traces).
- [ ] Unconnected count drops by 2 (2 escapes resolved).
- [ ] No new violations on USB diff pair (PR #75) — west-edge route must not encroach on USB area.
- [ ] No new violations on SPI1 — PA0/PA1 are west-of-SPI1 (SPI1 uses PA5/PA6/PA7 south-east-corner per hwdef:31-37), should be naturally separate.

## 5. PR plan

**Single PR**, branch `fw/crsf-uart4-repin`:

1. SKiDL amend → regenerate netlist
2. hwdef.dat edit (3 changes: remove PC6/PC7, add PA0/PA1, update SERIAL_ORDER)
3. ArduPilot build verify locally (gate)
4. .kicad_pcb update-from-schematic
5. Rip PC6/PC7 stubs (if any) + route PA0/PA1
6. DRC + cluster walk + verify gates §4 above
7. PR doc per 4-section template (Symptom / Fix / Root cause / Prevention)

**Sai-decision check:** CRSF re-pin is a wire-level swap of MCU pins inside the same flight function — NOT a scope change. CRSF requirements (420 kbaud, CRSF dialect, FS_THR_* failsafe semantics) all unchanged. Per `feedback-master-drives-decisions`, this is master-driveable + worker-executable. No Sai gate needed for the re-pin itself; the freeze trigger remains Sai's call.

## 6. Worker offer

Worker offered a "read-only escape-path clearance survey" on the PA0/PA1 west-edge route before final commit. Master accepts — surveying west-edge clearance (NRST + SPI1 + any other obstacles between PA0/PA1 pads and J10) is the right Rule 9 verify-before-execute step, parallel to the GPS1_TX (PR #101) and BUZZER (PR #102) repin patterns. The survey result either confirms PA0/PA1 as routable or surfaces a fallback to PE7/PE8 UART7 south-edge.

---

**Next step:** worker runs the read-only west-edge clearance survey, then executes the single-PR plan above.
