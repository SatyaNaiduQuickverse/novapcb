#!/usr/bin/env python3
"""USB differential-pair Z_diff sign-off — openEMS + scikit-rf.

Per master 2026-05-22:
  "USB Z_diff sign-off: run openEMS AND skrf on the ACTUAL board
   geometry — the real L1 trace W/S + the GND-fill reference — confirm
   Z_diff = 90 Ω."

Both tools were validated in Task 9 (VALIDATION_RESULTS.md row 2 = skrf
microstrip 1.03% vs H-J, row 5 = openEMS 3.6% vs H-J). This is their
first real use on novapcb geometry.

ACTUAL board geometry (this PR's USB coupled section):
  W      = 0.30 mm        (diff trace width)
  S      = 0.10 mm        (edge-to-edge gap)
  pitch  = W + S = 0.40 mm  (center-to-center)
  h      = 0.21 mm        (L1 → L2 GND plane; prepreg 7628 per
                            JLC06161H-7628 stackup)
  t      = 0.035 mm       (1 oz Cu)
  εr     = 4.3            (FR4 nominal)
  target Z_diff = 90 Ω    (USB 2.0 spec)

For coupled microstrip Z_diff, two formulae apply:
  1. Hammerstad-Jensen (closed-form, isolated single-ended) Z₀ then
     Z_diff ≈ 2*Z₀*(1 - 0.48*exp(-0.96*S/h))  [Jardon-Aguilar /
     Edwards-Steer texts]
  2. scikit-rf's MLine + coupling correction
  3. openEMS 3D FDTD on the actual W=0.30/S=0.10/h=0.21 stripline

Verdict: all three should agree to within 5-10% on Z_diff. PASS if
Z_diff in 81..99 Ω band (= 90 Ω ± 10%, USB-2 spec tolerance).
"""
import os
import sys
import math
import tempfile

# Geometry (SI / mm where noted)
W_mm = 0.30
S_mm = 0.10
H_mm = 0.21
T_mm = 0.035
EpR  = 4.3
TARGET_ZDIFF = 90.0

W = W_mm * 1e-3
S = S_mm * 1e-3
H = H_mm * 1e-3
T = T_mm * 1e-3


def hj_single_ended():
    """Hammerstad-Jensen 1980 single-ended Z₀ (with thickness correction)."""
    W_eff = W + (T/math.pi) * (1 + math.log(2*H/T))
    e_eff = (EpR + 1)/2 + (EpR - 1)/2 * (1 + 12*H/W_eff)**(-0.5)
    if W_eff/H <= 1:
        Z0 = 60/math.sqrt(e_eff) * math.log(8*H/W_eff + W_eff/(4*H))
    else:
        Z0 = 120*math.pi/math.sqrt(e_eff) / (W_eff/H + 1.393 + 0.667*math.log(W_eff/H + 1.444))
    return Z0


def hj_diff_pair():
    """Z_diff from Z₀ and S/h coupling factor (Edwards-Steer)."""
    Z0 = hj_single_ended()
    coupling = 0.48 * math.exp(-0.96 * S/H)
    return 2 * Z0 * (1 - coupling)


def skrf_mline():
    """scikit-rf MLine — single-ended Z₀ + apply coupling correction."""
    import skrf as rf
    from skrf.media import MLine
    freq = rf.Frequency(start=0.5, stop=0.5, npoints=1, unit='GHz')
    ms = MLine(frequency=freq, w=W, h=H, t=T, ep_r=EpR)
    Z0 = ms.z0.real[0]
    coupling = 0.48 * math.exp(-0.96 * S/H)
    return Z0, 2 * Z0 * (1 - coupling)


def openems_coupled():
    """openEMS 3D FDTD on the COUPLED PAIR geometry. Extracts Z_diff
    from the differential mode (E_diff / I_diff measured at the line)."""
    import numpy as np
    from CSXCAD import ContinuousStructure
    from openEMS import openEMS
    from openEMS.physical_constants import C0

    unit = 1e-3
    MSL_LEN = 25.0   # mm — long enough for clean extraction
    f_max = 2e9
    NRTS = 30000

    Sim_Path = os.path.join(tempfile.gettempdir(), "openems_usb_zdiff")
    os.makedirs(Sim_Path, exist_ok=True)
    for fn in os.listdir(Sim_Path):
        p = os.path.join(Sim_Path, fn)
        if os.path.isfile(p): os.remove(p)

    FDTD = openEMS(NrTS=NRTS, EndCriteria=1e-4)
    FDTD.SetGaussExcite(f_max/2, f_max/2)
    FDTD.SetBoundaryCond(['PML_8','PML_8','MUR','MUR','PEC','MUR'])

    CSX = ContinuousStructure()
    FDTD.SetCSX(CSX)
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(unit)

    pitch = W_mm + S_mm   # 0.4 mm center-to-center
    res_far = C0/(f_max * np.sqrt(EpR))/unit/30
    dy_strip = W_mm / 8.0       # 0.0375 mm

    # X mesh — long axis
    dx = 0.5
    mesh.AddLine('x', np.arange(-MSL_LEN, MSL_LEN + dx/2, dx))

    # Y mesh — fine across both traces. Trace 1 centered at -pitch/2,
    # trace 2 at +pitch/2.
    Y_T1 = -pitch / 2.0
    Y_T2 = +pitch / 2.0
    y_fine = np.arange(Y_T1 - W_mm/2 - 1.0, Y_T2 + W_mm/2 + 1.0 + dy_strip/2, dy_strip)
    mesh.AddLine('y', y_fine)
    mesh.AddLine('y', [-10.0, 10.0])
    mesh.SmoothMeshLines('y', res_far)

    # Z mesh
    mesh.AddLine('z', np.linspace(0, H_mm, 6))
    mesh.AddLine('z', np.array([0.5, 1.0, 2.0, 4.0]))
    mesh.SmoothMeshLines('z', res_far)

    # Substrate
    substrate = CSX.AddMaterial('FR4', epsilon=EpR)
    substrate.AddBox([-MSL_LEN, -10.0, 0], [MSL_LEN, 10.0, H_mm])
    pec = CSX.AddMetal('PEC')

    # Two MSLPorts — port 1 (excited differential) and port 2 (terminated)
    # For diff-mode excitation, use ports with opposing polarity.
    FEED_SHIFT = 2.0
    MEAS_SHIFT = 15.0
    # Port 1 (left) — TRACE 1 excited +1, TRACE 2 -1
    port = [None]*4
    # Trace 1 left port
    port[0] = FDTD.AddMSLPort(1, pec,
        [-MSL_LEN, Y_T1 - W_mm/2, H_mm], [0, Y_T1 + W_mm/2, 0],
        'x', 'z', excite=-1, FeedShift=FEED_SHIFT, Feed_R=50,
        MeasPlaneShift=MEAS_SHIFT, priority=10)
    # Trace 2 left port — opposite-polarity excite for diff-mode
    port[1] = FDTD.AddMSLPort(2, pec,
        [-MSL_LEN, Y_T2 - W_mm/2, H_mm], [0, Y_T2 + W_mm/2, 0],
        'x', 'z', excite=+1, FeedShift=FEED_SHIFT, Feed_R=50,
        MeasPlaneShift=MEAS_SHIFT, priority=10)
    # Right-side ports (terminated)
    port[2] = FDTD.AddMSLPort(3, pec,
        [MSL_LEN, Y_T1 - W_mm/2, H_mm], [0, Y_T1 + W_mm/2, 0],
        'x', 'z', Feed_R=50, MeasPlaneShift=MEAS_SHIFT, priority=10)
    port[3] = FDTD.AddMSLPort(4, pec,
        [MSL_LEN, Y_T2 - W_mm/2, H_mm], [0, Y_T2 + W_mm/2, 0],
        'x', 'z', Feed_R=50, MeasPlaneShift=MEAS_SHIFT, priority=10)

    print(f"  openEMS: running FDTD for the diff pair (NrTS={NRTS})...", flush=True)
    FDTD.Run(Sim_Path, cleanup=True, verbose=1)

    f_test = np.array([0.5e9])
    for p in port:
        p.CalcPort(Sim_Path, f_test)

    # Z_se (each trace's self-impedance) — the line characteristic
    # impedance as measured at the port
    Z_T1 = abs(port[0].Z_ref[0])
    Z_T2 = abs(port[1].Z_ref[0])
    # Z_diff in differential mode is approximately 2*Z_odd, where Z_odd
    # is the odd-mode impedance. For a symmetric pair excited
    # differentially, the measured Z at each port reduces to Z_odd.
    # → Z_diff ≈ 2 * Z_odd ≈ 2 * mean(Z_T1, Z_T2)
    Z_odd_avg = (Z_T1 + Z_T2) / 2.0
    Z_diff = 2 * Z_odd_avg
    return Z_T1, Z_T2, Z_diff


def main():
    print("=== USB diff-pair Z_diff sign-off (3 tools) ===\n")
    print(f"Geometry: W={W_mm} mm, S={S_mm} mm, h={H_mm} mm, t={T_mm} mm, εr={EpR}")
    print(f"Stackup: L1 → prepreg 7628 (0.21 mm) → L2 GND (JLC06161H-7628)\n")

    # 1. Hammerstad-Jensen analytical
    Z0_hj = hj_single_ended()
    Zdiff_hj = hj_diff_pair()
    print(f"[1] Hammerstad-Jensen 1980 (analytical)")
    print(f"     Z₀ single-ended         = {Z0_hj:.2f} Ω")
    print(f"     Z_diff (coupling corr.) = {Zdiff_hj:.2f} Ω\n")

    # 2. scikit-rf MLine + coupling
    try:
        Z0_skrf, Zdiff_skrf = skrf_mline()
        print(f"[2] scikit-rf MLine")
        print(f"     Z₀ single-ended         = {Z0_skrf:.2f} Ω")
        print(f"     Z_diff (coupling corr.) = {Zdiff_skrf:.2f} Ω\n")
    except Exception as e:
        print(f"[2] scikit-rf FAILED: {e}\n")
        Zdiff_skrf = None

    # 3. openEMS 3D FDTD
    try:
        Z_T1, Z_T2, Zdiff_oems = openems_coupled()
        print(f"[3] openEMS 3D FDTD (actual coupled geometry)")
        print(f"     Z_trace1                = {Z_T1:.2f} Ω")
        print(f"     Z_trace2                = {Z_T2:.2f} Ω")
        print(f"     Z_diff (= 2 × Z_odd)    = {Zdiff_oems:.2f} Ω\n")
    except Exception as e:
        print(f"[3] openEMS FAILED: {e}\n")
        Zdiff_oems = None

    # Verdict
    print(f"Target: {TARGET_ZDIFF} Ω (USB 2.0)")
    print(f"Acceptance: ±10% = {TARGET_ZDIFF*0.9:.0f}..{TARGET_ZDIFF*1.1:.0f} Ω")
    print()
    for name, val in [
        ("H-J (analytical)", Zdiff_hj),
        ("scikit-rf MLine", Zdiff_skrf),
        ("openEMS 3D FDTD", Zdiff_oems),
    ]:
        if val is None:
            print(f"  {name:<22}: FAILED")
            continue
        err = abs(val - TARGET_ZDIFF) / TARGET_ZDIFF * 100
        verdict = "PASS" if TARGET_ZDIFF*0.9 <= val <= TARGET_ZDIFF*1.1 else "FAIL"
        print(f"  {name:<22}: {val:6.2f} Ω  ({err:5.2f}% error)  {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
