# AKE SAP B1 – Daily Updates

Project: AKE Infrastructure – SAP Business One 10 (HANA) training database **AKE_DEMO**, built by Qltc.
Newest day on top. Status: ✅ Completed · 🔄 In progress · ⛔ Blocked / waiting · 📌 Next

---

## 2026-10-03 (Saturday)

### ✅ Completed
| # | Task | Result / where |
|---|---|---|
| 1 | U1 BPs moved onto the normal numbering (user request) | U1C002–U1C005 → C0008–C0011; U1V002–U1V009 → V0011–V0018 (re-created with all details incl. TDS, old codes deleted) – `tools/renumber_bps.py`; U1C001 → C0007 done by user in the client |
| 2 | BP groups by GST place of supply (company state Karnataka) | Customers: Intrastate / Interstate / Export; vendors: Intrastate Vendor / Interstate Vendor / Import Vendor (B1 group names must be unique across types). All 30 BPs regrouped from the bill-to state; old segment groups (incl. default Customers / Suppliers) deleted |
| 3 | Scripts and docs on the new codes | `build_u1_masters.py` (group follows state), `demo_o2c_p2p.py`, `docs/03_O2C_P2P_Demo.md`, `U1_Master_Data.xlsx` |
| 4 | UoMs + UoM groups restructured (user spec) | New UoMs Pairs, Packet, Square Meters/Feet, Centimeters, Inches, Cubic Meters (m3), Grams; renamed KG → KGS, MT → Tonnes. Groups renamed in place (no duplicates): STEEL → **Weight** (+ 1000 G = 1 KG, 1 Tonne = 1000 KG), NOS → **Each** (+ Pair = 2, Packet = 100, Set = 1 NOS), LITER → **Volume** (+ 1 m3 = 1000 LTR), **Length** (+ 100 CM = 1 M, 1 Inch = 0.0254 M, Feet kept); new **Area** (10.7639 SQFT = 1 SQM); Manual is B1's built-in. AGGREGATE and SET deleted after their items moved; pack-size groups CEMENT / ELECTRODE / DISC kept |
| 5 | 18 sample items + 3 BOMs | RM008–RM011, CN004–CN008, BO001–BO003 (new group Bought-out Components), PM001–PM003 (new group Packing Material), SA001 semi-finished, FG004 / FG005 – every item with pricing unit; BOMs SA001 → FG004 and FG005 (per SQM); Standard cost set by revaluation (SA001 750, FG004 2,600, FG005 1,250/SQM) |
| 6 | Existing items on the new groups + valuation rule | 32 items updated (`tools/update_item_uoms.py`): 22 Manual-UoM items moved to Each / Weight (steel bought in Tonnes); FIFO → Moving Average (BAT001, CN001–3, SF002–3); FG-CTRAY-300 / FG-PLAT-HR / FG-PRACK-6M / FG-TANK-5KL → Standard (indicative cost 78 % of sales price). Prices cleared by the group change were restored |
| 7 | 15 items with transactions set **Inactive** (user request) | B1 refused the UoM group / valuation change on them: CN-ELEC-E6013, CN-ENAMEL, CN-GRIND-4, CN-MIG-ER70, CN-PRIMER, PPE-HELMET, PPE-SHOE, RM-PL-0012, RM-PL-0020, RM-ST-A50, RM-ST-MB300, FG-COL-MB300-6M, SA-BASEPL-400, SA-GUSSET-12, SF001 (remark "Old UoM setup"); history kept |
| 8 | Planning method by procurement method (user request) | 13 Make items (FG001–FG005, FG-* , SA001, SA-*) → **MRP**; 69 Buy items already **None**; loader sets this on new items |
| 9 | All 17 **Consumables** items → UoM group Each, inventory / purchase / sales UoM and pricing unit NOS (user request) | Changed from Volume (BAT001, CN005, CN008), Weight (CN006), Area (CN004), Each-Pairs (CN007), Box packs (CN001–CN003) and Manual (5 inactive items); price figures kept, now per NOS |
| 10 | All other items without transactions → Each / NOS everywhere (user request) | 36 items: steel RM002–RM007, RM-PL/RM-SG/RM-ST/RM-TMT (were KGS, bought in Tonnes), RM008–RM011, EL001, PL001–PL002 (Meters/Feet), BO002–BO003, PM001, PM003, PPE-GLOVE-W, SF003, TR002, FG001, FG002, FG005, SRV002; price figures and standard costs kept. Left unchanged (transactions/stock): RM001, CN-LPG, the 15 inactive items |
| 11 | 10 new TDS codes (user list), effective 01-04-2026, eTDS, Invoice, 100 % Net base | P7.5 194J COM 7.5 % · T.75 194C 0.75 % · T1.5 194C 1.5 % · TDS1 194C 1 % · TDS2 194C 2 % · T7.5 194I IND 7.5 % · TD10 194I IND 10 % · TI10 194A 10 % · TJ10 194J COM 10 % · TP10 194J IND 10 % – each on its own AKE "TDS Payable @ x %" ledger; `data/07_tds_codes.json`, `python tools/sl_loader.py --step tds` |

### ⛔ Waiting on user / AKE
- Rename in the SAP client (they have transactions, Service Layer cannot change a BP code): **U1C006 → C0012** ABC Developers and **U1V001 → V0010** Tungabhadra Steel. The demo script and guide already use C0012 / V0010.
- New BPs: choose the group by address – Karnataka → Intrastate, other Indian state → Interstate, outside India → Export / Import Vendor
- Inactive items still hold stock (e.g. RM-PL-0012 486.4 KG, RM-PL-0020 299.8 KG, RM-ST-A50 300 KG, RM-ST-MB300 219.6 KG, FG-COL-MB300-6M 2 Nos, SF001 7 Nos) and sit in the old BOMs FG-COL-MB300-6M, FG-PLAT-HR, FG-CTRAY-300, SA-BASEPL-400, SA-GUSSET-12 – decide: issue / write off the stock, and replace those BOM lines with active items
- Items now counted in NOS: steel prices (₹55–72) and FG001/FG002 standard cost (85 / 82) were per KG, RM008 ₹48 per SQFT, RM011 ₹5,600 per m3 – set real per-piece prices / costs; BOM quantities (e.g. SA001 6.5 × RM003, FG005 1.05 × RM008) now mean NOS
- Consumables now counted in NOS: check the price figures (e.g. CN005 degreaser ₹180, CN006 brazing rod ₹38 were per LTR / Gram) and the BOM quantities SA001 → CN001 0.3 and FG004 → CN005 0.2 (now NOS)
- **T0.1** TDS @ 0.1 % Purchase (and Q01) not created: section **194Q** is missing in B1 and cannot be added via Service Layer – add it in the client (Administration > Setup > Financials > Tax > Section), then re-run `--step tds`
- Swap vendor TDS codes in the client (BP Master Data > Accounting > Tax > WTax Codes; Service Layer cannot remove a BP's WT row): **V0008, V0017 C2 → TDS2**, **V0009 J10 → TJ10**. V0007 / V0018 are individuals (atOthers) and stay on C1 – TDS1 is defined for companies (COM)
- Confirm standard costs (indicative) and the Packet = 100 NOS / Set = 1 NOS conversions

### 📌 Next
1. After the two client renames, re-check the demo documents (Relationship Map) under C0012 / V0010
2. Production demo with the new items: PO for BO001/BO002/RM008–RM010 → GRPO → production orders SA001 → FG004 and FG005 → delivery / invoice in SQFT

---

## 2026-10-02 (Friday)

### ✅ Completed
| # | Task | Result / where |
|---|---|---|
| 1 | Query Manager categories created in AKE_DEMO | OTC (18), PTP (19), PTS (20), FICO (21) – `python tools/build_reports.py --categories` |
| 2 | 28 reports saved into Query Manager | 7 each in OTC / PTP / PTS / FICO – `python tools/build_reports.py --no-test` |
| 3 | U1 (fabrication unit 1) master data | `tools/build_u1_masters.py`, spec in `data/u1_masters/U1_Master_Data.xlsx` |
| 3a | Units of measure + UoM groups | 9 UoMs (Nos, KG, MT, Bag, Meter, Feet, Liter, Box, Set); 9 groups e.g. 1 MT = 1000 KG, 1 Bag = 50 KG, 1 Box = 5 KG electrode / 25 discs |
| 3b | Warehouses | U1WH01 Main, U1WH02 Raw Material Store, U1WH03 Quality, U1WH04 Rejected, U1WH06 Rejected 2 (Scrap), U1WH07 Finished |
| 3c | Item groups | Raw material, Finished Goods, Safety Equipment, Tools & Consumables (new); Consumables (existing, reused) |
| 3d | 27 items | RM001–RM007, EL001–EL003, PL001–PL002, SF001–SF003, CN001–CN003, TR001–TR002, BAT001 (batch), SER001 (serial), SRV001–SRV002 (non-stock), FG001–FG003 (standard cost via revaluation) |
| 3e | Fabrication customers & vendors | Customers U1C001–U1C005; vendors U1V001–U1V009 (U1V008 TDS C2, U1V009 TDS C1) |
| 3f | Full BP details on all 14 U1 BPs (checked in SAP) | Bill-to + ship-to with PIN, state, dummy GSTIN/PAN, payment terms, contact person, mobile, e-mail (.example), BP group (3 customer + 7 vendor groups), control account, price list (customers: Sales, vendors: Purchase) |
| 3g | Same full details on the 15 demo BPs C0001–C0006, V0001–V0009 | All 29 BPs verified in SAP (13 fields each); new BP groups Manufacturing (C0006) and Consultants (V0009); existing GSTINs kept (valid check digits) |
| 3h | Credit limits removed (user request) | Credit limit and commitment limit = 0 on all 29 BPs; removed from loader and Excel |
| 4 | P2P demo – RM001 1,000 KG | PR/26-27/1 → PQ/26-27/1-3 (U1V001 ₹62 / V0001 ₹64 / V0002 ₹63.50) → PO/26-27/3 → GRN/26-27/3 600 KG (validated 1000 / 600 / 400) → PINV/26-27/5 → PAY/26-27/1 ₹25,000 partial → GRN/26-27/4 400 KG → PINV/26-27/6 |
| 5 | O2C demo – ABC Developers (U1C006) | SQ/26-27/2 → SO/26-27/6 → DN/26-27/6 (600 KG partial + 20 Nos full) → SR/26-27/1 return 2 Nos → INV/26-27/5 → RCT/26-27/2 → DN/26-27/7 400 KG → INV/26-27/6 → SCN/26-27/1 50 KG → RCT/26-27/3 |
| 6 | Demo guide + reports | `docs/03_O2C_P2P_Demo.md`, `tools/demo_o2c_p2p.py`; new queries PTP08 Quotation Comparison, PTP09 PO Receipt Status (both tested) |
| 7 | Setup fixes found by the demo | Realized conversion difference accounts (2003-02 / 4006-07); sales/purchase credit accounts on item groups + G/L determination; SF001 made a sales item |
| 8 | Purchase reports (user list) | New PTP10 Open Purchase Requests, PTP11 GRPO Register, PTP12 A/P Credit Memo Register, PTP13 Goods Return Register; already present: PTP08 quotation comparison, PTP01 open PO, PTP09 PO vs GRPO, PTP02 GRPO pending, PTP03 A/P invoice register |
| 9 | Sales reports (user list) | New OTC08 Open Sales Quotations, OTC09 Sales Order Register, OTC10 SO vs Delivery, OTC11 Open Sales Orders – Summary, OTC12 A/R Credit Memo Register; already present: OTC01 quotations, OTC02 delivery pending, OTC04 A/R invoice register |
| 10 | Query Manager now holds 39 reports | OTC 12 · PTP 13 · PTS 7 · FICO 7 – tables/columns of the 9 new ones checked against AKE_DEMO |

### 🔄 In progress
| Task | Status |
|---|---|
| Query Manager reports (28) | Saved; not yet run – Service Layer SQLQueries cannot test them (rejects `\|\|`, CASE, arithmetic, OACT/OWHT), so run each once in the SAP client |
| Crystal Reports print layouts (.rpt) | Continue on SAP server SSO-WINDOWS1 |

### ⛔ Waiting on user / AKE
- SRV001 / SRV002: set Item Class = Service and SAC (996511 / 998873) in the SAP client – Service Layer ignores these fields
- Confirm indicative GST rates / HSN / SAC of the U1 items with AKE's tax team; U1V001 steel TDS 194Q still pending
- Same open items as 2026-10-01 (HANA read-only user, TDS 194Q, USD rate, company address, `manager` password, bank details, Claude Code on SSO-WINDOWS1)

### 📌 Next
1. Walk through `docs/03_O2C_P2P_Demo.md` in the SAP client (Relationship Map per document)
2. Run each of the 39 reports in the SAP client (dates 01-04-2026 to 31-03-2027) and fix any that fail
3. Crystal Tax Invoice layout on the SAP server

---

## 2026-10-01 (Thursday)

### ✅ Completed
| # | Task | Result / where |
|---|---|---|
| 1 | Recommendations: create COA, TDS, tax codes without Service Layer | DTW for COA, manual entry for GST/TDS |
| 2 | Dummy finance setup (sample COA, GST codes, TDS codes) | `data/dummy/` – Excel + DTW CSVs (`tools/build_dummy_setup.py`) |
| 3 | AKE real COA / GST / TDS import files | `data/ake_import/` – DTW CSVs by level + Excel (`tools/build_ake_import.py`) |
| 4 | Secure Service Layer connection to AKE_DEMO | Server certificate pinned (`SL_CA_FILE`), credentials in git-ignored `.env` |
| 5 | Chart of Accounts created in SAP | 598 accounts (506 postable) under the 5 drawers |
| 6 | GST setup | AKE ledgers on 18 CGST/SGST/IGST authorities; new 40% codes `CG+SG@40`, `IGST@40` |
| 7 | TDS setup | Codes C1, C2 (194C), J10 (194J), I10 (194I), A10 (194A) with surcharge/cess/non-compliance rates; FY2025-26 & FY2026-27 |
| 8 | Company location | Bangalore – Peenya, GSTIN 29AAMCA5278K1ZZ, PAN AAMCA5278K |
| 9 | States with GST codes | 10 states (KA 29, TN 33, TS 36, KL 32, MH 27 …) |
| 10 | Customers & vendors | 6 customers + 9 vendors (dummy), TDS on V0007/V0008/V0009 |
| 11 | G/L account determination | 24 company default accounts (FY 2026-27) |
| 12 | Numbering series FY 2026-27 | 25 series incl. GST sub-types GA/GD for invoices & credit notes, default for all users |
| 13 | Master data | 6 warehouses, 9 item groups, 37 items, 18 HSN codes + SAC 998331, 7 resources, 5 BOMs |
| 14 | Demo transactions | Purchase P1–P3, Inventory I1–I3, Production PR1–PR3, Sales S1–S3 (`tools/demo_transactions.py`) |
| 15 | Sales orders + deliveries with multiple items & tax codes | SO/26-27/3 → DN/26-27/3 (CG+SG@18 + @5), SO/26-27/4 → DN/26-27/4 (IGST@18 + @5) |
| 16 | TDS correction | Invoice without TDS reversed by PCN/26-27/1; re-posted PINV/26-27/4 with TDS ₹6,000 |
| 17 | Print formats (PDF) | 15 formats, 34 PDFs – Tax Invoice, Delivery Challan, PO, GRN, Job Card … (`tools/print_docs.py` → `prints/`) |
| 18 | Handover for SAP server session | `docs/02_Handover_SAP_Server.md` |
| 19 | Report pack written | 28 HANA SQL reports in categories OTC / PTP / PTS / FIN – FIN renamed FICO on 02-10 (`tools/build_reports.py`) |
| 20 | Daily update tracker | This file; pushed to GitHub |

### 🔄 In progress
| Task | Status |
|---|---|
| Query Manager reports OTC / PTP / PTS / FICO | SQL written; needs testing on HANA before saving into SAP |
| Crystal Reports print layouts (.rpt) | Option B chosen – continue on SAP server SSO-WINDOWS1 |

### ⛔ Waiting on user / AKE
- HANA read-only DB user in `.env` (`HANA_HOST`, `HANA_PORT`, `HANA_USER`, `HANA_PASSWORD`) – to test the 28 reports
- Add TDS section **194Q** in SAP (Administration → Setup → Financials → Tax → Section) → then TDS code Q01 + vendors V0001/V0002
- Replace demo USD exchange rate 88.00 (01-10-2026) with the real rate
- Fill Company Details address (Administration → Company Details)
- Change the `manager` password (shared in chat) and update `.env`
- AKE bank details for invoice footer; reverse-charge (RCM) usage
- Install Claude Code + project on SSO-WINDOWS1 and check Crystal Reports is installed

### 📌 Next
1. Test and save the 28 reports in Query Manager
2. Crystal Tax Invoice layout on the SAP server, then the other documents
3. A/R invoices for deliveries DN/26-27/3 and DN/26-27/4 (if wanted)
