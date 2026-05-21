# JLCPCB JLC06161H 6-Layer Manufacturability Compliance Audit

> **Per Sai 2026-05-21 directive** (via master): "make sure it is manufacturable by JLCPCB, follow ALL rules." This is the comprehensive DFM-compliance pass — every rule, our value, JLC spec, OK/FIX. Becomes a hard item in the Phase 7a fab-ready gate.
>
> **Status**: AUDIT — fixes proposed but not all applied yet. The final pre-order DFM (JLCPCB's online analyzer) is Sai's to run.

## 1. Source

JLCPCB's PCB Capabilities page (`https://jlcpcb.com/capabilities/Capabilities`) is JS-driven; direct WebFetch returned page skeletons without numerical tables. **Authoritative source used here**: the community-maintained `jlcpcb.kicad_dru` rule set by `agausmann/jlcpcb-kicad-drc` ([repo](https://github.com/agausmann/jlcpcb-kicad-drc)), which cites JLCPCB capabilities directly and codifies the standard JLC 6-layer numbers as KiCad-applicable rules. File saved to `hardware/kicad/novapcb-layout-v2/jlcpcb.kicad_dru` and bound to the project as a custom rules file.

Verified-by-fetch single value: from `https://jlcpcb.com/impedance` — "High-precision multilayer: min trace/space 3.5 mil, min via 0.2 mm, min BGA 0.25 mm". This corroborates the community DRC's tightest tier values.

Additional cross-reference: SparkFun Eagle JLCPCB DRC files cite the same JLC capability page and report identical standard-tier values (4 mil trace/space, 7 mil annular ring on 2-layer).

Sai's final-DFM step at order time uploads the gerbers to JLCPCB's online DFM analyzer; that is the binding fab-side check. This document's job is to make the design pass that step cleanly.

## 2. Comprehensive rule audit

| # | Rule | novapcb design value | JLC spec | OK / FIX |
|---:|---|---|---|---|
| 1 | Min trace width | 0.10 mm (Default class 0.20 mm typical) | 0.127 mm 1-2L / 0.09 mm 4-6L (commented in community DRC) | **OK** — tracks routed at ≥0.20 mm, well above min |
| 2 | Min trace spacing (clearance) | 0.10 mm project / 0.20 mm netclass | 0.127 mm 1-2L / 0.09 mm 4-6L | **OK** — netclass 0.20 mm enforced during route |
| 3 | Min drill hole size | 0.30 mm (project min) — current drills are 0.30 mm | 0.20 mm (JLC standard now) | **OK** (we are above min) |
| 4 | Min via outer diameter | **0.40 mm (project min); we placed 102 plane stitches at 0.40 mm** | 0.46 mm with 0.20 drill (annular 0.13 mm) OR 0.56 mm with 0.30 drill | **FIX** — 0.40 mm vias fail JLC annular-ring spec |
| 5 | Min annular ring | **0.05 mm (project min); 0.40/0.30 vias = 0.05 mm annular** | **0.13 mm** (community DRC; matches JLC 5-mil standard) | **FIX** — major: 0.05 mm is below spec by 0.08 mm. All 0.40 mm vias affected. |
| 6 | Min hole-to-hole (different nets) | **0.25 mm (project min)** | **0.50 mm** | **FIX** — 4 pairs near U3 IMU at 0.316-0.350 mm |
| 7 | Min hole-to-hole (same net) | 0.25 mm | 0.254 mm | OK |
| 8 | Via-to-track (hole-to-track clearance) | 0.20 mm project | 0.254 mm | **FIX-MARGINAL** — tighten to 0.254 |
| 9 | PTH-to-track clearance | 0.20 mm (project min_hole_clearance) | 0.33 mm | **FIX-MARGINAL** — tighten or document conditional |
| 10 | Board edge to copper clearance | 0.30 mm | 0.20 mm | **OK** (we are above) |
| 11 | Silkscreen-to-pad clearance | 0.00 mm (off) | 0.15 mm typical | **FIX** — turn on, set 0.15 mm |
| 12 | Soldermask-to-copper clearance | 0.00 mm (off) | 0.10 mm typical | **FIX** — turn on, set 0.10 mm |
| 13 | Min mask sliver (between adjacent pads) | not enforced | 0.10 mm typical | **FIX** — add custom rule |
| 14 | Min silkscreen line width | 0.08 mm | 0.13 mm typical | **FIX** — tighten to 0.15 mm (KiCad default) |
| 15 | Pad-to-pad SMD clearance (different nets) | 0.20 mm (netclass) | 0.127 mm | **OK** |
| 16 | Pad-to-pad PTH clearance (different nets) | uses hole_to_hole | 0.50 mm hole-to-hole | **FIX** along with rule 6 |
| 17 | **Via-in-pad** | **102 plane-stitch vias placed AT-PAD center** | **NOT ALLOWED in JLC standard process** (wicks solder unless via-in-pad / resin-plug + cap process is explicitly ordered, extra cost) | **FIX (BIG)** — move all at-pad vias to fanout stubs |

## 3. The big findings — by priority

### 3.1 Via-in-pad (rule 17) — every at-pad plane stitch must move

Master's correction (2026-05-21): "ALL plane-stitch vias must sit on short stubs OUTSIDE component pads — standard fanout, standard process. Do NOT place vias in pads."

Current state: of the 102 plane-stitch vias placed by `run_stitch_r1_amended.py`, **~69 were placed at-pad** (no stub), 33 used a short stub (≤1 mm). The 69 at-pad placements all need to convert to short-stub.

This is the same fix as the 28 vision-loop residuals — every plane-net pad gets a SHORT STUB to a via in clear space adjacent to the pad. No via inside a SMD pad.

### 3.2 Annular ring (rules 4, 5) — every 0.40 mm via needs resizing

0.40 mm outer + 0.30 mm drill = 0.05 mm radial annular. JLC minimum is 0.13 mm. Two clean fixes:

- **Option A**: Resize to 0.56 mm outer + 0.30 mm drill (annular 0.13 mm). Same drill, larger pad.
- **Option B**: Resize to 0.46 mm outer + 0.20 mm drill (annular 0.13 mm). Smaller drill + smaller pad → smaller via footprint.

**Recommend Option B** — smaller via is better for dense plane stitching, JLC standard now supports 0.20 mm drill.

Action: change `min_via_diameter` to 0.46 mm, `min_through_hole_diameter` to 0.20 mm, `min_via_annular_width` to 0.13 mm. Resize all 172 vias (102 plane stitches + 70 signal vias from Freerouting) accordingly. The Freerouting signal vias at 0.60/0.30 already meet 0.15 mm annular — they don't need resizing. Only the 102 stitch vias (0.40/0.30) need resizing.

### 3.3 Hole-to-hole (rule 6) — 4 pairs under U3 IMU

Already identified in the via-pair audit. Need:
- Tighten project rule from 0.25 → 0.50 mm
- Zigzag the 4 decoupling-cap stitches near U3 (X=68.675/69.325/69.975/70.590, Y=39.85/41.45) to break the 0.65 mm pitch colinear arrangement

### 3.4 Silkscreen + mask (rules 11-14)

Currently disabled (0.00 mm). Need:
- silk-to-pad: 0.15 mm
- mask-to-copper: 0.10 mm
- silk line width: 0.15 mm

These are likely to surface several minor violations in the routed-board (silkscreen text near pads, etc.) — these are typically auto-handled by KiCad during gerber export with `--include-border-title` etc. but should be explicitly enforced.

### 3.5 Custom-DRC rules

The community `jlcpcb.kicad_dru` adds custom rules beyond what `.kicad_pro` covers:
- via-to-track hole_clearance: 0.254 mm
- PTH-to-track hole_clearance: 0.33 mm
- NPTH-to-track hole_clearance: 0.254 mm
- pad-to-track clearance: 0.20 mm
- hole-to-hole same-net: 0.254 mm

These need to be loaded as a custom-rules file in KiCad (Project menu → Custom Rules).

## 4. Stackup confirmation

JLC06161H is confirmed current per JLCPCB's controlled-impedance stackup page (`https://jlcpcb.com/impedance`). Our chosen prepreg variant **JLC06161H-7628** (L1↔L2 prepreg = 0.21 mm) is one of the documented 6-layer impedance-controlled stackups (per `docs/CONTROLLED_IMPEDANCE.md` §1.1).

Confirmed match:
- Board thickness: 1.6 mm ✓ JLC standard
- Layer count: 6 ✓ JLC standard offering
- Outer copper: 1 oz ✓ JLC standard
- Inner copper: 0.5 oz ✓ JLC standard
- Prepreg: 7628 ✓ JLC offers this prepreg

## 5. Controlled-impedance ordering

USB 2.0 differential pair targets Z_diff = 94.4 Ω (per `docs/CONTROLLED_IMPEDANCE.md` §2.4).

**Two options at fab time** (Sai's call):

- **(I1) Order JLCPCB's controlled-impedance service** for the USB pair. JLC's impedance calculator (`https://jlcpcb.com/impedance`) shows our stackup + W/S; they manufacture to ±10% impedance tolerance, with fab impedance coupon. Adds ~$10-30 to the order. Best for HS USB 480 Mbps.
- **(I2) Rely on analytical design + Phase 9 bench TDR** (the current plan per `docs/PHASE7A_FREEZE_PROCEDURE.md`). Standard PCB process; we measure Z_diff at bench and accept slightly wider impedance distribution.

**Recommendation for fab-ready freeze**: (I2). USB 2.0 enumeration is robust to ±15% impedance; our analytical design is in-spec; Phase 9 bench verifies. Save the impedance-control surcharge for v1.x if drop-outs occur.

## 6. Action plan (what gets fixed before vision loop)

1. **Bind custom DRC file**: load `jlcpcb.kicad_dru` into the project (Custom Rules menu in KiCad GUI; OR add reference to `.kicad_pro` `text_variables`/`design_rules` section).
2. **Tighten project rules** (`novapcb-layout-v2.kicad_pro` `board.design_settings.rules`):
   - `min_hole_to_hole`: 0.25 → 0.50
   - `min_via_diameter`: 0.40 → 0.46
   - `min_via_annular_width`: 0.05 → 0.13
   - `min_through_hole_diameter`: 0.30 → 0.20 (relaxed to JLC standard so 0.20-drill vias are allowed)
   - `min_silk_clearance`: 0 → 0.15
   - `solder_mask_to_copper_clearance`: 0 → 0.10
3. **Resize all 102 plane-stitch vias** from 0.40/0.30 to 0.46/0.20 (a script: iterate plane-net vias, update Width()/Drill()).
4. **Move all at-pad vias to short stubs** outside the SMD pad. New constraint: NO via touching a SMD pad's copper. This is a re-execution of the stitcher with `via-not-in-pad` enforced.
5. **Re-position the 4 U3-area cap stitches** to break the 0.65 mm colinear pattern (zigzag to opposite ends of adjacent caps).
6. **Re-run DRC** with the corrected ruleset + custom rules file. Expect new violations from the silk/mask rules + any remaining at-pad vias that resist relocation.
7. **Then resume the 28-via vision loop** with corrected ruleset as the verdict.

## 7. Phase 7a gate update

Add to `docs/PHASE7A_FREEZE_PROCEDURE.md` §1.4 (DFM):
- DRC must pass with both the project rules AND the `jlcpcb.kicad_dru` custom rules file loaded
- 0 via-in-pad findings
- All vias at 0.46/0.20 (or larger via with 0.20 drill OR 0.30+ drill with proportionally larger outer)
- All silk/mask clearance rules enforced

The Phase 7b fab-order step (Sai sign-off) uploads to JLCPCB's online DFM analyzer for the final binding check.
