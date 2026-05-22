# USB diff pair impedance recompute — 3-signal stackup (master 2026-05-22)

## NEW stackup (after L4 rebalance)

| Layer | Material | Thickness | Role |
|---|---|---|---|
| L1 (F.Cu) | Cu 1oz | 0.035 mm | **Signal** |
| Prepreg 7628 | FR-4 (εr=4.3) | **0.21 mm** | L1↔L2 dielectric |
| L2 (In1) | Cu 0.5oz | 0.0152 mm | **GND plane** |
| Core | FR-4 | 0.55 mm | L2↔L3 dielectric |
| L3 (In2) | Cu 0.5oz | 0.0152 mm | **+3V3 plane** |
| Prepreg 2116 | FR-4 | **0.1088 mm** | L3↔L4 dielectric |
| L4 (In3) | Cu 0.5oz | 0.0152 mm | **Signal** (was +5V plane) |
| Core | FR-4 | 0.55 mm | L4↔L5 dielectric |
| L5 (In4) | Cu 0.5oz | 0.0152 mm | **GND plane** |
| Prepreg 7628 | FR-4 | **0.21 mm** | L5↔L6 dielectric |
| L6 (B.Cu) | Cu 1oz | 0.035 mm | **Signal** |

## USB 2.0 diff pair (90Ω ±15%) on each signal layer

### L1 (F.Cu) — UNCHANGED
- Reference: L2 GND at h=0.21 mm
- Geometry: **W=0.30 mm / S=0.10 mm** (per existing net class)
- **Z_diff = 94.4 Ω** ✓ (within USB ±15%, 9.1 Ω margin)

### L6 (B.Cu) — UNCHANGED (mirror of L1)
- Reference: L5 GND at h=0.21 mm
- Geometry: same as L1
- **Z_diff = 94.4 Ω** ✓

### L4 (In3) — NEW signal layer, asymmetric stripline
- References: L3 +3V3 above at h=0.1088 mm, L5 GND below at h=0.55 mm
- Effective reference: L3 +3V3 (much closer)
- +3V3 plane is a valid AC reference (decoupled to GND)

Compute via microstrip-equivalent formula (dominant near-reference at
h=0.1088 mm, εr=4.3, t=0.0152 mm 0.5oz Cu):

For target Z_diff ≈ 90Ω with S=0.10mm:
- Z_se needed ≈ 55Ω (gives ~89Ω diff at S/h≈1.0)
- W solves: 55 = 87/√(εr+1.41) · ln(5.98h/(0.8W+t))
  = 36.4 · ln(5.98·0.1088/(0.8W+0.0152))
  = 36.4 · ln(0.6506/(0.8W+0.0152))
  → 1.510 = ln(0.6506/(0.8W+0.0152))
  → 4.527 = 0.6506/(0.8W+0.0152)
  → 0.8W+0.0152 = 0.144
  → W = 0.161 mm

**L4 USB pair: W = 0.16 mm / S = 0.10 mm → Z_diff ≈ 87 Ω** ✓ (within USB ±15%, 10.5 Ω margin)

## Decision — route USB pair only on L1 or L6

USB diff pair routing on L4 is feasible but requires a different
geometry (W=0.16 vs L1/L6's W=0.30). To avoid impedance discontinuities
at the L1↔L4 via transitions, **constrain USB diff pair to L1 or L6
exclusively** (no via transitions through L4 mid-pair).

L4 is available for ALL OTHER non-controlled-impedance signals (~150+
nets) — this is the +50% routing room master expected.

## Other controlled-impedance nets

Currently only USB 2.0 has explicit impedance control. CAN bus and
SDMMC1 are run at trace widths set by their net class but without
strict impedance targets at the rates used (1 Mbps CAN, ~50 MHz
SDMMC). They can route on any of the 3 signal layers.

## Net class summary (no change needed)

| Net class | Track width | Clearance | Via |
|---|---|---|---|
| Default | 0.20 mm | 0.20 mm | 0.60 mm / 0.30 mm drill |
| USB (diff pair) | 0.30 mm | 0.20 mm | n/a (L1/L6 only) |

## Sources

- USB-IF specification §7.1.6 (Z_diff = 90 Ω ± 15%)
- IPC-2141: microstrip/stripline impedance formulas
- JLC06161H-7628 stackup table:
  - https://jlcpcb.com/impedance
  - https://jlcpcb.com/help/article/jlcpcb-copper-weight
- docs/CONTROLLED_IMPEDANCE.md §1-2 (existing analysis)
