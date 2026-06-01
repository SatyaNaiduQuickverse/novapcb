"""Sim 6i Scenario E — ESC switching feedthrough on Mauch ADC sense (analytical)

Scenario: DShot600 ESC switching at 600 kHz causes ripple on Mauch BEC output
via cable inductance + Mauch internal regulation bandwidth. This ripple feeds
through to the FC's +5V_BEC and to the Mauch V/I ADC sense lines.

Gate (per docs/SIM_6I_TRANSIENT_OV_SPEC.md §3.6i.E):
  Mauch V/I ADC sense reads within ±10mV of true value during ESC switching.

Cited values:
  - DShot600 switching frequency: 600 kHz per ESC datasheet typ + DECISIONS §3
  - Mauch ADC anti-alias filter: 1 kΩ + 100 nF RC = 1.59 kHz cutoff
    (per docs/CONFIDENCE_MAP.md row 11 + phase 3h schematic capture)
  - ADC tolerance: ±10 mV per spec
"""
import math

# ---- Inputs (cited) ----
F_DSHOT = 600e3          # Hz — DShot600 switching, DECISIONS §3
V_RIPPLE_PP_INPUT = 0.10 # V — assumed 100 mV pk-pk ripple at Mauch BEC output
                         # (conservative — typical Mauch BEC actual ripple is 20-50 mV;
                         # docs/CONFIDENCE_MAP.md notes "DShot600 600 kHz, ESC PWM 25-50 kHz")

# RC filter (per phase 3h capture in CONFIDENCE_MAP row 11)
R_FILT = 1e3             # Ω
C_FILT = 100e-9          # F
F_CUTOFF = 1 / (2 * math.pi * R_FILT * C_FILT)

# ADC tolerance gate
V_ADC_TOLERANCE = 10e-3  # V — per spec §3.6i.E


def run():
    print("=== Sim 6i.E — ESC switching feedthrough on Mauch ADC (analytical) ===\n")

    print("## Inputs (cited)")
    print(f"  DShot600 switching: {F_DSHOT/1e3:.0f} kHz")
    print(f"  Input ripple at Mauch output (conservative): {V_RIPPLE_PP_INPUT*1e3:.0f} mV pk-pk")
    print(f"  RC filter: R={R_FILT/1e3:.0f} kΩ, C={C_FILT*1e9:.0f} nF")
    print(f"  RC cutoff: f_c = 1/(2π·RC) = {F_CUTOFF:.1f} Hz = {F_CUTOFF/1e3:.2f} kHz")
    print(f"  ADC tolerance gate: ±{V_ADC_TOLERANCE*1e3:.0f} mV")
    print()

    print("## Step 1 — Single-pole RC LPF attenuation at f_DSHOT")
    # Magnitude of single-pole LPF: |H(f)| = 1 / sqrt(1 + (f/f_c)^2)
    # For f >> f_c: |H(f)| ≈ f_c / f
    ratio = F_DSHOT / F_CUTOFF
    H_mag = 1 / math.sqrt(1 + ratio**2)
    H_dB = 20 * math.log10(H_mag)
    print(f"  f_DSHOT / f_c = {ratio:.0f} (deep in attenuation band)")
    print(f"  |H(f_DSHOT)| = 1/√(1+{ratio:.0f}²) = {H_mag:.2e}")
    print(f"  Attenuation = {H_dB:.1f} dB")
    print()

    print("## Step 2 — Ripple at ADC pin")
    v_ripple_adc_pp = V_RIPPLE_PP_INPUT * H_mag
    v_ripple_adc_peak = v_ripple_adc_pp / 2  # half of pk-pk
    print(f"  Output ripple pk-pk: {V_RIPPLE_PP_INPUT*1e3:.0f} mV × {H_mag:.2e} = {v_ripple_adc_pp*1e6:.3f} µV pk-pk")
    print(f"  Output ripple peak: {v_ripple_adc_peak*1e6:.3f} µV (= {v_ripple_adc_peak*1e3:.5f} mV)")
    print()

    print("## Gate check")
    gate_e = v_ripple_adc_peak <= V_ADC_TOLERANCE
    margin = V_ADC_TOLERANCE - v_ripple_adc_peak
    print(f"  Gate 6i.E: ADC ripple ≤ ±{V_ADC_TOLERANCE*1e3:.0f} mV?")
    print(f"    {v_ripple_adc_peak*1e6:.3f} µV ≤ {V_ADC_TOLERANCE*1e3:.0f} mV → {'✅ PASS' if gate_e else '❌ FAIL'}")
    print(f"    Margin: {margin*1e3:.3f} mV (~{margin/V_ADC_TOLERANCE*100:.1f}% of tolerance)")
    print()

    print("## Step 3 — Worst-case 25 kHz ESC PWM (vs DShot600 600 kHz)")
    # Some ESCs run lower PWM rate (25-50 kHz analog PWM mode). Check the worse case.
    f_pwm_low = 25e3
    ratio_low = f_pwm_low / F_CUTOFF
    H_mag_low = 1 / math.sqrt(1 + ratio_low**2)
    v_ripple_adc_pwm = V_RIPPLE_PP_INPUT * H_mag_low / 2
    print(f"  At 25 kHz PWM: f/f_c = {ratio_low:.1f}, |H| = {H_mag_low:.3f}, ripple peak = {v_ripple_adc_pwm*1e3:.2f} mV")
    gate_e_pwm = v_ripple_adc_pwm <= V_ADC_TOLERANCE
    print(f"  Still within ±{V_ADC_TOLERANCE*1e3:.0f} mV gate? → {'✅ PASS' if gate_e_pwm else '❌ FAIL'}")
    print()

    overall = gate_e and gate_e_pwm
    print(f"## Verdict: {'✅ PASS (all ESC modes)' if overall else '❌ FAIL'}\n")
    return overall


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
