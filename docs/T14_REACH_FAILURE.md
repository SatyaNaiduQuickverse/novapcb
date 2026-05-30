# T14 piezo buzzer — v1 REACH FAILURE (2026-05-30)

> Sai-directed SOTA T14 (on-board piezo buzzer driven by BUZZER GPIO).
> Placement clean (DRC delta 0) but routing the 24mm trace from BZ1.1 to
> existing BUZZER endpoint cascades 18 violations on F.Cu W-edge path.
> Per master's scope-creep cap watch (4/4 = full): cannot add another
> exception. v1 ships with BUZZER pin routed to GPS connector pin 9
> (J5.9) only; users wanting an audible buzzer use the GPS module's
> on-cable buzzer or solder a wire to J5.9.

## What was attempted

### Part selection
Murata PKMCS0909E (9×9×3mm SMD piezo, ~75 dB SPL @ 10cm @ 4kHz) — chosen as smallest practical piezo with adequate SPL. Smaller than master's CMI-1295S-0585T suggestion to fit dense board.

KiCad footprint `Buzzer_Murata_PKMCS0909E` bbox: **21.63×12.70mm** (includes courtyard + pad extension).

### Placement (clean)

Searched for bbox-clear spots (9 sample points across bbox). Closest to existing BUZZER route endpoint (D9/J5 area at Y=73-75): **(24, 50)** at 23.7mm distance.

Tried initial placement at **(8, 50)** — W edge area, more clearance. DRC delta = 0 (no scope-creep).

### Routing (cascaded)

BZ1.1 pad at (3.65, 50). Nearest existing BUZZER trace endpoint at (19.38, 73.15) = 28mm.

Attempted L-route on F.Cu along W edge: BZ1.1 → (3.65, 73) → (19.38, 73.15). Pre-route obstacle check (footprints + vias only) showed CLEAR at all 9 sample points.

DRC delta after route: 29 → 47 (+18 violations: 8 mask_bridge + 6 clearance + 4 tracks_crossing + 1 shorting). Same trap as T13 re-place attempts — footprint+via scan missed existing PLANE COPPER FILLS at intermediate trace coords.

## Why structural

- Buzzer is a LARGE component (22×14mm bbox) — requires equivalent clear area
- v1 board density: closest bbox-clear spot to BUZZER route is 24mm away
- 24mm F.Cu trace traversal hits zone copper (+3V3, +5V_BEC, GND fills) on the way
- No B.Cu corner with both empty bbox space AND short path to BUZZER trace exists

## Master's cap watch (decisive)

T13 PR #148 added 1 SCOPE-CREEP exception → board-wide count 3 → 4 at cap.
Per master 2026-05-30: "Any of T14/T16/T17 that adds another scope-creep exception BREACHES the cap. For T14 (buzzer): If genuinely cap-breaching: full revert + REACH FAILURE pattern."

The T14 route attempt would add ≥1 scope-creep clearance relax (6 clearance violations from the route). Cap-breach. FULL REVERT per master directive.

## Operational mitigation

BUZZER pin (MCU PA3) is routed to:
- D9 ESD7L5 (clamp diode)
- J5.9 (GPS connector pin 9 per Pixhawk DS-009)

Users wanting audible buzzer:
1. Use a GPS module with on-cable buzzer (Pixhawk standard) — works as-is
2. Solder a wire from J5.9 pad to an external piezo
3. Bring-up: scope-probe at J5.9 or D9.1 pad to verify GPIO output

No flight-critical functionality lost (buzzer is for status announcement,
not safety system).

## v2 path

Pre-allocate buzzer area at Phase 4a (reserve ~25×15mm clear bbox near west
or north edge BEFORE routing dense buses). Or use a smaller MEMS speaker
(some 5×5mm options exist, lower SPL but board-friendly).

## State after revert

- DRC severity-error: **29** (T13 +1 baseline, unchanged from pre-T14)
- audit_unconnected_per_net: PASS, **0 real-latent**
- verify_bom: 0 missing parts, 0 stale rows
- Board-wide scope-creep: **4/4** (T13 contribution), no new T14 additions

## Cross-references

- `docs/T11_REACH_FAILURE.md` + `docs/T12_REACH_FAILURE.md` — same density-cascade pattern
- Master 2026-05-30 cap-watch dispatch (4/4 cap, T14 must DRC-delta-0)
- `feedback_dense_pocket_scan_geometry` memory — footprint+via scan misses copper fills
