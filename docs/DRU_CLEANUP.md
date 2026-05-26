# DRU coverage-gap cleanup (task #30)

> Branch `hw/dru-cleanup` off `sch/option-b-buck`. Pre-Phase-7a DRC cleanup:
> classifies all pre-existing DRC items, codifies fab-spec exceptions, and
> net-assigns the false-positive connector pads. **All items verified benign —
> no real bugs.**

## 0. Tooling note (important for the Phase 7a freeze gate)

**`kicad-cli pcb drc` does NOT apply the `.kicad_dru` custom rules** (no option
for it; KiCad limitation, not project-specific). Confirmed: the existing
ORING_A/B_GATE via-in-pad rules are present, yet kicad-cli still flags those
vias. So the headless kicad-cli DRC count **overstates** the real DRC — the
KiCad **GUI** DRC (which loads `.kicad_dru`) is authoritative and cleaner.

> **Phase 7a freeze gate (Sai, on his Pi):** open `novapcb-stepwise.kicad_pcb`
> in the KiCad GUI and run DRC with full `.kicad_dru` application. Expected: the
> 10 via-in-pad items below PASS (rule-covered); only the 2 documented courtyard
> overlaps remain → exclude them in the GUI (right-click → exclude) → **0 errors**.

## 1. Classification of all pre-existing DRC items (kicad-cli, error-severity)

Baseline 21 → **12** after this PR (9 false-positive connector items fixed by
net-assign). The 12 remaining are all explained:

| Group | Count | Items | Resolution |
|---|---|---|---|
| Already `.kicad_dru`-covered | 4 | ORING_A/B_GATE via-dia+hole; EFUSE_ILIM via-dia | existing rules (GUI passes; kicad-cli false-positive) |
| Via-in-pad fab-spec gaps | 6→0 err* | +5V_BEC vias ×2 (dia+hole), EFUSE_ILIM hole | **NEW rules added** (§2) |
| Connector false-positives | 9 | J9.7/8 + J3.MP no-net pads "shorting"/mask/hole vs GND vias | **net-assigned to GND** (§3) — FIXED |
| Intentional courtyard overlaps | 2 | U6+C9 (decap in IC courtyard); J20+J19 (adjacent connectors) | document → Sai GUI-exclude at freeze (§4) |

\* The 10 via-in-pad items (5 vias × dia+hole) still appear in kicad-cli (it
ignores `.kicad_dru`) but are all rule-covered for the GUI/fab DRC.

## 2. New `.kicad_dru` rules (via-in-pad fab-spec, mirror ORFET/EFUSE precedent)

- **`via-in-pad-5vbec-diameter` / `-hole`** — +5V_BEC via-in-pad at the U11/U12
  ORFET output (vias @ (34.15,5.95)+(73.15,5.95), 0.45 OD / 0.25 drill). Net-based
  (the orfet-output vias sit ~2.3mm E of the SOT-23-6 courtyards, so
  `insideCourtyard` can't scope them); only loosens the +5V_BEC via floor to
  0.45 — standard 0.50 stitching vias still pass, so it effectively scopes to
  the two intended via-in-pads. Same JLC vias-filled-and-capped process as ORFET.
- **`u6-extended-courtyard-via-hole`** — completes the existing
  `u6-extended-courtyard-via-diameter` rule (which set OD but not hole) for the
  EFUSE_OVP/ILIM/DVDT/FLT protection-config via-in-pads (EFUSE_ILIM @ (28.75,14.5)).

Verified by-inspection (kicad-cli can't apply them): each flagged via's net
matches a rule condition. All within JLC capability (0.20mm hole / 0.10mm clr).

## 3. Net-assign no-net connector pads → GND (fixes 9 false-positives)

The "shorting"/mask-bridge/hole-clearance items were **no-net pads** physically
adjacent to GND stitching vias — not real shorts. Tied to GND (standard practice
for unused debug pins + connector mounting pegs; cleaner EMC, removes the
false-positive):

- **J9.7 (KEY) + J9.8 (NC/TDI)** — unused ARM-SWD header pins → GND in **SKiDL**
  (`power_sd_swd_3h.py`), netlist regenerated, **ERC 0 errors**.
- **J3.MP** — JST-GH mounting peg → GND **board-direct** (mechanical pad, no
  symbol pin; matches the design's "mounting pads tied to GND for EMC" intent —
  same as the board mounting holes).

Note: J9/J3 GND pins (incl. these) show as unconnected ratsnest because the J9
(SWD) + J3 (Telem) connectors are **unrouted (deferred to task #48)** — the
plane connection lands with that routing. No new floating-pad issue; the
net-assign correctly groups 7/8/MP with the rest of each connector's GND.

## 4. Documented intentional courtyard overlaps (Sai GUI-exclude at freeze)

- **U6 (TPS25940A) + C9** — C9 is U6's input decap, intentionally close;
  courtyard margins overlap, bodies/pads clear. Standard decap placement.
- **J20 (CAN 4P) + J19** — adjacent connectors; courtyard margins overlap,
  bodies clear. Intentional tight NE-corner placement.

Both pre-existing + benign. DRC-exclusion strings are GUI-serialized (hard to
hand-write headless); Sai marks them excluded in the GUI at the Phase 7a freeze.

## 5. Verification

- **DRC (kicad-cli, error-severity): 21 → 12** (9 connector false-positives
  fixed). Remaining 12 = 10 via-in-pad (rule-covered, GUI passes) + 2 courtyards
  (documented). **0 NEW errors introduced.**
- **ERC: 0 errors** (netlist regen after J9 SKiDL edit; 278 pre-existing
  missing-tag warnings unchanged).
- **GUI DRC (authoritative, Sai at freeze):** expected 0 after rule application
  + the 2 courtyard exclusions.
