# T20 Step 2 plan verification — master sanity check (2026-06-02)

> Sai mandate: master takes regular updates + supports worker queue.
> Master text-only parse of `.kicad_pcb` at HEAD `a00a85f` to verify
> the 5 blocking SDMMC1 segments cited in `T20_STEP2_PROGRESS.md`
> per-net shift table actually exist at the cited positions.

## Result: ALL 5 SEGMENTS VERIFIED

| Net | Layer | Plan start | Plan end | Actual (closest) | Δ |
|---|---|---|---|---|---|
| SDMMC1_CLK | F.Cu | (54.57, 32.35) | (64.18, 32.35) | matches reverse | 0.01 mm ✓ |
| SDMMC1_D0  | F.Cu | (52.67, 34.00) | (57.68, 34.00) | matches | 0.01 mm ✓ |
| SDMMC1_D1  | F.Cu | (52.67, 33.50) | (57.77, 33.55) | (52.67,33.50)→(57.72,33.50) | 0.11 mm ✓ |
| SDMMC1_D2  | B.Cu | (76.48, 37.66) | (76.48, 48.69) | matches | 0.02 mm ✓ |
| SDMMC1_D3  | B.Cu | (79.18, 39.05) | (69.13, 29.00) | matches | 0.01 mm ✓ |

All segments confirmed within 0.5 mm tolerance.

## Total SDMMC1 segment count

Board has **92 SDMMC1 segments** distributed across the 6 nets (CLK, CMD,
D0, D1, D2, D3). The 5 cited blocking segments are the **specific blockers**
of the USART1 corridor; other segments are elsewhere on the SDMMC1 path
and don't need to move.

## Implication

Worker can execute Step 2 directly from `T20_STEP2_PROGRESS.md` per-net
plan without needing to re-survey. Each shift target is concrete; no
ambiguity.

## Master-only context

This verification is text-only (regex on the .kicad_pcb file). Master
has no pcbnew API on novaedge1, but for `(segment ...)` block parsing
the text is unambiguous. The check doesn't validate routing geometry —
just that the cited start/end XY exist as a real segment on the right
layer + net.

Worker's pcbnew API on novatics64 is still authoritative for the actual
shift operation + DRC re-check.
