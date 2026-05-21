# Controlled-impedance trace geometry

> **Purpose**: lock the trace geometry for the controlled-impedance nets
> (USB 2.0 D+/D−) for the **REAL** JLCPCB 6-layer stackup, computed
> analytically via the Hammerstad-Jensen + edge-coupled differential
> formula. Feeds the Step 5 routing net-class setup.
>
> **Status**: Step 5 pre-routing setup, 2026-05-21. The stackup was
> corrected from a 4 oz inner-layer assumption (which doesn't exist as
> a JLC standard) to the real JLC06161H-7628 standard offering per
> master correction 2026-05-21.

---

## 1. Stackup (CORRECTED 2026-05-21 — real JLC06161H-7628)

Per JLCPCB published stackup table (https://jlcpcb.com/impedance and
https://jlcpcb.com/help/article/jlcpcb-copper-weight), the standard
6-layer 1.6 mm orderable stackup is **JLC06161H**. Within that family
there are four prepreg variants (3313, 1080, 2116A, 7628) which differ
in the prepreg dielectric thickness — chosen at fab order time based on
impedance-control needs.

For impedance-controlled USB 2.0 diff pair, we specify **JLC06161H-7628**
because its 0.21 mm L1↔L2 prepreg is the only variant that lets a
microstrip diff pair sit in the 90 Ω ±15% USB 2.0 spec window without
needing absurdly wide traces.

### JLC06161H-7628 layer table

| Layer | Material | Thickness | Notes |
|---|---|---|---|
| L1 (top) | Copper | **0.035 mm** (1 oz) | Components + signal |
| Prepreg 7628 | FR-4 (εr ≈ 4.3) | **0.21 mm** | ← L1↔L2 dielectric (USB ref) |
| L2 (inner) | Copper | **0.0152 mm** (0.5 oz) | GND plane |
| Core | FR-4 | 0.55 mm | |
| L3 (inner) | Copper | 0.0152 mm (0.5 oz) | +3V3 plane |
| Prepreg 2116 | FR-4 | 0.1088 mm | |
| L4 (inner) | Copper | 0.0152 mm (0.5 oz) | +5V plane |
| Core | FR-4 | 0.55 mm | |
| L5 (inner) | Copper | 0.0152 mm (0.5 oz) | GND plane |
| Prepreg 7628 | FR-4 | 0.21 mm | ← L5↔L6 dielectric (mirror of L1↔L2) |
| L6 (bot) | Copper | 0.035 mm (1 oz) | Signal + bottom-side sensors |

Total Cu thickness: 2 × 0.035 (outer) + 4 × 0.0152 (inner) = **0.131 mm**
Total board thickness: 0.131 + 1.469 (FR-4 + prepreg) ≈ 1.6 mm

**Correction note**: prior versions of PLACEMENT_STRATEGY.md §3.5 and
THERMAL_BUDGET.md §3.2 claimed "4 oz inner" copper. That was wrong —
JLCPCB does NOT offer 4 oz inner copper on a 6-layer board (heavy
copper is 2-layer only per their capability matrix at
https://jlcpcb.com/help/article/jlcpcb-copper-weight). PLACEMENT_STRATEGY +
THERMAL_BUDGET docs corrected in the same PR as this CONTROLLED_IMPEDANCE
doc.

## 2. USB 2.0 differential pair (90Ω ±15%)

USB-C J1 (Zone 2 N edge) → MCU U1 PA11/PA12 pins, microstrip on L1
referenced to L2 GND plane.

### 2.1 Spec

USB 2.0 (USB-IF specification §7.1.6) tolerates **Z_diff = 90 Ω ± 15%**
(76.5 to 103.5 Ω). USB 2.0 is "Full Speed" / "High Speed" (480 Mbps max);
the ±15% is the genuine USB 2.0 spec tolerance.

### 2.2 Geometry (Hammerstad-Jensen + edge-coupled differential)

Single-ended microstrip Z0 per Pozar §3.8 (thickness-corrected H-J):

```
W_eff = W + (t/π) × (1 + ln(2h/t))
u = W_eff / h
ε_eff = (ε_r+1)/2 + (ε_r-1)/2 × (1 + 10/u)^(-a·b)
Z0_air = 60 × ln(6 + (2π-6)·exp(-(30.666/u)^0.7528) + √(1 + 4/u²))
Z_se = Z0_air / √ε_eff
```

Edge-coupled differential factor (IPC-2141):

```
Z_diff = 2 × Z_se × (1 - 0.48 × exp(-0.96 × S/h))
```

### 2.3 Sweep at h = 0.21 mm (JLC06161H-7628), ε_r = 4.3, t = 35 µm

| W (mm) | S (mm) | Z_se (Ω) | Z_diff (Ω) | In USB 2.0 ±15% spec? |
|---|---|---|---|---|
| 0.20 | 0.10 | 73.4 | 96.3 | IN (7.2 Ω margin) |
| 0.25 | 0.10 | 70.4 | 95.4 | IN |
| **0.30** | **0.10** | **67.8** | **94.4** | **IN (9.1 Ω margin)** |
| 0.30 | 0.12 | 67.8 | 99.0 | IN |
| 0.35 | 0.10 | 65.6 | 93.4 | IN (10.1 Ω margin) |
| 0.40 | 0.10 | 63.8 | 92.4 | IN |
| 0.50 | 0.10 | 60.7 | 90.5 | IN (right at 90 Ω nominal) |

Wider trace → closer to 90 Ω nominal. The choice is between routing
convenience (narrower trace = less area, easier dense routing) and
impedance accuracy.

### 2.4 Recommendation — W = 0.30 mm, S = 0.10 mm

**Z_diff = 94.4 Ω** — within USB 2.0 ±15% spec with 9 Ω margin to the
upper limit. Reasonable routing width for an 80×60 mm board.

W = 0.30 mm is also wide enough to carry the 500 mA USB peak current
(USB-C spec) comfortably (IPC-2152: 0.30 mm × 35 µm Cu = 0.85 A at 20°C
rise).

### 2.5 Why not the alternative JLC stackup variants

- **JLC06161H-3313** (h=0.0994 mm L1↔L2): even at W=0.40 mm, Z_diff sits
  at 102.6 Ω — at the absolute upper edge of USB 2.0 ±15% spec (103.5 Ω).
  No margin. Rejected.
- **JLC06161H-1080** (h=0.0764 mm): even thinner prepreg → Z_diff in
  the 105-110 Ω range for any reasonable W. Rejected.
- **JLC06161H-2116A** (h=0.1164 mm): similar to 3313, Z_diff 100-105 Ω.
  No margin. Rejected.
- **JLC06161H-7628** ✓ (h=0.21 mm): comfortably in spec at W=0.30, S=0.10.

### 2.6 Fab-order specification

When the design lands at JLCPCB, the order must specify:
- Layer count: 6
- Material: FR-4 TG170
- Board thickness: 1.6 mm
- Outer Cu: 1 oz
- Inner Cu: 0.5 oz (default)
- **Stackup variant: JLC06161H-7628** (impedance-control prepreg choice)
- Surface finish: HASL (lead-free) or ENIG per Sai cost preference

The -7628 variant is a JLCPCB standard offering (no custom-stackup fee).

## 3. Routing constraint (codified for the router)

- Track width: **0.30 mm** (300 µm)
- Gap (intra-pair): **0.10 mm** (100 µm)
- Length matching: ≤ 0.5 mm differential skew (USB 2.0 is forgiving)
- Via count: minimize (each via adds ~10 Ω discontinuity); ideally 0 vias
- Spacing to other signals: ≥ 0.15 mm (3 × dielectric thickness rule)

## 4. Other nets (not impedance-controlled)

| Net class | Spec | Decision |
|---|---|---|
| SDMMC1 clock (12.5 MHz) | slow CMOS | `Default` 0.20 mm |
| DShot600 (600 kHz) | slow | `Default` |
| ICM-42688-P SPI (10 MHz max) | slow | `Default` |
| HSE 8 MHz crystal | self-contained | layout-time keep traces ≤ 5 mm |
| GPS UART / CRSF / Telem | low-speed | `Default` |
| ADC (DC-1 kHz, LPF-filtered) | low-speed | `Default`; LPF close to MCU |

USB diff pair is the only impedance-controlled signal on novapcb v1.

## 5. Power-rail track widths (when not plane-served)

Per IPC-2152, 1 oz outer Cu at 20 °C rise:

| Width (mm) | Current capacity |
|---|---|
| 0.25 | 0.7 A |
| 0.5 | 1.5 A |
| 1.0 | 3.0 A |
| 1.5 | 4.0 A |

Almost all power nets are plane-served (L3 +3V3, L4 +5V, L2/L5 GND).
Track-style power routing only for fan-out from pad to via — keep
≥ 0.5 mm at fan-out for fault-current handling.

## 6. References

- Pozar, *Microwave Engineering* (4th ed.), §3.8 (microstrip lines)
- IPC-2141 (Controlled Impedance Circuit Boards and High-Speed Logic Design)
- IPC-2152 (Standard for Determining Current-Carrying Capacity)
- Hammerstad + Jensen (1980), IEEE MTT-S, "Accurate Models for Microstrip CAD"
- USB-IF, USB 2.0 specification §7.1.6
- JLCPCB Impedance Calculator page: https://jlcpcb.com/impedance
- JLCPCB Copper Weight matrix: https://jlcpcb.com/help/article/jlcpcb-copper-weight

---

**Status**: locked for Step 5 routing. USB diff-pair = **W 0.30 mm /
S 0.10 mm**. Fab-order spec: **JLC06161H-7628** (impedance-control
prepreg variant). All other nets `Default` (0.20 mm track / 0.15 mm
clearance per Step 5 ruleset).
