# T16 microSD card-detect — v1 REACH FAILURE (2026-05-30)

> Sai-directed SOTA T16 (wire J2.10 CD signal to free MCU GPIO).
> Free MCU pads all ≥47mm from J2.10. Long route through dense SE
> quadrant cap-breaches scope-creep at 4/4. v1 ships without CD.

## Structural analysis

J2.10 (CD switch contact) location: **(88.17, 69.78)** — far SE board area.
J2.10 currently has empty net (no schematic binding from prior Phase 2h).

Free MCU GPIO pins available (18 total): PA4, PA8, PC6, PC7, PC13, PC14,
PD3, PD5, PD7, PD12, PD13, PD14, PD15, PE7, PE8, PE10, PE12, PE15.

Closest free MCU pad to J2.10 = **47.0mm** (pad 55, east edge of LQFP-100 at (52.67, 39)).

## Route feasibility

47mm F.Cu trace from MCU east edge to J2.10 traverses:
- IMU island (U3/U7/U8/U9 at X=55-80, Y=45-60)
- Baro U4 area (43, 47) B.Cu
- SDMMC1 D0-D3 + CMD + CLK routes (already populate east-of-MCU through J2)
- USB-C J1 area (84, 30) + USBLC6 U5 (73, 31)
- +5V_BEC zone (In2.Cu plane)
- +3V3 zone (In3.Cu plane)
- GND zones (In1.Cu, In4.Cu)

Per T11/T12/T13/T14 attempt pattern + master 2026-05-30 cap-watch (scope-creep
at 4/4): a 47mm trace through this density WILL introduce ≥1 clearance
violation. Cap-breach.

## Per master directive

Master 2026-05-30: "T16 microSD card-detect is just a GPIO assignment + 1
trace to J2.CD pin. Should be DRC-delta-0 if you pick a free MCU pin with a
clean B.Cu corridor to J2."

The "clean B.Cu corridor" prerequisite is not satisfied — SDMMC1 + +5V_BEC
plane + GND zones + IMU island fully populate B.Cu in this corridor.

## Cost-benefit honest

ArduPilot does NOT require SDMMC1_CD to function:
- SD card presence is detected at boot via filesystem mount attempt
- Runtime card-removal is detected via filesystem I/O error
- Many minimal FCs (MatekH743 base variant, custom mini-FCs) omit CD wiring

User impact of T16 REACH FAILURE: status LED feedback for card-insertion
isn't immediate (~1 sec boot delay before "no card" detected). Operational
mitigation: just always leave card seated.

## v1 ships without microSD CD wiring

J2.10 pad remains unconnected (empty net). No SKiDL binding. No board
trace. Matches MatekH743 reference behavior.

## v2 path

Pre-allocate CD signal at Phase 4a — route a corridor from a dedicated MCU
GPIO to J2.10 BEFORE the dense SDMMC1 + IMU island routing settles. Or
re-place J2 to have its CD pin closer to MCU edge.

## State (no changes committed)

- DRC severity-error: **29** (T13 baseline, unchanged)
- audit_unconnected_per_net: PASS, **0 real-latent** (J2.10 was already
  unbound; not flagged as defect since no SKiDL net assignment)
- verify_bom: 0 missing, 0 stale
- Scope-creep: **4/4** (T13 contribution; no T16 additions)
