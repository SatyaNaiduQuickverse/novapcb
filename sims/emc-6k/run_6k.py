#!/usr/bin/env python3
"""
Phase 6k — EMC analytical Fourier estimate of switching harmonics.

OpenEMS deferred (TOOLCHAIN.md §4). Per SIMULATION_PLAN §6k the PRIMARY method
is analytical Fourier decomposition + spot OpenEMS — analytical alone is the
v1 floor.

Sources of switching on novapcb v1:
  - HSE crystal: 8 MHz square (low harmonics — sinusoidal-ish)
  - SPI1 to ICM-42688-P: 16 MHz clock (trapezoidal — rich in odd harmonics)
  - SDMMC1 clock: 12.5 MHz (per Phase 2h STM32_SDC_MAX_CLOCK)
  - DShot600: 600 kHz bit rate (sharp edges — broadband)
  - USB FS: 12 MHz (NRZI encoded)
  - I²C: 400 kHz max — low harmonic content
  - UARTs: 420 kbaud CRSF + 38.4 kbaud GPS — low

Sensitive bands to check against:
  - GPS L1: 1575.42 MHz ± 10 MHz
  - GPS L2: 1227.60 MHz (if using dual-band)
  - ELRS 868/915 MHz region
  - USB 2.0 FS: 12 MHz (self)
  - WiFi/BT 2.4 GHz: not on novapcb but environmental noise budget

Output: spectrum plot + a table of which harmonics fall in sensitive bands +
adjacency to spec emission limits (FCC Part 15 Class B / CE EN55032 Class B).

Pass criterion: All identified harmonics in sensitive bands below the
estimated emission floor (analytical conservatism; precise EMC compliance
needs chamber test post-fab).
"""

import json
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent.resolve()
PLOTS = HERE / "plots"; PLOTS.mkdir(exist_ok=True)


def harmonic_amplitude(f0_Hz, n_harm, signal_type="trapezoidal", t_rise_s=2e-9):
    """Amplitude of the n'th harmonic of a periodic switching signal.
    For trapezoidal (rich-harmonic): A_n ∝ sinc(n*duty) * sinc(n*tau_rise*f0)
    Returns dB relative to fundamental."""
    if n_harm < 1: return 0
    duty = 0.5  # 50% duty cycle
    # Trapezoidal harmonic envelope: drops at -20 dB/dec until f_rise = 1/(π*tau_rise),
    # then -40 dB/dec
    A = 2 / (np.pi * n_harm) * abs(np.sin(np.pi * n_harm * duty))
    f_harm = n_harm * f0_Hz
    f_break = 1 / (np.pi * t_rise_s)
    if f_harm > f_break:
        A *= (f_break / f_harm)
    return 20 * np.log10(max(A, 1e-12))


def sensitive_band_check():
    sources = [
        ("HSE 8MHz crystal", 8e6, 50e-9),       # slow risetime; sinusoidal-ish
        ("SPI1 IMU clock", 16e6, 5e-9),
        ("SDMMC1 clock 12.5MHz", 12.5e6, 5e-9),
        ("DShot600 600kHz", 600e3, 50e-9),       # 50ns rise per ESC spec
        ("USB FS 12MHz NRZI", 12e6, 5e-9),
        ("I²C 400kHz max", 400e3, 100e-9),
        ("CRSF UART 420kbaud", 420e3, 100e-9),
    ]
    bands = [
        ("GPS L1", 1565e6, 1585e6),
        ("GPS L2", 1217e6, 1237e6),
        ("ELRS 868MHz EU", 863e6, 873e6),
        ("ELRS 915MHz US", 910e6, 920e6),
        ("USB FS self", 11e6, 13e6),
    ]

    findings = []
    for src_name, f0, t_rise in sources:
        for band_name, f_lo, f_hi in bands:
            for n in range(1, 500):
                f_harm = n * f0
                if f_lo <= f_harm <= f_hi:
                    A_dB = harmonic_amplitude(f0, n, t_rise_s=t_rise)
                    findings.append({
                        "source": src_name,
                        "harm_n": n,
                        "f_harm_MHz": round(f_harm / 1e6, 3),
                        "band": band_name,
                        "amplitude_dB_rel_fundamental": round(A_dB, 1),
                    })
    return findings


def plot_spectrum(name, f0, t_rise, n_max=200):
    """Plot the spectrum of a single source up to n_max harmonics."""
    ns = np.arange(1, n_max + 1)
    f_harms = ns * f0
    amps = np.array([harmonic_amplitude(f0, n, t_rise_s=t_rise) for n in ns])
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.stem(f_harms / 1e6, amps, basefmt=" ", linefmt="b-", markerfmt="b.")
    # Sensitive bands as shaded regions
    for band_name, f_lo, f_hi in [
        ("GPS L1", 1565, 1585),
        ("ELRS 868EU", 863, 873),
        ("ELRS 915US", 910, 920),
    ]:
        ax.axvspan(f_lo, f_hi, alpha=0.15, color="r", label=band_name)
    ax.set_xlabel("Frequency (MHz)"); ax.set_ylabel("Amplitude (dB rel fundamental)")
    ax.set_title(f"6k — {name} harmonic spectrum")
    ax.set_ylim(-100, 5); ax.set_xlim(0, max(f_harms) / 1e6)
    ax.legend(loc="lower right", fontsize=8); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    safename = name.replace(" ", "_").replace("/", "_")
    fig.savefig(PLOTS / f"6k_spectrum_{safename}.png", dpi=120)
    plt.close(fig)


def main():
    print("Phase 6k — EMC analytical Fourier")
    results = {"tool": "analytical Fourier (numpy/matplotlib) — OpenEMS deferred per TOOLCHAIN.md §4",
               "checks": []}

    findings = sensitive_band_check()
    # Sort by amplitude (worst first)
    findings.sort(key=lambda x: -x["amplitude_dB_rel_fundamental"])

    # Generate spectrum plots for the main sources
    for name, f0, t_rise in [
        ("HSE 8MHz", 8e6, 50e-9),
        ("SPI1 16MHz", 16e6, 5e-9),
        ("SDMMC 12.5MHz", 12.5e6, 5e-9),
        ("USB FS 12MHz", 12e6, 5e-9),
    ]:
        plot_spectrum(name, f0, t_rise)

    # Findings interpretation
    if findings:
        worst = findings[0]
        # Conservative interpretation: harmonics below -40 dB rel fundamental are
        # generally below the emission floor for a 4-layer mini-FC at <1 m. Above
        # -40 dB warrants chamber-test attention.
        critical = [f for f in findings if f["amplitude_dB_rel_fundamental"] > -40]
    else:
        worst = None
        critical = []

    results["checks"].append({
        "check": "6k.1_harmonic_band_intersections",
        "status": "INFO",
        "result": {
            "n_intersections_found": len(findings),
            "worst_case": worst,
            "critical_count": len(critical),
            "critical_findings": critical,
        },
        "notes": "Analytical Fourier — harmonics > -40 dB in sensitive bands are chamber-test targets. Pre-fab analysis only; real EMC compliance via Phase 9.5 chamber.",
    })

    results["summary"] = {"total": 1, "info": 1}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"  Found {len(findings)} harmonic-band intersections; {len(critical)} above -40 dB threshold")
    print(f"  Spectrum plots in {PLOTS}/")
    print(f"  Results: {HERE / 'results.json'}")


if __name__ == "__main__":
    main()
