# Vision-Assisted Routing Protocol

Used when headless scripted/enumeration routing is genuinely stuck in a congested region and a visual judgment of free space would unblock it. Roles: master = eyes + strategy; worker = hands + coordinate data + DRC.

1. **Vision proposes, data disposes** — a render shows ROUGHLY where free space is; it does NOT give precise coordinates. Every route master proposes is cross-checked against the actual .kicad_pcb coordinate data (the "string check"). Vision = strategy; coordinate data = precision. Never route on a pixel-estimate alone.
2. **DRC is the hard verdict** — every proposed route is laid by the worker and DRC-checked. 0 errors, or master misjudged → re-look.
3. **The loop** — worker renders the TARGETED region (good zoom, modest resolution) + supplies a coordinate data sheet (pads/vias/tracks/obstacles in the region, as text) → master views + proposes a route as coordinates anchored to that data → worker lays it + DRC + re-renders → master verifies → next.
4. **Context discipline** — targeted SMALL renders, not full-board images; view → extract the decision as text → move on; do not let board images accumulate.
5. **Self-sureness** — if a render is ambiguous, get a clearer/zoomed render or more coordinate data; never guess. A misread cascades into wrong decisions.
6. **Honest caveat** — vision finds paths a blind script missed; it does NOT give push-and-shove (reshaping existing routes).
