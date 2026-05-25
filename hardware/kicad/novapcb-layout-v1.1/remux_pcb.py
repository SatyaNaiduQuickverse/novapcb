#!/usr/bin/env python3
"""PCB-level pin re-mux on U1 — FEASIBLE 3-swap version (master 2026-05-22).

After AF verification revealed 10 of 16 original swaps were AF-invalid
on STM32H743 LQFP-100, master directed: keep only the AF-feasible
swaps. SPI3/I2C1 stay on N (no S-side AF). 8-MOT-on-N is impossible
(only ~7 N-side timer pins, with conflicts). MOTs stay where they are.

The feasible re-mux is just 3 pin swaps:
1. SPI1_MOSI: pin 88 (PD7) → pin 31 (PA7) — PA7 = SPI1_MOSI AF5 ✓
2. HEATER_PWM: pin 31 (PA7) → pin 77 (PA15) — PA15 = TIM2_CH1 AF1 ✓
3. BUZZER: pin 77 (PA15) → pin 88 (PD7) — PD7 = digital GPIO ✓

Three-way swap: SPI1_MOSI ← old HEATER_PWM slot; HEATER_PWM ← old
BUZZER slot; BUZZER ← old SPI1_MOSI slot.
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "novapcb-layout-v1.1.kicad_pcb")

# Three-way swap implemented as 2 swaps:
# First swap pin 31 ↔ pin 88: SPI1_MOSI ↔ HEATER_PWM
# Then swap pin 77 ↔ pin 88: BUZZER ↔ (now-HEATER_PWM)
# Final state: pin 31 = SPI1_MOSI, pin 77 = HEATER_PWM, pin 88 = BUZZER
SWAPS = [
    (31, 88, "SPI1_MOSI↔HEATER_PWM"),
    (77, 88, "BUZZER↔HEATER_PWM"),
]


def main():
    brd = pcbnew.LoadBoard(PCB)
    u1 = None
    for fp in brd.GetFootprints():
        if fp.GetReference() == "U1": u1 = fp; break
    if not u1:
        print("U1 not found"); return

    pin_pad = {}
    for p in u1.Pads():
        pn = p.GetNumber()
        if pn.isdigit():
            pin_pad[int(pn)] = p

    for pin_a, pin_b, label in SWAPS:
        pa = pin_pad.get(pin_a)
        pb = pin_pad.get(pin_b)
        if not pa or not pb:
            print(f"  {label}: pin {pin_a} or {pin_b} not found"); continue
        net_a_before = pa.GetNetname()
        net_b_before = pb.GetNetname()
        net_obj_a = pa.GetNet()
        net_obj_b = pb.GetNet()
        pa.SetNet(net_obj_b)
        pb.SetNet(net_obj_a)
        print(f"  pin {pin_a} ({net_a_before}) ↔ pin {pin_b} ({net_b_before})  [{label}]")

    pcbnew.SaveBoard(PCB, brd)
    print("\nFinal state:")
    for pn in [31, 77, 88]:
        if pn in pin_pad:
            print(f"  pin {pn}: {pin_pad[pn].GetNetname()}")
    print("[saved]")


if __name__ == "__main__":
    main()
