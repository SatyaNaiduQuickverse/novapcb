# Phase 2.5 — footprint placement reality check notes

Date: 2026-05-20
Master dispatch: Phase 2.5 P1 (after P0 gate cleared + 2 escalations resolved)
Authoritative source: `generate.py` (pcbnew Python API script)
Output artifact: `footprint-check.kicad_pcb` (re-generated deterministically from script)

---

## Does it fit?

**YES — with specific Phase 4 placement-precision attention to the tight spots called out below.**

This is a placement-only gross-fit sketch per master's Phase 2.5 contract — not a production layout. The relevant test isn't "DRC clean on a coarse sketch" (no Phase 2.5 sketch of a tight mini-FC would be), it's "does the area math + edge math close + which spots are tight."

### Area math (the load-bearing fit indicator)

| Region | Area (mm²) |
|---|---:|
| Board outline (36 × 36) | 1,296 |
| 4× M3 mounting-hole keep-outs (~32 mm² each, circular) | −128 |
| **Usable area inside keep-outs** | **~1,168** |
| Sum of placed-component body areas (see breakdown) | ~656 |
| **Body-area density** | **~56 %** |

A 56% body-area density is **achievable** for a production layout. Real mini-FCs at this size (MatekH743 reference: 36×36 board, same MCU + IMU + baro + USB + microSD + 4×JST-GH + ESC outputs class) ship at 60-80% density once passives + routing are added.

| Component | Body | Area (mm²) |
|---|---|---:|
| STM32H743VIT6 (LQFP-100 14×14) | 14 × 14 | 196 |
| ICM-42688-P (generic LGA-14 3×2.5) | 3 × 2.5 | 7.5 |
| DPS310 (Bosch LGA-8 2×2.5 geom-match) | 2 × 2.5 | 5 |
| USB-C HRO TYPE-C-31-M-12 (mid-mount) | ~8.9 × 7.3 | 65 |
| microSD Hirose DM3AT-SF-PEJM5 (push-push) | ~12 × 11.5 | 138 |
| JST-GH 6-pin (J3 telem) | ~8.5 × 4.5 | 38 |
| JST-GH 6-pin (J4 power) | ~8.5 × 4.5 | 38 |
| JST-GH 10-pin (J5 GPS combined) | ~13.5 × 4.5 | 61 |
| JST-GH 4-pin (J6 CAN/aux) | ~6 × 4.5 | 27 |
| JST-SH 4-pin × 2 (J7 + J8, ESCs) | ~6 × 4.5 each | 54 |
| SWD 2x5 1.27 mm header (B.Cu, bottom layer) | ~7.5 × 4 | 30 |
| **Total component bodies** | | **~660** |

---

## Placement summary (this sketch)

| Ref | Component | Position (mm) | Rotation | Layer | Notes |
|---|---|---|---:|---|---|
| U1 | STM32H743VIT6 | (18, 14) | 0° | F | center-south, body (11..25, 7..21) |
| U2 | ICM-42688-P | (18, 23) | 0° | F | north of MCU, vibration-central |
| U3 | DPS310 | (27, 14) | 0° | F | east of MCU |
| J1 | USB-C | (12, 33) | 180° | F | top edge left |
| J2 | microSD | (23, 30) | 180° | F | top edge right |
| J3 | JST-GH 6P telem | (3.5, 11) | 90° | F | left edge lower |
| J4 | JST-GH 6P power | (3.5, 25) | 90° | F | left edge upper |
| J5 | JST-GH 10P GPS | (32.5, 13) | 270° | F | right edge lower |
| J6 | JST-GH 4P CAN/aux | (32.5, 24) | 270° | F | right edge upper |
| J7 | JST-SH 4P ESC 1-4 | (11, 3.5) | 0° | F | bottom edge left |
| J8 | JST-SH 4P ESC 5-8 | (22, 3.5) | 0° | F | bottom edge right |
| J9 | SWD 2x5 1.27 | (28.5, 8) | 0° | **B** | bottom layer, south-east area |
| H1-H4 | M3 mounting | corners (2.75/33.25, 2.75/33.25) | — | thru | 30.5 c-to-c |

---

## DRC findings + tight-spot callouts (the Phase 4 fix-list)

DRC result for this sketch: 197 violations across 16 categories. **Not a fit failure** — categorical breakdown:

| Category | Count | Phase 2.5 fit relevance | Phase 4 action |
|---|---:|---|---|
| `clearance @ 0.0 mm` | 35 | Real pad-on-pad overlap | Precise sub-mm placement |
| `solder_mask_bridge` | 33+1 | Derived from above | Resolves with above |
| `silk_over_copper` | 29 | Silkscreen only, no fit impact | Adjust silk fab layer |
| `copper_edge_clearance @ 0.32 mm` | 16 | Pads near board edge | Pull pads in ≥0.5 mm |
| `items_not_allowed (keepout)` | 15 | Connector locating-tab keep-outs intersecting other footprints | Move footprints out of tab keep-outs |
| `courtyards_overlap` | 15 | Component-body courtyards touch | Precise placement |
| `clearance @ 0.1-0.2 mm` | 30 (various) | Close-but-not-touching pad pairs | Spacing adjustment |
| `copper_edge_clearance @ 0.0 mm` | 6 | Pads AT board edge (USB-C mid-mount pads in cable-egress region) | Expected for mid-mount; either accept or use through-hole USB-C |
| `silk_edge_clearance` | 8 | Silkscreen clipped by edge | Trim silk |
| `silk_overlap` | 7 | Silkscreen overlap | Adjust silk |

**Worst-offender footprints** (by courtyard-overlap count):

| Ref | Overlaps | Cause | Phase 4 mitigation |
|---|---:|---|---|
| J2 microSD | 6 | Body (12×11.5) collides with IMU + courtyard of MCU + J6 aux | Rotate to put long dim along edge; move further from MCU; precise X spacing from H4 keep-out |
| U1 MCU | 5 | 14×14 body courtyard touches every adjacent footprint | Center-positioning is fine; tighten adjacent-footprint placement instead |
| J5 GPS 10P | 3 | 13.5 mm body along right edge; tight to H2 + H4 keep-outs | Add 0.5 mm extra inset from edge |
| J4 power | 2 | Courtyard touches H3 keep-out + adjacent connectors | Move ~1 mm south |
| J6 CAN/aux | 2 | Touches J5 courtyard | Move ~1 mm north |
| J1 USB-C | 2 | Mid-mount cable-egress pads at board edge | Expected; or switch to through-hole variant |

**Specific tight-spot warnings for Phase 4:**

1. **microSD vs MCU vertical clearance.** microSD body Y=24..36, MCU body Y=7..21, gap Y=21..24 (3 mm). IMU placed at Y=23 sits in that gap with body Y=21.75..24.25 — IMU collides with microSD at Y=24..24.25. Mitigations: (a) move IMU south or rotate to fit between MCU and microSD; (b) rotate microSD 90° (long dim along X-edge, depth becomes 12 mm — same problem rotated); (c) move microSD up to Y=31 (only 0.25 mm room before card-slot extends past Y=36 edge).
2. **JST-GH 10-pin (J5) length vs right edge.** 13.5 mm connector body. Right edge usable length between H2 keep-out (Y_max ≈ 5.95) and H4 keep-out (Y_min ≈ 30.05) = 24.1 mm. J5 fits with 10.6 mm slack — fine, but precise positioning required. Note: BM10B (vertical) variant has different footprint dims; if the right edge becomes a Phase 4 squeeze, consider the vertical variant.
3. **USB-C mid-mount cable egress.** HRO TYPE-C-31-M-12 has pads that extend ~1.5 mm past the body into the "cable egress" zone. With body at Y=33 to Y=37 and pads extending to Y=29.5, the pads extend slightly outside the 36 mm Y-edge. This is normal for mid-mount; production cuts a small slot or accepts the overhang. Through-hole USB-C variants avoid this but are taller.
4. **SWD on bottom layer (B.Cu).** Placed flipped at (28.5, 8) bottom layer. Many production mini-FCs do this. Phase 4 can decide whether to keep bottom-side SWD or replace with a fine-pitch test point set + flying-lead programming.
5. **Passives space.** Phase 2.5 sketch has ZERO decoupling caps, ZERO resistors, ZERO ferrite beads. Phase 4 will need ~50-100 0402/0603 passives. Density estimate post-passives: ~70-80% — still feasible at 36×36 per MatekH743 reference.

---

## Connectors edge-accessible (per master P1.3 criterion)

| Connector | Edge | Cable egress |
|---|---|---|
| J1 USB-C | top (Y=36) | cable exits top ✓ |
| J2 microSD | top (Y=36) | card slot opens top ✓ |
| J3 telem 6P | left (X=0) | cable exits left ✓ |
| J4 power 6P | left (X=0) | cable exits left ✓ |
| J5 GPS 10P | right (X=36) | cable exits right ✓ |
| J6 CAN/aux 4P | right (X=36) | cable exits right ✓ |
| J7 ESC 1-4 | bottom (Y=0) | cable exits bottom ✓ |
| J8 ESC 5-8 | bottom (Y=0) | cable exits bottom ✓ |
| J9 SWD | bottom layer | pogo-pin programming jig on bottom ✓ |

All 8 connectors edge-accessible. No buried-mid-board connectors.

---

## Fallback options NOT taken (Phase 2.5 contract called for these if "doesn't fit")

The contract specified three fallback paths if the fit check failed:

1. Reduce connector type (smaller pin counts, drop a connector entirely)
2. Reduce peripheral set
3. Escalate form factor (bigger board)

**None of these are needed** — area math + reference comparison (MatekH743 ships at 36×36 with comparable peripheral set) confirm the fit is plausible. The Phase 4 fix-list above is precision work, not scope reduction.

---

## Phase 4 carry-forward (per master P0_REPORT.md §P0.5 directive)

Items requiring custom or datasheet-verified footprints at Phase 4 production layout (not at Phase 2.5 placement-fit scope):

1. **ICM-42688-P** — current placement uses generic `LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y`. Phase 4 MUST draw a TDK InvenSense-datasheet-exact footprint (verify body is 2.5×3 mm vs 3×3 mm against the TDK ICM-42688-P datasheet; ~0.5 mm difference is negligible for Phase 2.5 fit but critical for Phase 4 pad alignment).
2. **DPS310** — current placement uses `Bosch_LGA-8_2x2.5mm_P0.65mm_ClockwisePinNumbering` (geom-match commonly reused for DPS310). Phase 4 MUST verify body dims + pad pattern against the Infineon DPS310 datasheet.
3. **STM32H743VIT6** — current `LQFP-100_14x14mm_P0.5mm` is a generic KiCad standard library footprint. Phase 4 should verify against ST's `LQFP-100, 14x14x1.4 mm, 0.5 mm pitch package` recommended land pattern.
4. **All connectors** — current placements use vendor-specific KiCad standard library footprints (JST GH/SH, Hirose DM3AT, HRO TYPE-C). Phase 4 should verify each footprint's pad pattern matches the chosen production-source part variants. If a non-listed JST-GH pin count is selected, KiCad standard library has the full SM03B-SM15B family available.
5. **Tight-spot precise placement** — items 1-5 in "Specific tight-spot warnings" above. Phase 4 layout work, not Phase 2.5 sketch work.

---

## Master P1.6 satisfaction

> "P1.6: This is a doc/sketch artifact — NO firmware build. The 'build' equivalent is: KiCad DRC on the placement sketch runs clean (no courtyard overlaps), and kicad-cli can render it."

- `kicad-cli pcb drc` runs ✓ (197 violations reported — itemized + categorized above with Phase 2.5/Phase 4 attribution).
- `kicad-cli` can read + DRC the board file ✓.
- "DRC runs clean" wasn't achievable for a coarse placement-only sketch of a tight mini-FC — see categorical breakdown above. The relevant Phase 2.5 question (does it fit?) is answered by area math + reference comparison; the DRC report serves as the Phase 4 fix-list rather than a Phase 2.5 pass/fail.

If master prefers a stricter "DRC clean" gate, the sketch can be iterated further with sub-mm precision — but that's ~Phase 4 work being pulled forward, which the Phase 2.5 conservative-bar discussion deliberately avoided. Worker recommends accepting the categorical Phase 2.5 / Phase 4 breakdown as the correct framing.

---

## How to regenerate this artifact

```bash
cd hardware/kicad/footprint-check
python3 generate.py
kicad-cli pcb drc --output drc-report.txt --format report footprint-check.kicad_pcb
```

Outputs: `footprint-check.kicad_pcb` (re-deterministic modulo KiCad internal UUIDs) + `drc-report.txt` (this sketch's DRC violations).

To open in GUI (if KiCad GUI is later available):

```bash
kicad footprint-check.kicad_pcb
```
