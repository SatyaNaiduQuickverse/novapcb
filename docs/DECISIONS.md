# Locked v1 decisions (2026-05-18)

All 9 scoping decisions for the v1 FC, signed off 2026-05-18. Each section shows the resolution line on top; the original options and discussion are kept below so the reasoning isn't lost. New open questions go in `OPEN_QUESTIONS.md`, not here. Owner: Sai.

## 1. MCU

**Resolved 2026-05-18:** STM32H743VIT6 — the **Holybro Pixhawk 6X (the autopilot currently flying)** uses STM32H743xx per the `Pixhawk6X` ArduPilot hwdef, so H743 keeps full ArduCopter parity with what the surrounding stack already talks to. MatekH743 is the closest single-PCB H743 reference to fork for v1's functional-drop-in scope; Pixhawk6X hwdef is the reference for v2.

**Options on the table:**

- **STM32H743VIT6** — what the Holybro Pixhawk 6X uses (and MatekH743, Pixhawk 6C, and several others). Highest software path-of-least-resistance; existing board defs to fork. Note: CubeOrange/CubeOrangePlus are H757 (dual-core); not the right reference for novapcb.
- **STM32H753** — cryptographic peripherals; nice if we ever want signed firmware, otherwise overkill.
- **STM32H723** — cheaper, smaller flash; tight for ArduCopter.
- **RP2350** — interesting because we're already a Pi house, dual-core M33, but ArduPilot doesn't target it; would need a non-ArduPilot firmware path (INAV / Betaflight / custom MAVLink shim). Punts on ArduCopter parity.

**Recommendation:** start with H743 unless there's a strong reason not to. It keeps the firmware story trivial.

## 2. Form factor

**SUPERSEDED 2026-05-20 (Sai pivot, mid-Phase-4)**: the 36×36 / 30.5×30.5 M3 v1 spec is set aside. New direction:

**v1 = RECTANGULAR, sized to the placement.** No standard-dimension constraint. Board outline shape (length × breadth) is an OUTPUT of deliberate physics-guided placement (Phase pivot Step 3), not a fixed input. Sai's explicit direction 2026-05-20 ("don't confine to Pixhawk 30.5 / 36×36"). Mounting pattern + airframe tray follow the resulting board outline; a new tray is acceptable.

**Reliability mandate** (Sai 2026-05-20, verbatim: "it working 100% is the priority", "strong resilient stuff that won't fail"): use the freed board area for generous spacing, clean subsystem separation, robust margins — design so EMI/EMC/thermal failure modes simply don't arise. Quality + real workability over time-to-build.

**Open dimensions** (Sai's input pending — see `OPEN_QUESTIONS.md pivot-2026-05-20`):
- Aspect ratio (the rectangle's length:breadth)
- Layer count (4 vs 6 — Phase 0.6 pivot Step 3 assesses)
- Mounting pattern (driven by the airframe envelope Sai will provide)

**v2 = FMUv6X mechanical drop-in** — still deferred (separate FMU + isolated-IMU boards, exact 6X mechanical match); see OPEN_QUESTIONS.

**Original-v1 record kept here for traceability:**
- *Resolved 2026-05-18; mechanical specs disambiguated 2026-05-20 (Phase 2.5 P1.1)*: v1 = Pixhawk-standard mini-FC single-PCB — board outline 36 × 36 mm, mounting holes 30.5 × 30.5 mm center-to-center M3 (4 holes; the "30.5×30.5 M3" Pixhawk-standard pattern, matching MatekH743 reference). Functional drop-in against the Holybro Pixhawk 6X. **Superseded by 2026-05-20 pivot above** because density on the 36×36 mini-FC drove the Phase 6 P0 findings (PDN anti-resonance at 100 kHz, AP2112K LDO Tj=88°C, inrush 3.39A, EMC harmonic intersections in GPS L1). Roomier rectangle + reliability mandate addresses all four.

- **Pixhawk standard 30.5×30.5 mm M3, single-PCB** (chosen for v1) — well-trodden form factor; closest reference design is MatekH743 (36×36 board, 30.5×30.5 c-to-c M3 holes). Functional swap only; the airframe needs a new tray since the Pixhawk 6X uses the FMUv6X pattern, not the 30.5×30.5 mini-FC pattern.
- **FMUv6X form factor, two-board (FMU + isolated IMU)** (chosen for v2) — true mechanical drop-in against the 6X. Significantly more complex (vibration isolation, exact connector pin-out, dual-board assembly); not worth blocking v1 on.
- **Custom outline** — only if there's a frame-fit problem with both of the above.

**Recommendation:** v1 = Pixhawk standard for fastest path to a flying custom FC; v2 = FMUv6X once v1 proves out.

## 3. ESC channel count

**Resolved 2026-05-18:** 8 channels (DShot300/600, PWM fallback) — H7 has the timers for free; 4 spare lines cover hex/gimbal/payload contingencies without a re-spin, at the cost of connector real-estate only.

4 / 6 / 8. Depends on the airframe — the current Nova drone is a quad (4 motors), but we may want headroom for a hex or for gimbal/payload PWM. 8 channels of DShot is cheap on H7 (timer-rich) so this is mostly a connector-real-estate question.

**Recommendation:** 8 channels — DShot on H7 is timer-cheap; gives headroom for hex/gimbal/payload without a re-spin. Cost is connector real estate.

## 4. ELRS RX integration

**Resolved 2026-05-18:** External RX module + on-board CRSF UART — skips RF layout risk for v1 while still retiring the ESP32-C6 bridge; the integrated-RF option is a v2 conversation.

- **Off-board** (status quo): RP4TD on USB, ESP32-C6 bridge, FC consumes CRSF over UART from the bridge.
- **On-board CRSF UART**: skip the ESP32, route ELRS RX directly to an FC UART. Saves a USB port and ~15 g.
- **On-board ELRS module socket** (SX1280 + STM32 daughterboard): all-in-one. Higher PCB risk — RF layout.

**Recommendation:** v1 on-board CRSF UART, RX module stays external. Skip the integrated RF for now.

## 5. Voltage / current monitoring

**Resolved 2026-05-18:** External Mauch power module via FC ADC input — matches what the existing airframe already runs; no on-board high-side current sensor to calibrate.

- Onboard hall-effect current sensor (e.g. ACS758) vs external power module (Mauch / Holybro).
- Mauch 200 A is what the current frame uses.

**Recommendation:** match what the airframe already has — external Mauch, FC just provides the analog input.

## 6. Logging / SD card

**Resolved 2026-05-18:** Yes, microSD slot for ArduPilot `.bin` logs — post-incident analysis is non-negotiable; cost is one connector and a few traces. Mechanical placement deferred to layout time.

ArduPilot wants a microSD slot for `.bin` logs. Yes/no and where it sits mechanically.

## 7. Connector standard

**Resolved 2026-05-18:** JST-GH (Pixhawk family) — matches every harness on the existing airframe; bring-up must not also require re-crimping cables.

JST-GH (Pixhawk standard) vs JST-SH 1.0 vs solder pads. JST-GH is bulky but matches all our existing harnesses.

## 8. PCB stack-up

**SUPERSEDED 2026-05-20 (Sai pivot)**: 4-layer was right for the tight 36×36 board; the new rectangular roomier outline reopens the 4 vs 6 question. Phase 0.6 pivot Step 3 (placement) assesses which is appropriate given:
- The reliability mandate ("won't fail") favors 6-layer if it materially reduces SI/EMI failure modes.
- Phase 6k EMC analytical found 4 harmonics above -40 dB in GPS L1 / ELRS bands — a 6-layer with a second clean GND or split power plane can reduce those.
- 6-layer ~25-40% more expensive at JLCPCB but trivial against the resilience priority.

**Recommendation pending Step-3 analysis**: lean 6-layer if it provides quantifiable EMI/SI improvement; stay 4-layer if 6 only adds cost without measurable failure-mode reduction.

**Original v1 record:**
- *Resolved 2026-05-18*: 4-layer for v1 — clean ground plane under the IMU is the load-bearing requirement; 6-layer is reserved for a v2 spin only if on-board RF lands.

## 9. USB VID/PID for the FC

**Resolved 2026-05-18:** ArduPilot allocation (option a) — request via the ArduPilot forum when the time comes; meanwhile firmware can set `USB_VENDOR_STRING` starting with `ArduPilot` since udev only requires the string prefix to match.

The FC's USB descriptor must include strings that produce `/dev/serial/by-id/usb-ArduPilot_*-if00` on the drone Pi (see INTERFACE_CONTRACT.md §3.1). udev does not require a specific VID/PID, but some ground-station / downstream consumers filter on VID/PID, so we should pick deliberately rather than re-use a random vendor's allocation.

**Options:**

- **(a) ArduPilot allocation** — ask on the ArduPilot forum / dev channel for a VID/PID assigned to this board. Matches the convention used by the Pixhawk 6X and other Pixhawk-family boards; downstream filters that whitelist ArduPilot-family devices will accept it without changes.
- **(b) pid.codes free pool** — request a PID under the `0x1209` (pid.codes) free VID for open-source hardware. Fast, no permission needed beyond a PR to pid.codes, but downstream Ardu-family VID/PID filters won't recognise it.

**Recommendation:** (a). Aligning with the ArduPilot allocation keeps us inside the family that downstream tools already expect; pid.codes is a fine fallback only if the ArduPilot path stalls.

Note: udev by-id resolution only requires the *string* prefix to match (`USB_VENDOR_STRING` starting with `ArduPilot`), not the VID/PID. So even before VID/PID is locked, firmware bring-up that depends only on the by-id symlink will work.

---

## 10. Reliability-first design priority (Sai pivot 2026-05-20)

**Resolved 2026-05-20 — Sai's directive, verbatim:** "it working 100% is the priority", "strong resilient stuff that won't fail", "quality + real workability over everything; time is not a constraint."

This is a **design principle**, not a specific component choice. Applied across the entire post-pivot design:

- **Spacing**: generous, not packed. The freed board area from the §2 form-factor pivot is spent on margin, not features.
- **Subsystem separation**: power tree at one end, sensitive analog+IMU at the far end, MCU central, connectors on edges. EMI / thermal / mechanical-cable-strain failure modes don't arise if the physical layout prevents them.
- **Failure-mode mitigation over justification**: when a Phase 6 sim surfaces a CAUTION (e.g. inrush 3.39A over the <2A criterion; AP2112K Tj=88°C borderline), the design FIXES it. We don't argue why the failure mode "probably won't trigger in practice." See §11 (inrush) for the first instance.
- **Worst-case boundary conditions**: thermal modeling at 50-60°C ambient (drone bay / sun-soaked), still-air convection (no airflow assumed). If it works there, it works in flight.
- **Deterministic over heuristic**: prefer designs whose failure-recovery behavior is predictable + repeatable. E.g. MOSFET-based soft-start beats NTC thermistor for inrush limiting because NTC has reliability caveats (steady-state voltage drop; fails to reset on fast warm power-cycle).
- **No premature optimization for cost / area / BOM count**: if a small upgrade materially reduces a failure mode, it lands.

This principle resolves design forks where reliability and another axis (cost, board area, BOM count) conflict — reliability wins.

---

## 11. Inrush limiting on the +5V BEC input (Step 2 of pivot)

**To be resolved by Phase 0.6 pivot Step 2 (inrush mitigation PR)**, in progress.

Background: Phase 6a found inrush peak ~3.39 A at power-on (over the <2A SIMULATION_PLAN §6a criterion + likely over a 3A BEC's transient tolerance). Per §10 reliability mandate, this is FIXED in the design.

**Options under evaluation** (Step 2 PR will resolve):
- **MOSFET-based active soft-start** — P-MOSFET in the 5V path with an RC on the gate that slowly turns the FET on over ~10 ms. Deterministic; resets cleanly on any power-cycle; no steady-state voltage drop. Master's steer: this is the most-resilient option, favor it.
- **NTC inrush limiter** — series NTC thermistor (e.g. 5Ω cold → ~50mΩ hot). Simple, one part. **Caveats**: real steady-state voltage drop (~150mV at 350mA load) wasted as heat; FAILS to reset on a fast warm power-cycle (NTC stays low-resistance after a quick brownout, then the next inrush event isn't limited). Per §10 these are real reliability caveats.
- **EN-pin RC soft-start on AP2112K** — 10 nF + 100 kΩ to GND on the LDO's EN pin slows turn-on by ~10 ms; gradual LDO output ramp absorbs input transient. Lighter-weight than MOSFET soft-start but only addresses LDO inrush, not the input cap charging spike.

**Recommendation pending Step 2 PR**: MOSFET soft-start per master + §10. The §6.5 forum-review can sanity-check the topology.
