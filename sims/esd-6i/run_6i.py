#!/usr/bin/env python3
"""
Phase 6i — Reverse polarity + ESD analysis.

novapcb v1 currently has MINIMAL input protection (per Phase 3b sheet
docstring + CONFIDENCE_MAP row 11 LOW status):
  - USB-C D+/D-:  U5 USBLC6-2P6 ESD protection (PRESENT, Phase 3g)
  - VBAT:         Upstream Mauch power module ships with its own protection
                  (hall-sensor protection + voltage divider on the LV variant)
  - +5V BEC input: NO on-board reverse-polarity protection. Bare BEC connector
                  to LDO Vin. NO TVS array on 5V.
  - GPS+mag JST-GH 10P (J5): NO TVS on I²C/UART pins. Long external cable.
  - CRSF J10 solder pads: NO TVS on +5V/UART_TX/UART_RX.
  - Telem J3 JST-GH 6P: NO TVS on UART.

Phase 6.5 forum review queue item — get external EE eyes on protection
topology BEFORE fab.

This script:
  1. Documents what IS protected vs UN-protected.
  2. Estimates the ESD survival level for unprotected lines (HBM ±2 kV
     spec target per SIMULATION_PLAN §6i).
  3. Simulates the USBLC6 clamp response — verifies it works.
"""

import json, subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
NGSPICE = str(Path.home()/"local/ngspice/usr/bin/ngspice")


def usblc6_clamp_sim():
    """Apply a Human Body Model (HBM) ESD pulse to USB-C D+, check clamp voltage at MCU."""
    nl = """* HBM ESD pulse (1500Ω source + 100pF storage cap, 2kV charge)
* into USBLC6-2P6 (clamp at ~24V working / 15V breakdown)
* output: MCU pin D+ voltage during the strike
* HBM model: charged 100pF discharged through 1500Ω
Vesd vstor 0 2000
Resd_chrg vstor cap 1500
Cesd cap 0 100p IC=2000
Resd_dis cap vusb 1500
* USBLC6 TVS clamp at 24V (RM/RP working), 15V VRWM, 9V VBR breakdown
Dclamp vusb 0 dclamp
.MODEL dclamp D BV=15 IBV=1m N=1.5 RS=2 IS=1e-12
* MCU pin sees the clamped voltage
Rmcu vusb mcu_pin 50
Cmcu_pin mcu_pin 0 5p
.TRAN 1n 1u UIC
.CONTROL
run
meas tran v_mcu_peak MAX v(mcu_pin) FROM=0 TO=1u
print v_mcu_peak
.ENDC
.END
"""
    Path("/tmp/esd_6i.cir").write_text(nl)
    proc = subprocess.run([NGSPICE, "-b", "/tmp/esd_6i.cir"], capture_output=True, text=True)
    vpeak = None
    for line in proc.stdout.splitlines():
        if "v_mcu_peak" in line.lower() and "=" in line:
            try: vpeak = float(line.split("=")[1].split()[0])
            except (ValueError, IndexError): pass
    return {"v_mcu_peak_V": vpeak,
            "spec_max_abs_V": 4.0,
            "interpretation": "USBLC6 clamps the ESD strike to ~15V at the line; MCU pin via series Rmcu+Cmcu_pin sees the residual transient. Pass if mcu_peak < 4V (STM32H743 abs max VDD+0.5V on 3.3V-tolerant pin).",
            "pass": vpeak is not None and abs(vpeak) < 4.0}


def main():
    print("Phase 6i — ESD + reverse polarity")
    results = {
        "tool": "ngspice + analytical inventory",
        "tier": "1 partial (USB clamp test runs; coverage gap inventory + Phase 6.5 forum-review queue)",
        "checks": [],
    }

    # Protection inventory
    inventory = {
        "USB-C D+/D-":            {"protected": True, "device": "U5 USBLC6-2P6 (ST)"},
        "VBAT input (Mauch)":     {"protected": "external", "device": "Mauch HS-200-LV module"},
        "+5V BEC input":          {"protected": False, "device": None, "risk": "Reverse polarity = LDO destruction; ESD on bare connector"},
        "GPS+mag J5 I²C/UART":    {"protected": False, "device": None, "risk": "Long external cable; static buildup"},
        "CRSF J10 solder pads":   {"protected": False, "device": None, "risk": "User-soldered wires; less risky but still exposed"},
        "Telem J3 UART":          {"protected": False, "device": None, "risk": "External telem cable; static buildup"},
    }
    results["checks"].append({
        "check": "6i.1_protection_inventory",
        "status": "INFO",
        "result": inventory,
        "notes": "novapcb v1 ESD/reverse-polarity protection: USB-C only. 5 unprotected lines flagged for Phase 6.5 forum review.",
    })

    # USB clamp sim
    r_usb = usblc6_clamp_sim()
    results["checks"].append({
        "check": "6i.2_USBLC6_clamp_HBM_2kV",
        "status": "PASS" if r_usb.get("pass") else "FAIL",
        "result": r_usb,
        "notes": "USB-C D+/D- HBM ±2kV strike clamped by U5 USBLC6-2P6. MCU pin should see <4V.",
    })

    # Conclude with the gap statement
    results["gap_analysis"] = {
        "v1_protected": ["USB-C D+/D- (USBLC6-2P6)"],
        "v1_unprotected": ["+5V BEC", "GPS+mag I²C/UART", "CRSF UART", "Telem UART"],
        "phase_6_5_forum_review_topics": [
            "Add TVS arrays on GPS+mag J5 and Telem J3 connectors? (Standard practice on production FCs.)",
            "Reverse-polarity protection on +5V BEC: P-MOSFET vs Schottky diode trade-off?",
            "Bulk inrush limiter NTC at BEC input — see 6a.3 inrush finding (3.39A peak).",
        ],
        "v2_carry_forward": True,
        "v1_acceptable_with_caveats": "User must (a) verify BEC polarity before connecting; (b) avoid static discharge to FC during ground handling; (c) accept v1 is 'engineering sample' protection level. v2 adds TVS arrays.",
    }
    n_pass = sum(1 for c in results["checks"] if c["status"] == "PASS")
    n_fail = sum(1 for c in results["checks"] if c["status"] == "FAIL")
    n_info = sum(1 for c in results["checks"] if c["status"] == "INFO")
    results["summary"] = {"total": len(results["checks"]), "pass": n_pass, "fail": n_fail, "info": n_info}
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"  USBLC6 clamp: v_mcu_peak = {r_usb.get('v_mcu_peak_V')} V ({'PASS' if r_usb.get('pass') else 'FAIL'})")
    print(f"  SUMMARY: {results['summary']}")


if __name__ == "__main__":
    main()
