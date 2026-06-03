# Layer-constant root-cause discovery (2026-06-04)

> Worker discovery during +5V orphan stub cleanup at freeze-gate close.
> Informational for v2-inheritance + future-Claude awareness.
> Does NOT affect v1 freeze state (all committed routes verified on correct layers per audit_unconnected_per_net 0 real-latent).

---

## The bug

In the worker's KiCad pcbnew version on novatics64:

| Constant intended | Numeric value used | Actual layer |
|---|---|---|
| `pcbnew.B_Cu` | `31` | **F.Courtyard** (not copper) |
| `pcbnew.B_Cu` | `2` (CORRECT) | **B.Cu** (copper) |

Worker's earlier exploratory routing scripts in the T22 chain (and possibly earlier sub-phases) used `layer=31` thinking it was B.Cu. KiCad silently dropped the resulting `(segment ...)` blocks because they targeted a non-copper layer — they didn't generate DRC errors of "track on non-copper layer", they were simply ignored.

The bug surfaced during +5V orphan cleanup when worker's route attempts to connect the stub at (48.65, 60.49) kept not appearing on B.Cu. Investigation traced to layer constant.

---

## Historical impact (informational only)

The bug **partially explains** several T22 chain outcomes:

| Sub-task | Observed | Likely contributing factor |
|---|---|---|
| T22.1 SD card-detect | +25 DRC cascade revert | Routes on layer=31 (F.Courtyard) crashed with every courtyard; correct layer might have helped but mid-board J2 47+mm trace structural constraint remains |
| T22.5 microSD ESD | +10 DRC placement-only marginal | Same layer-constant issue; 423mm SDMMC1 re-route challenge structural |
| Earlier "B.Cu obstacle-free" scans | Sometimes returned 0 incorrectly | Filtering by layer==31 instead of layer==2 |

**Important:** the bug was *incidental*, not the sole cause of v2-defers. T22.1 (CD) and T22.5 (ESD) v2-defer decisions stand because:
- J2 microSD connector is mid-board (structural placement constraint independent of layer)
- ArduPilot doesn't require SD card-detect
- Industry standard (Raspberry Pi, Matek FCs) omits internal SD ESD
- 423mm SDMMC1 re-route would risk Sim 3 SI regression (currently 97.8% margin)

---

## Why current freeze state is unaffected

`audit_unconnected_per_net` at HEAD `2eb92e2` shows **0 real-latent** after orphan cleanup. This means:
- Every committed `(segment ...)` block in the `.kicad_pcb` is on a valid copper layer
- The bug only affected exploratory routes that were either:
  - Reverted out as part of cascade gates (no commit)
  - Never committed because they didn't appear on B.Cu (KiCad dropped them)
- Cleanup re-applied the +5V residual route with correct `pcbnew.B_Cu` constant, closing the last real-latent

T22.4 ESC TVS land was unaffected — it used a different placement strategy (top-side staggered) that didn't exercise the buggy B.Cu route paths.

---

## v2-inheritance value

For future-Claude rebuilding T22.1/T22.5 in v2:

1. **Always reference `pcbnew.B_Cu` symbolically**, never numeric `31` or `2`. Use:
   ```python
   from pcbnew import F_Cu, B_Cu, In1_Cu, In2_Cu, In3_Cu, In4_Cu
   ```
2. **Verify layer constant on session start** with a small sanity print:
   ```python
   print(f"B_Cu={B_Cu}, F_Cu={F_Cu}")  # expect B_Cu=2, F_Cu=0 in modern KiCad
   ```
3. **B.Cu obstacle scans must filter by `track.GetLayer() == B_Cu`**, not by integer comparison.
4. The structural constraints for T22.1/T22.5 (J2 mid-board, 47+mm trace) likely still wall even with correct layer. Don't pre-assume the layer fix unlocks them.

---

## Master process correction codified

Master will treat any worker "B.Cu obstacle-free" finding with healthy skepticism going forward. Per existing memory `feedback_verify_hwdef_before_authorizing` (2026-05-28), the discipline of verifying source before authorizing applies equally to worker-side toolchain claims.

Future B.Cu scan results should include the layer constant print alongside the scan output, so master can sanity-check the constant in transit.

---

## References

- Worker session message 2026-06-04: orphan cleanup root cause
- `audit_unconnected_per_net` output at HEAD `2eb92e2` (worker side, novatics64)
- `pcbnew` Python API layer constants (KiCad source documentation)
- T22.1/T22.5/T22.4 outcome history: `docs/DECISIONS.md` §15 T22 chain disposition

---

— master, 2026-06-04 (informational, post-freeze-gate)
