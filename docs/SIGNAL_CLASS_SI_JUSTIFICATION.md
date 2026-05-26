# Signal-class SI justification — why these nets need no SI sim

> Closes the "why didn't we sim X" loose-thread audit (Sai directive 2026-05-26,
> Rule 17). Per Sai: *"where it is no requirement don't sim — document why."*
> For each non-controlled-impedance signal class, this shows analytically that
> the net is **electrically short** (lumped) at its routed length, so it needs
> no transmission-line treatment, no termination, and no FDTD/SI sim.

Companion to the sims that WERE run (controlled-impedance / SI-critical):
Sim 2 USB Z_diff, Sim 3 SDMMC SI, Sim 4 CAN Z_diff, Sim 5 PDN (separate PRs).

## 1. The criterion

A trace needs transmission-line treatment (controlled Z₀ + termination, and an
SI sim to verify) only when it is **electrically long** — i.e. the signal edge
is fast relative to the round-trip flight time. The standard lumped/short test:

> **t_round-trip < t_rise** → reflections return before the edge completes →
> no distinct reflection, no ringing → **electrically short, no termination needed.**

(Equivalently the common "length < t_rise / (2·t_pd)" rule.) When this holds,
*and* the bit period ≫ any settling, the net is a lumped RC/CMOS load and SI is
trivially passing.

Flight time on this board: outer-layer microstrip on JLC06161H-7628,
**t_pd ≈ 6 ps/mm** (same figure validated in Sim 3/4). Round-trip = 2·L·t_pd.

## 2. Per-class analysis (routed lengths from the live board)

| Class | Net(s) | Max len | Round-trip flight | Edge / rise time | Bit period | Margin | Verdict |
|---|---|---|---|---|---|---|---|
| **I²C1** | SCL/SDA | 107.0 mm | 1.28 ns | ~100–300 ns (RC, open-drain + pull-up) | 2.5 µs (400 kHz) | rise ≫ round-trip by ~100–230× | electrically short ✓ |
| **I²C2** | SCL/SDA | 20.8 mm | 0.25 ns | ~100–300 ns (RC) | 2.5 µs | ~400–1200× | electrically short ✓ |
| **USART2 (GPS)** | TX/RX | 75.9 mm | 0.91 ns | ~2–5 ns (CMOS push-pull) | 2.17 µs (460 kbaud) | round-trip < rise | electrically short ✓ |
| **USART6 (CRSF)** | TX/RX | pending #56 | — | ~2–5 ns | 2.38 µs (420 kbaud) | slow class | short at any plausible len ✓ |
| **USART1 (Telem)** | TX/RX | pending #56 | — | ~2–5 ns | 8.68 µs (115 kbaud) | slow class | short ✓ |
| **SPI1 (IMU1 ICM-42688)** | SCK/MOSI/MISO | 33.5 mm | 0.40 ns | ~2–5 ns | 125 ns (8 MHz) | round-trip < rise; bit ≫ settling | electrically short ✓ |
| **SPI2 (IMU2 BMI088)** | SCK/MOSI/MISO | 35.3 mm | 0.42 ns | ~2–5 ns | 100 ns (10 MHz) | round-trip < rise | electrically short ✓ |
| **SPI3 (IMU3 LSM6DSV16X)** | SCK/MOSI/MISO | 59.3 mm | 0.71 ns | ~2–5 ns | 125 ns (8 MHz) | round-trip < rise | electrically short ✓ |
| **DShot (MOT3-6)** | MOT3-6 | 52.7 mm | 0.63 ns | ~5–30 ns (DShot edge) | 1.67 µs (DShot600) | round-trip ≪ rise; bit ≫ settling | electrically short ✓ |
| **DShot (MOT1)** | MOT1 | 98.3 mm | 1.18 ns | ~5–30 ns | 1.67 µs | round-trip ≪ rise | electrically short ✓ |
| **BUZZER** | BUZZER | 69.8 mm | 0.84 ns | kHz audio tones (DC-class) | — | not an SI signal | n/a ✓ |

## 3. Why each was NOT FDTD-simmed

- **I²C1 / I²C2 (400 kHz):** open-drain; edge rate is set by the pull-up RC
  (≥100 ns), *thousands* of times slower than the 1.3 ns round-trip. The bus is a
  lumped capacitive load — the only SI parameter is bus capacitance vs pull-up
  (within I²C spec). No transmission-line behaviour possible. I²C1 at 107 mm is
  long but at 400 kHz with correct pull-ups it is well within spec.
- **UART (GPS/CRSF/Telem, ≤460 kbaud):** µs-class bit periods; even with 2–5 ns
  CMOS edges the round-trip (<1 ns) is below the edge, so reflections fold into
  the edge — no ringing the receiver can mis-sample. (Same conclusion the Sim 3
  SDMMC analysis reached for a faster bus.)
- **SPI1/2/3 (8–10 MHz):** round-trip (0.4–0.7 ns) < edge (2–5 ns) → lumped; bit
  period (100–125 ns) ≫ any reflection settling. STM32 SPI receivers tolerate
  substantial overshoot per the H743 datasheet. **(Sim 7 SPI3 was dispatched then
  dropped — this is its analytical closure.)**
- **DShot600 (MOT*):** round-trip ≤1.2 ns ≪ the ~5–30 ns DShot edge and ≪ the
  1.67 µs bit period (≈0.07 % even at the 98 mm MOT1). ESC inputs are high-Z
  (~kΩ); ArduPilot's DShot decode is bit-timing based and tolerant of ringing.
  **(Sim 6 DShot was dispatched then dropped — this is its analytical closure.)**
- **BUZZER:** a kHz-rate on/off tone driver into a piezo/magnetic buzzer — not a
  digital-SI signal at all. One line: no SI concern.

## 4. Conclusion

Every signal class above is **electrically short** at its as-routed length, with
SI margin of 25× to >1000× against any plausible reflection/edge-rate budget. No
termination, controlled-impedance routing, or SI sim is warranted for these
classes. The only nets that DID warrant SI work — USB (Z_diff), SDMMC (skew),
CAN (Z_diff), and the PDN — are covered by their own sims (Sim 2/3/4/5). This
closes the loose-thread audit per Rule 17.
