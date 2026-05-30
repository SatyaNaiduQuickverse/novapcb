# JLCPCB Order Guide — Nova FC v1 (6L + SMT + Via-in-Pad)

> Click-by-click guide for ordering the Nova FC PCB + SMT assembly at JLCPCB.
> Tailored to v1 (6-layer, ENIG, 9 VIP pads, 5-board first article).
> Last revised: 2026-05-29. Sources cited inline.

---

## 0. Before you start

Have these files ready in `hardware/exports/`:

| File | Tool | Notes |
|---|---|---|
| `novapcb_v1_gerbers.zip` | KiCad → Plot → Gerber + Drill | one ZIP containing all layers + drill |
| `novapcb_v1_BOM.csv` | KiCad → Tools → BOM (or `scripts/export.sh`) | columns: `Comment, Designator, Footprint, LCSC Part # (JLCPCB Part #)` |
| `novapcb_v1_CPL.csv` | KiCad → File → Fabrication → PnP | columns: `Designator, Mid X, Mid Y, Layer, Rotation` (mm, T/B) |

BOM/CPL prep rules (JLCPCB): consistent units (mm), use `T`/`B` for layer, refdes case-sensitive match between BOM and CPL, max 200 designators per BOM line, no duplicate designators. See [BOM/CPL preparation](https://jlcpcb.com/help/article/advice-for-bom-and-cpl-files-preparation).

---

## 1. Upload + PCB spec page

1. Go to **jlcpcb.com** → click **"Order Now"** (top-right).
2. Click **"Add gerber file"** → upload `novapcb_v1_gerbers.zip`. Wait for the preview to render (both sides + drill).
3. The PCB spec form appears below the preview. Set these fields **in order top-to-bottom**:

| Field | Value for Nova FC v1 | Why |
|---|---|---|
| Base Material | **FR-4** | default |
| Layers | **6** | DECISIONS.md #8 |
| Dimensions | auto-detected (~36 × 36 mm) | confirm matches `kicad-cli` board outline |
| PCB Qty | **5** | first article |
| Product Type | **Industrial/Consumer electronics** | default |
| Different Design | 1 | one design in panel |
| Delivery Format | **Single PCB** | not panelized |
| PCB Thickness | **1.6 mm** | most common; matches stackup sims |
| PCB Color | **Green** | default; cheapest, fastest |
| Silkscreen | White | default |
| Surface Finish | **ENIG** (sub-option **ENIG 1U"**) | required for fine-pitch LGA/QFN (LSM6DSV16X, DPS310, STM32H743 LQFP-100). HASL is uneven and flunks LGA pads. JLC currently runs **free ENIG promo on 6-layer** (see [6-Layer PCB](https://jlcpcb.com/6-layer-pcb)) |
| Outer Copper Weight | **1 oz** | default |
| Inner Copper Weight | **0.5 oz** | matches CONTROLLED_IMPEDANCE.md sim |
| Via Covering | **POFV (Plated Over Filled Via)** — see §2 below | for the 9 VIP pads |
| Min Via Hole Size/Diameter | **0.25 mm / 0.45 mm** | our smallest via |
| Board Outline Tolerance | ±0.2 mm | default |
| Confirm Production File | **Yes** | catches Gerber issues before fab |

4. Click **"Show Advanced Options"** to expose:

| Field | Value | Why |
|---|---|---|
| Min Track/Spacing | **5/5 mil** (0.127/0.127 mm) | our DRU is 0.10/0.09 — JLC's 4/4 mil tier costs extra. Confirm DRC clean at 5/5 before assuming we need finer. If 4/4 is required (likely for STM32 fanout), select **4/4 mil** |
| Castellated Holes | No | |
| Edge Plating | No | |
| Impedance Control | **No** for first article (matches stackup default); revisit v1.1 if USB Z drift shows | CONTROLLED_IMPEDANCE.md uses JLC's free standard 6-layer stackup |
| Stackup | **JLC06161H-3313** (default for 6L 1.6mm) | what the impedance sims target |

---

## 2. Via-in-Pad (POFV) — the exact selection

**Goal:** IPC-4761 Type VII equivalent (epoxy-filled + copper-capped/plated-over) on the 9 VIP pads under U1 (STM32H743), U7..U9 (IMUs), U2 (TPS62177).

**JLCPCB nomenclature:** the option is now called **"POFV"** (Plated Over Filled Via). Sits in the **Via Covering** dropdown on the main order page. The five options are: *Tented / Untented / Plugged / Epoxy-Filled & Capped / Copper-Paste-Filled & Capped* — see [Via Covering article](https://jlcpcb.com/help/article/pcb-via-covering).

**Pick:** **"Epoxy-Filled & Capped"** (= POFV). This is the standard VIP process — non-conductive epoxy plug, surface-leveled, then copper-plated over so the pad is flat. Matches IPC-4761 Type VII.

**Cost:** **FREE** on **6–20 layer boards** since the 2025 POFV upgrade — applies to both sample and batch orders. See [Free Via-in-Pad on 6-20 Layer PCBs](https://jlcpcb.com/news/free-via-in-pad-6-20-layer-pcbs-pofv). Qualifying via hole size: **0.2–0.5 mm** (our 0.25 mm fits).

**No "which vias" callout needed for POFV at 6L+** — all vias get the treatment. If JLC asks for a note in the order remarks, paste: *"VIP pads under U1/U2/U7/U8/U9; treat per POFV standard."*

---

## 3. SMT Assembly section

Scroll past the PCB spec to the **"PCB Assembly"** toggle.

1. **PCB Assembly: ON**
2. **Assembly Side:** **Both Sides** (B.Cu has J2 microSD, U4 DPS310, decoupling caps)
3. **PCBA Qty:** **5** (match PCB qty)
4. **Tooling holes:** **Added by JLC** (saves us adding panel rails)
5. **Confirm Parts Placement:** **Yes** (gives us a preview before fab)
6. **Bake components:** No
7. **Conformal Coating:** No (v1; revisit for outdoor use)

Click **"NEXT"**. Skip the stencil page (JLC includes the stencil free for in-house assembly).

---

## 4. BOM + CPL upload page

1. **"Add BOM File"** → `novapcb_v1_BOM.csv`
2. **"Add CPL File"** → `novapcb_v1_CPL.csv`
3. Click **"Process BOM & CPL"**. The parser shows a per-line table with `Designator | Qty | MPN | LCSC Part # | Type (Basic/Extended) | Stock | Price`.
4. Resolve any **red rows** (unmatched MPN or out of stock). Substitute from JLC's parts library — prefer **Basic** parts (no $3 setup fee each).
5. **DNP (Do Not Populate):** mark R61 as DNP via the trash-can icon (per task #60).
6. Click **"NEXT"** → component placement preview opens. Verify rotations for: LSM6DSV16X (pin-1 dot), DPS310, STM32H743 LQFP-100 corner, all IMUs (X axis = board +X). Use the rotation tool inline.

---

## 5. Quote review + checkout

Final page shows the line-item quote. **Verify in this order:**

- [ ] PCB: 6-layer, 1.6 mm, ENIG, Green, 5 pcs
- [ ] Via Covering: **POFV / Epoxy-Filled & Capped** ($0)
- [ ] Min track/spacing matches what DRC passes on (4/4 or 5/5)
- [ ] Confirm Production File: Yes
- [ ] Assembly: 5 pcs, **Both Sides**
- [ ] All BOM lines green (in stock, matched MPN)
- [ ] No DNP parts in assembly count
- [ ] CPL parsed without "rotation unknown" warnings
- [ ] Shipping: DHL/FedEx Express (avoid economy for first article — 3–5 days vs 2–3 weeks)
- [ ] Customs declaration: "Prototype PCB, no commercial value beyond declared"

**Expected ballpark for 5-board first article:**

| Line | Cost (USD) |
|---|---|
| 6-layer PCB, 36×36 mm, 5 pcs, ENIG, POFV | ~$10–25 (ENIG promo + free POFV) |
| SMT assembly, both sides, ~80 placements × 5 | ~$30–60 (setup) + ~$15–40 (parts, mostly Basic) |
| Extended parts setup fee | $3 × N extended parts (aim for 0–3) |
| DHL Express shipping to user region | ~$25–40 |
| **Total** | **~$80–170** |

Wide range because Extended part count and shipping dominate. If quote comes in >$200, recheck: (a) any Extended parts that have a Basic equivalent, (b) shipping tier.

---

## 6. After payment

- JLC emails a production confirmation within ~24 h (parts placement review).
- **Respond to the placement-confirmation email within 24 h** or fab pauses. Master must page Sai if the email arrives outside hours.
- Lead time at writing: PCB ~2 days, assembly ~3–5 days, shipping 3–5 days = **~8–12 days door-to-door**.

---

## Sources

- [JLCPCB Via Covering Options](https://jlcpcb.com/help/article/pcb-via-covering)
- [Free Via-in-Pad on 6-20 Layer PCBs (POFV)](https://jlcpcb.com/news/free-via-in-pad-6-20-layer-pcbs-pofv)
- [JLCPCB 6-Layer PCB pricing + ENIG promo](https://jlcpcb.com/6-layer-pcb)
- [BOM/CPL preparation rules](https://jlcpcb.com/help/article/advice-for-bom-and-cpl-files-preparation)
- [PCB Assembly FAQs](https://jlcpcb.com/help/article/pcb-assembly-faqs)
- [Files Needed for PCB Assembly checklist](https://jlcpcb.com/blog/files-needed-for-pcb-assembly)
- Internal: `docs/DECISIONS.md` (#2 form factor, #8 stackup), `docs/CONTROLLED_IMPEDANCE.md` (stackup target)
