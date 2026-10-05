# AKE_DEMO – Sales and purchase cycles for AKE's real customers and vendors

Posted on 05-10-2026 by `tools/demo_ake_cycles.py` for the **first 10 customers (C001–C010) and first 10 vendors
(V001–V010)** of AKE's own BP list. Each document is copied from the previous one, so **Relationship Map**
(right-click → Relationship Map) on any of them shows the whole chain. All stock moves through **U1 WH1**.

- **Sales prices** = AKE's average cost (item master export) + 25 %, rounded to the rupee. Items come from AKE's stock
  loaded on 2026-04-01 (`tools/load_ake_stock.py`); batch items are delivered from batch `OB-260401`.
- **Purchase prices** = AKE's average cost. Batch items are received on batch `GRN-<vendor>-261002`.
- **GST**: Karnataka party → CGST 9 % + SGST 9 %; other states → IGST 18 %; export (C007, Portugal) → IGST 0 %.
- Invoices are left **unpaid** (open) – use them for incoming / outgoing payment training.

## 1. Sales cycle – Sales Quotation → Sales Order → Delivery → A/R Invoice

Dates: quotation 29-09, order 30-09, delivery 03-10, invoice 05-10-2026 (due 04-11).

| Customer | Items | Quotation | Order | Delivery | A/R Invoice | GST | Invoice total (₹) |
|---|---|---|---|---|---|---|---|
| C001 Ajax Engineering Limited | DRUM ASSEMBLY ×2, DRUM ROLLER RING ×4 | SQ2627/5 | SO2627/10 | DN2627/12 | INV2627/10 | CGST 9% + SGST 9% | 346,568.36 |
| C002 Buhler (India) Pvt Ltd | Drum roller mounting bracket ×20, manhole rubber gasket ×100 | SQ2627/6 | SO2627/11 | DN2627/13 | INV2627/11 | CGST 9% + SGST 9% | 36,910.40 |
| C003 Maruthi Enterprises | Grinding wheel 180 mm ×200, flap disc 4.5" ×300 | SQ2627/4 | SO2627/9 | DN2627/11 | INV2627/9 | CGST 9% + SGST 9% | 48,852.00 |
| C004 Wirtgen India Pvt.Ltd | Drum base frame Argo 4000 ×2, support ring A2.0 drum ×4 | SQ2627/7 | SO2627/12 | DN2627/14 | INV2627/12 | IGST 18% | 252,638.00 |
| C005 homission india pvt ltd | Bucket mounting plate ×20, bush-1 ×20 | SQ2627/8 | SO2627/13 | DN2627/15 | INV2627/13 | CGST 9% + SGST 9% | 6,183.20 |
| C006 LARSEN & TOUBRO LTD | TD125 stator frame fab ×1, service cover stator frame ×10 | SQ2627/9 | SO2627/14 | DN2627/16 | INV2627/14 | CGST 9% + SGST 9% | 1,125,278.68 |
| C007 WEG EURO - INDUSTRIA ELECTRICA S.A. | Stator frame fabrication ×2, 5X service cover stator frame ×5 | SQ2627/10 | SO2627/15 | DN2627/17 | INV2627/15 | IGST 0% (export) | 1,009,696.00 |
| C008 WEG Industries | Endshield fixing cylinder ×5, foot-enclosure support ×10 | SQ2627/11 | SO2627/16 | DN2627/18 | INV2627/16 | IGST 18% | 133,446.20 |
| C009 BEML LIMITED | Argo 4300 swivel drum base frame ×2, dish assembly machining ×5 | SQ2627/12 | SO2627/17 | DN2627/19 | INV2627/17 | CGST 9% + SGST 9% | 236,217.12 |
| C010 NIKHITHA BUILD-TECH PVT.LTD | Leather safety shoe ×20 pairs, safety goggles ×50 | SQ2627/13 | SO2627/18 | DN2627/20 | INV2627/18 | CGST 9% + SGST 9% | 23,777.00 |
| **Total** | | | | | | | **3,219,566.96** |

## 2. Purchase cycle – Purchase Request → Purchase Quotation → Purchase Order → GRPO → A/P Invoice

Dates: request 28-09 (required 02-10), quotation 29-09, order 30-09, GRPO 02-10, invoice 03-10-2026 (due 02-11).
Requester: manager; the request names the vendor on each line.

| Vendor | Items | Request | Quotation | Order | GRPO | A/P Invoice | GST | Invoice total (₹) |
|---|---|---|---|---|---|---|---|---|
| V001 Aaruda Paints & Coatings | Primer Grand Polycoat 200 LTR, enamel deep orange 40 LTR | PR2627/3 | PQ2627/6 | PO2627/6 | GRN2627/8 | PINV2627/9 | CGST 9% + SGST 9% | 99,688.76 |
| V002 Accfin Corporate Suppliers | HP 88A cartridge refill ×10, inspection report book ×20 | PR2627/4 | PQ2627/7 | PO2627/7 | GRN2627/9 | PINV2627/10 | CGST 9% + SGST 9% | 6,728.60 |
| V003 Accident Relief Care (India) Pvt. Ltd. | Full body safety harness ×10, leather apron ×25 | PR2627/5 | PQ2627/8 | PO2627/8 | GRN2627/10 | PINV2627/11 | CGST 9% + SGST 9% | 14,307.50 |
| V004 Accurate Bearing Centre | SKF ball bearing 6312 2Z ×4, 6205ZZ ×20 | PR2627/6 | PQ2627/9 | PO2627/9 | GRN2627/11 | PINV2627/12 | CGST 9% + SGST 9% | 14,367.44 |
| V005 Add Corp | Cable tie 150 mm ×500, insulation tape ×100 | PR2627/7 | PQ2627/10 | PO2627/10 | GRN2627/12 | PINV2627/13 | IGST 18% | 2,761.20 |
| V006 Adrtek India Pvt Ltd | Contactor add-on block Schneider ×20, Siemens ×20 | PR2627/8 | PQ2627/11 | PO2627/11 | GRN2627/13 | PINV2627/14 | CGST 9% + SGST 9% | 5,616.80 |
| V007 Ajax Engineering Pvt. Ltd. | 2-speed switch 25 A ×2, LPG regulator adaptor ×5 | PR2627/9 | PQ2627/12 | PO2627/12 | GRN2627/14 | PINV2627/15 | CGST 9% + SGST 9% | 5,212.65 |
| V008 Alloyage Product | Solid wire ER70S 1.2 mm 500 KG, EM12K 1.6 mm 300 KG | PR2627/10 | PQ2627/13 | PO2627/13 | GRN2627/15 | PINV2627/16 | IGST 18% | 93,243.60 |
| V009 Ambica Trading Corporation | HR cut plate E350 2,000 KG, ERW rect. tube 1,000 KG | PR2627/11 | PQ2627/14 | PO2627/14 | GRN2627/16 | PINV2627/17 | CGST 9% + SGST 9% | 293,442.40 |
| V010 Amco Traders | Nyloc nut M30 ×100, grease nipple M10 ×50 | PR2627/12 | PQ2627/15 | PO2627/15 | GRN2627/17 | PINV2627/18 | CGST 9% + SGST 9% | 10,253.02 |
| **Total** | | | | | | | | **545,621.97** |

## What to show

1. **Copy-to chain:** open a quotation and use *Copy To*; after the next document is added the base document shows
   status *Closed*. All quotations, orders, deliveries, requests, POs and GRPOs above are closed; only the invoices are open.
2. **Stock effect:** Inventory → Inventory Reports → Inventory Audit Report for an item (e.g. CON120082) shows the opening
   receipt on 01-04 and the delivery on 03-10; purchase items (e.g. CON120236) show the GRPO on 02-10.
3. **Batches:** on a delivery of a batch item (e.g. DN for C003) open *Batch Numbers* to see batch OB-260401.
4. **GST:** compare C001 (CGST + SGST), C004 Wirtgen, Maharashtra (IGST) and C007 WEG Euro (export, IGST 0 %).
5. **Open items:** Sales / Purchasing Reports → Open Items List → A/R / A/P invoices lists the 10 + 10 unpaid invoices.

Notes: C008 WEG Industries has no GSTIN in AKE's export (treated as unregistered, IGST). Items in the Tools group have
no HSN yet (B1 refuses GST lines without HSN), so V006 got contactor add-on blocks instead of tools.
