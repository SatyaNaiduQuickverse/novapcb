# BOM LCSC Sourcing — 8 TBD Items

**Purpose:** Close the 8 `LCSC=TBD` items in `bom/novapcb-bom.csv` with concrete LCSC part numbers Sai can paste into the JLCPCB BOM at order time.
**Date:** 2026-05-30
**Sources:** jlcpcb.com (parts library + JLC Basic CSV at github.com/josemariaaraujo/JLCPCB-Basic-Parts), lcsc.com.
**Method:** WebFetch + WebSearch against JLC partdetail pages and LCSC product pages. Each item lists LCSC C-number, JLC Basic/Extended tier, 1pc price, stock, datasheet, and risk.

> **Sai-action:** at JLCPCB BOM upload time, paste the `LCSC_Part` column values below into the corresponding rows of `bom/novapcb-bom.csv`. This report does NOT edit the BOM file — see "BOM CSV row changes" section for exact text diff to apply.

---

## 1. Q5 — AO3400A (IMU heater FET driver)

- **LCSC:** `C20917`
- **JLC tier:** **Basic** (no setup fee) — high-volume JLC house-stocked part
- **Price (1pc):** $0.0825 ($0.0669 @ 50+)
- **Stock:** 1,557,357 in stock (huge)
- **Manufacturer / MPN:** Alpha & Omega Semicon / `AO3400A` (SOT-23)
- **Datasheet:** https://datasheet.lcsc.com/lcsc/1811081213_Alpha-&-Omega-Semicon-AO3400A_C20917.pdf
- **Risk:** None. Industry-standard 30V N-ch, 5.7A, RDS(on) ≤ 32 mΩ @ Vgs=4.5V; deep stock; matches BOM footprint `SOT-23`.

---

## 2. L1 — 2.2 µH XAL4020 (TPS62177 buck inductor)

- **LCSC:** `C3151182`
- **JLC tier:** **Extended** (~$3 setup fee; not in JLC Basic CSV)
- **Price (1pc):** $1.3425 (LCSC) / Coilcraft list ~$1.5–$1.6
- **Stock:** 2,948 at LCSC (adequate for v1)
- **Manufacturer / MPN:** Coilcraft / `XAL4020-222MEC`
- **Spec match:** 2.2 µH, 5.5 A Isat, 35.2 mΩ DCR, shielded composite — meets all gates (≥2A, ≥2.2µH, ≥3.5A sat, ≤30mΩ DCR was target — **DCR 35.2mΩ slightly exceeds target**, see risk)
- **Datasheet:** https://www.coilcraft.com/getmedia/6adcb47d-8b55-416c-976e-1e22e0d2848c/xal4000.pdf
- **Risk (medium):** DCR is 35.2 mΩ (target was ≤30 mΩ). At Iout=0.5A typical the I²R loss is only ~9 mW — negligible thermally vs the TPS62177's own losses. **Accept as-is for v1.** No drop-in pin-compatible part hits both ≤30 mΩ DCR and ≥5 A sat in the 4×4×2 mm form factor. The earlier sim run (Phase 4d, Option B) used XAL4020-222 — keeping it preserves sim provenance. Alt = Würth `744373240022` (similar) if XAL4020-222 stock drops; would re-trigger a sourcing search.
- **Sourcing risk note:** JLC stocks the lower-current variant `XAL4020-221MEC` (220 nH, C19191670) more deeply (Extended, 129 in stock). DO NOT substitute — that's 10× lower inductance and will destabilize the buck. Order the `-222MEC` (C3151182) explicitly.

---

## 3. R45 — 120 Ω 0603 1% (CAN termination)

- **LCSC:** `C22787`
- **JLC tier:** **Basic** (confirmed in JLC Basic CSV)
- **Price (1pc):** ~$0.0015
- **Stock:** millions (Basic — always in stock)
- **Manufacturer / MPN:** UNI-ROYAL / `0603WAF1200T5E`
- **Spec match:** 120 Ω, 0603, ±1%, 1/10 W, 75 V
- **Datasheet:** https://datasheet.lcsc.com/lcsc/UNI-ROYAL-Uniroyal-Elec-0603WAF1200T5E_C22787.pdf
- **Risk:** None. CAN bus standard termination value; Basic part with deep stock.

---

## 4. R46 — 0 Ω 0603 jumper

- **LCSC:** `C21189`
- **JLC tier:** **Basic** (confirmed in JLC Basic CSV)
- **Price (1pc):** $0.0015
- **Stock:** 7,365,475 (massive)
- **Manufacturer / MPN:** UNI-ROYAL / `0603WAF0000T5E`
- **Spec match:** 0 Ω, 0603, 100 mW, 75 V (jumper-grade)
- **Datasheet:** https://datasheet.lcsc.com/lcsc/UNI-ROYAL-Uniroyal-Elec-0603WAF0000T5E_C21189.pdf
- **Risk:** None. Distinct from C17168 (0R 0402, already in BOM as R1/R2).

---

## 5. R47 — 562 kΩ 0402 1% (buck FB divider top)

- **LCSC:** `C4294005` (Yageo `AA0402FR-07562KL`)
- **JLC tier:** **Extended** (not in JLC Basic CSV — 562K is not E24, only E96)
- **Price (1pc):** $0.0066
- **Stock:** **OUT OF STOCK at LCSC as of 2026-05-30** — RISK FLAG
- **Manufacturer / MPN:** YAGEO / `AA0402FR-07562KL` (62.5 mW, ±1%, ±150 ppm/°C)
- **Datasheet:** https://www.lcsc.com/datasheet/C4294005.pdf
- **Risk (HIGH — sourcing):** Out of stock at LCSC. Sai must verify availability at JLCPCB order time, otherwise substitute. **Acceptable substitutes** (all Extended, search JLCPCB catalog by value at order time):
  - Yageo `RC0402FR-07562KL` — same 562K 0402 ±1%, RC-series (popular variant); search C-number at order time.
  - Uni-Royal `0402WGF5623TCE` — Uniroyal house equivalent (no confirmed C-number found in catalog search; may not exist as a JLC-stocked SKU).
  - **Divider-math fallback:** if 562K is unobtainable, use 560K (E24, much more common) + verify Vout shift. With Rbot=180K → Vout = 0.8 × (1 + 560/180) = 3.289V vs nominal 3.3V (−0.34% — acceptable). 560K 0402 1% candidates: search `C25812` or Yageo `RC0402FR-07560KL`.

---

## 6. R48 — 180 kΩ 0402 1% (buck FB divider bottom)

- **LCSC:** `C25099` *(NOT CONFIRMED — Yageo `RC0402FR-07180KL` exists per Yageo catalog but exact C-number not surfaced in catalog search; pattern-derived only)*
- **JLC tier:** **Extended** (not in JLC Basic CSV — 180K not in JLC Basic 0402 set)
- **Price (1pc):** ~$0.0010–$0.005 (typical Extended chip-R)
- **Stock:** verify at order time
- **Manufacturer / MPN:** YAGEO `RC0402FR-07180KL` (preferred) OR UNI-ROYAL `0402WGF1803TCE`
- **Datasheet:** https://www.yageo.com/upload/media/product/productsearch/datasheet/rchip/PYu-RC_Group_51_RoHS_L_12.pdf
- **Risk (MEDIUM — sourcing):** C-number not directly confirmed in this session's catalog search. **Sai-action at order time:** open JLCPCB parts search → filter `180KΩ`, `0402`, `±1%` → confirm Basic/Extended + grab the actual C-number. 180K 0402 1% is a very common value — many JLC-stocked SKUs will appear.

---

## 7. J20 — JST-GH SM04B-GHS-TB (4-pin CAN connector)

- **LCSC:** `C189895`
- **JLC tier:** **Extended** (~$3 setup fee — consistent with other JST-GH parts already in BOM at C146386, C5160770)
- **Price (1pc):** $0.5235 (JLC) / $0.5281 (LCSC)
- **Stock:** 8,027 at JLCPCB / 4,710 at LCSC
- **Manufacturer / MPN:** JST Sales America / `SM04B-GHS-TB(LF)(SN)`
- **Spec match:** 1.25 mm pitch, 4P, right-angle, SMT, 1 A, 50 V, −25 to +85 °C — exact match to BOM footprint `JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal`
- **Datasheet:** https://www.jst-mfg.com/product/pdf/eng/eGH.pdf
- **Risk:** None. Same family/manufacturer as J3/J4/J19/J5 (already Extended in BOM). **Setup fee already paid** for JST-GH family — adding J20 to the same Extended fee bucket is incremental zero.

---

## 8. R61 — IMU heater resistor 2512 (PLACEHOLDER)

- **Recommendation: MARK DNP (Do Not Populate) for first-article fab.**
- **Rationale:** Heater is optional for v1 (ArduPilot doesn't require it for arming). Footprint is laid down for future bring-up. DNP saves the assembly-pick fee for an SKU we haven't engineering-validated (heater PWM duty cycle hasn't been simulated end-to-end). When heater is needed in v1.1, populate with a 1k 2512 1% from JLC at that time.
- **If Sai overrides and wants populated for first article:**
  - **Value:** 1 kΩ (mid-range; 11 mW dissipation at 3.3 V — safe, well below 2512's 1 W rating)
  - **LCSC candidate:** `C141975` — Uni-Royal `2512W2F1001T5E` (1 kΩ 2512 1% 1W) — Extended tier, typical stock 50k+, $0.05/pc
  - **Datasheet:** https://datasheet.lcsc.com/lcsc/UNI-ROYAL-Uniroyal-Elec-2512W2F1001T5E_C141975.pdf
  - **Risk:** C-number `C141975` is pattern-derived from Uni-Royal naming; Sai must verify at JLCPCB order time (search `1k 2512 1%`).
- **BOM action:** set `Assembled=no` and `LCSC_Part=DNP` to instruct JLCPCB assembly to skip this position. PCB footprint remains so v1.1 can populate without a re-spin.

---

## BOM CSV row changes

Apply these exact line replacements to `bom/novapcb-bom.csv`. Current rows are lines 46-54 (Item 45 = Q5, Item 47 = L1, Items 49-54 = R45/R46/R47/R48/J20/R61). Header columns: `Item,RefDes,Qty,Value,Footprint,MPN,Manufacturer,LCSC_Part,JLCPCB_Type,Datasheet_URL,Last_Checked,Alt_Part,Assembled,Notes`.

### Q5 (line 46)
**FROM:**
```
46,Q5,1,AO3400A,Package_TO_SOT_SMD:SOT-23,AO3400A,Alpha & Omega,TBD,TBD-confirm,,2026-05-26,,yes,"SAI-SOURCE: common N-ch FET, no LCSC in design"
```
**TO:**
```
46,Q5,1,AO3400A,Package_TO_SOT_SMD:SOT-23,AO3400A,Alpha & Omega,C20917,Basic,https://datasheet.lcsc.com/lcsc/1811081213_Alpha-&-Omega-Semicon-AO3400A_C20917.pdf,2026-05-30,Si2302CDS / DMN2400U,yes,IMU heater FET driver; SOT-23 N-ch 30V 5.7A
```

### L1 (line 47)
**FROM:**
```
47,L1,1,2.2uH XAL4020,Inductor_SMD:L_Coilcraft_XAL4020,2.2uH XAL4020,Coilcraft,TBD,TBD-confirm,,2026-05-26,,yes,SAI-SOURCE: buck inductor (Option B)
```
**TO:**
```
47,L1,1,2.2uH XAL4020,Inductor_SMD:L_Coilcraft_XAL4020,XAL4020-222MEC,Coilcraft,C3151182,Extended,https://www.coilcraft.com/getmedia/6adcb47d-8b55-416c-976e-1e22e0d2848c/xal4000.pdf,2026-05-30,Wuerth 744373240022 (alt if stock drops); DO NOT sub XAL4020-221MEC (220nH wrong),yes,TPS62177 buck inductor 2.2uH/5.5A/35.2mOhm shielded; DCR 35.2mOhm > 30mOhm target — accepted (loss ~9mW)
```

### R45 (line 49)
**FROM:**
```
49,R45,1,120R / 0603,Resistor_SMD:R_0603_1608Metric,120R / 0603,,TBD,TBD-confirm,,2026-05-26,,yes,SAI-SOURCE: CAN termination (verify 1%)
```
**TO:**
```
49,R45,1,120R / 0603,Resistor_SMD:R_0603_1608Metric,0603WAF1200T5E,UNI-ROYAL,C22787,Basic,https://datasheet.lcsc.com/lcsc/UNI-ROYAL-Uniroyal-Elec-0603WAF1200T5E_C22787.pdf,2026-05-30,Yageo RC0603FR-07120RL,yes,CAN bus termination 120R 1%
```

### R46 (line 50)
**FROM:**
```
50,R46,1,0R / 0603,Resistor_SMD:R_0603_1608Metric,0R / 0603,,TBD,TBD-confirm,,2026-05-26,,yes,SAI-SOURCE: distinct from 0R-0402 line
```
**TO:**
```
50,R46,1,0R / 0603,Resistor_SMD:R_0603_1608Metric,0603WAF0000T5E,UNI-ROYAL,C21189,Basic,https://datasheet.lcsc.com/lcsc/UNI-ROYAL-Uniroyal-Elec-0603WAF0000T5E_C21189.pdf,2026-05-30,Yageo RC0603JR-070RL,yes,Zero-ohm jumper 0603 (distinct from R1/R2 0402)
```

### R47 (line 51)
**FROM:**
```
51,R47,1,562k / 0402,Resistor_SMD:R_0402_1005Metric,562k / 0402,,TBD,TBD-confirm,,2026-05-26,,yes,SAI-SOURCE: buck FB divider 1% (Option B)
```
**TO:**
```
51,R47,1,562k / 0402,Resistor_SMD:R_0402_1005Metric,AA0402FR-07562KL,YAGEO,C4294005,Extended,https://www.lcsc.com/datasheet/C4294005.pdf,2026-05-30,560K 0402 1% if 562K out-of-stock (Vout -0.34% only — math in BOM_LCSC_SOURCING.md §5),yes,Buck FB divider top; SOURCING RISK: out-of-stock at LCSC 2026-05-30 — verify at order time
```

### R48 (line 52)
**FROM:**
```
52,R48,1,180k / 0402,Resistor_SMD:R_0402_1005Metric,180k / 0402,,TBD,TBD-confirm,,2026-05-26,,yes,SAI-SOURCE: buck FB divider 1% (Option B)
```
**TO:**
```
52,R48,1,180k / 0402,Resistor_SMD:R_0402_1005Metric,RC0402FR-07180KL,YAGEO,VERIFY-AT-ORDER,Extended,https://www.yageo.com/upload/media/product/productsearch/datasheet/rchip/PYu-RC_Group_51_RoHS_L_12.pdf,2026-05-30,Uni-Royal 0402WGF1803TCE,yes,Buck FB divider bottom; C-number not confirmed — Sai search JLCPCB at order time (180K 0402 1%)
```

### J20 (line 53)
**FROM:**
```
53,J20,1,JST-GH SM04B-GHS-TB (CAN),Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal,JST-GH SM04B-GHS-TB (CAN),JST,TBD,TBD-confirm,,2026-05-26,,yes,SAI-SOURCE: CAN connector 4P
```
**TO:**
```
53,J20,1,JST-GH SM04B-GHS-TB (CAN),Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal,SM04B-GHS-TB(LF)(SN),JST,C189895,Extended,https://www.jst-mfg.com/product/pdf/eng/eGH.pdf,2026-05-30,no-MP variant DOES NOT EXIST (same as J3/J4/J19),yes,CAN bus 4P; same Extended family as J3/J4/J19/J5 — incremental zero setup fee
```

### R61 (line 54)
**FROM:**
```
54,R61,1,TBD_SIM_OUT (PLACEHOLDER),Resistor_SMD:R_2512_6332Metric,TBD_SIM_OUT (PLACEHOLDER),,TBD,TBD-confirm,,2026-05-26,,yes,PLACEHOLDER — value unresolved (sim output R); RESOLVE or mark DNP before fab
```
**TO (recommended — DNP):**
```
54,R61,1,DNP (IMU heater — defer to v1.1),Resistor_SMD:R_2512_6332Metric,DNP,,DNP,DNP,,2026-05-30,1k 2512 1% (C141975 Uni-Royal 2512W2F1001T5E) if populated,no,IMU heater optional in v1; DNP for first article — footprint preserved for v1.1 populate
```

---

## Summary table for Sai

| # | RefDes | LCSC | JLC tier | 1pc price | Stock | Risk |
|---|---|---|---|---|---|---|
| 1 | Q5 | C20917 | **Basic** | $0.0825 | 1.5M+ | none |
| 2 | L1 | C3151182 | Extended | $1.34 | 2,948 | DCR 35mΩ > 30mΩ target (accepted) |
| 3 | R45 | C22787 | **Basic** | $0.0015 | millions | none |
| 4 | R46 | C21189 | **Basic** | $0.0015 | 7.4M | none |
| 5 | R47 | C4294005 | Extended | $0.0066 | **OUT OF STOCK** | **HIGH — verify or sub 560K** |
| 6 | R48 | VERIFY (Yageo RC0402FR-07180KL) | Extended | ~$0.003 | TBD | C-number not confirmed in catalog |
| 7 | J20 | C189895 | Extended | $0.52 | 8,027 | none (same family already paid) |
| 8 | R61 | DNP | — | $0 | — | recommend DNP for first article |

**Tier counts:**
- **Basic (no setup fee):** 3 items — Q5, R45, R46
- **Extended (~$3 each setup fee):** 4 items — L1, R47, R48, J20
- **DNP:** 1 item — R61

**Estimated Extended setup fees:** 4 × $3 = **$12 added at order time** (note: J20 stacks onto the existing JST-GH Extended fee already paid for J3/J4/J19/J5, so the *incremental* Extended fee may be only **3 × $3 = $9** depending on JLC's per-MPN policy — JLC charges per unique Extended part-MPN, not per refdes).

**Sai-actions before fab order:**
1. **R47 (C4294005):** verify stock at JLCPCB cart time. If 0 stock, substitute 560K 0402 1% (find C-number then) — Vout shifts only −0.34%.
2. **R48:** confirm `RC0402FR-07180KL` C-number via JLCPCB component search (very common value, multiple candidates).
3. **R61:** confirm DNP decision (recommended) vs populate 1k 2512.
4. **L1:** explicitly order `XAL4020-222MEC` C3151182 — DO NOT let auto-match substitute the 220nH `-221MEC`.
