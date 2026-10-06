# AKE SAP B1 – Daily Updates

Project: AKE Infrastructure – SAP Business One 10 (HANA) training database **AKE_DEMO**, built by Qltc.
Newest day on top. Status: ✅ Completed · 🔄 In progress · ⛔ Blocked / waiting · 📌 Next

---

## 2026-10-06 (Tuesday)

### ✅ Completed
| # | Task | Result / where |
|---|---|---|
| 1 | Fixed Assets module not visible in the B1 client | Enabled by the user: Company Details → Basic Initialization → *Enable Fixed Assets*, then log in again |
| 2 | **Depreciation areas** (user upload `Deprecation Area.csv`) | **Main Books** → **Indirect posting** (I), Posting to G/L, main booking area. **Tax Books** stays Direct posting, Additional Area (B1 can't change the Area Type of an existing area: *1470000059 Field cannot be updated*). Demo area IFRS left alone – `tools/load_depreciation_areas.py` |
| 3 | **Asset classes** (user upload `Assest Classes.csv`) | **22 classes** as in AKE: Unit 1 `U1…` and Unit 2 `U2…` × 11 (Computers, Factory Building, Electrical Fittings, Furniture, Four / Two Wheelers, Office Equipment, P&M, P&M Fixtures, P&M Instruments, Server & Software). Type General, one **Main Books** line each with AKE's account determination (TA-…), depreciation type (…WDV@…%) and useful life (36–360 months). No branch set (AKE_DEMO has no branches; AKE's Branch ID 1 / 3). Demo classes Furnitures / Machine / Motor vehicles untouched – `tools/load_asset_classes.py` |

| 4 | **Direct GRPOs** (no purchase order) for 10 more AKE vendors (user request) | **GRN2627/24–33 = ₹5,02,610.62** (net ₹4,25,941.20 + GST ₹76,669.42), 06-10-2026, into U1 WH1 at AKE's average cost, left open (no A/P invoice). Items fit the vendor: V011 Apex Abrasives (cut-off / grinding wheels, flap discs), V014 Asba (oxygen, argon m3), V015 Aswathi Hardware (HT bolts), V020 Ballista (HP cartridge, mouse), V025 Beekay Steel (MS angle, channel), V027 Berger Paints (epoxy primer, thinner), V029 Bhotika Ispat (HR plate 3 t), V030 Blastline (steel grit, blasting hose), V035 Choudhary Steel (MS flat, beam), V039 Donaldson (compressor filters). GST: IGST for V011 / V030 / V039 (other state), CG+SG for the rest; batch items on GRN-<vendor>-261006 – `tools/demo_direct_grpo.py` |
### ⛔ Waiting on user / AKE
- Tax Books: user asked for Area Type *Posting to G/L*; AKE's file has O (Additional Area). Needs delete + recreate (it is on the 3 demo asset classes) and would post depreciation to G/L twice (Main Books + Tax Books) – confirm before changing
- U1 and U2 asset classes are identical without branches – pick U1… or U2… on the asset master data

### 📌 Next
- Fixed-asset item master (629 FA items skipped on 2026-10-05) on the new asset classes; capitalization / opening values

---

## 2026-10-05 (Monday)

### ✅ Completed
| # | Task | Result / where |
|---|---|---|
| 1 | AKE's real customer + vendor list loaded into AKE_DEMO (user upload `Customer list.csv`, B1 export) | **711 BPs** created with AKE's own codes (user choice): 98 customers C001–C098 (Intrastate 71, Interstate 24, Export 3) and 613 vendors V001–V656 (Intrastate Vendor 511, Interstate Vendor 100, Import Vendor 2); 29 inactive vendors skipped (user choice). Each BP: name, all bill-to/ship-to addresses (Ajax C001 has 21 ship-to sites), state, GSTIN + GST type Regular, PAN (from GSTIN), mobile, e-mail, control + DP clearing accounts as on the demo BPs. Demo BPs C0001…/V0001… untouched |
| 2 | Parser for the unquoted export | `tools/parse_bp_list.py` → `data/ake_customers/bps.json` (fields found by anchors because commas in names/addresses/amounts shift the columns); loader `tools/load_ake_bps.py` (idempotent, `--dry`, `--only`) |
| 3 | States WB, GJ, RJ, BR, PB, JH added with GST codes | `sl_loader.py --step states` |
| 4 | Foreign / unregistered customers | PAN `PANNOTAVBL` + Deductee Ref. No. (B1 requires it) – C007 WEG Euro (PT), C040 Trackline (GB), C048 Wipro Oy (FI) |
| 5 | AKE's real **item master** loaded (user upload `item master list final.csv`) | **10,725 items** with AKE's codes, descriptions, item group and UoM group / inventory / purchasing / sales UoM by name (NOS, KGS, Tonnes, Meters, Set, LTR, m3, Square Meters, Grams, Pairs, Packet; OTH → Manual); valuation Moving Avg / Standard, Buy / Make, MRP, batch management and purchase / sales / inventory flags as in AKE. 543 inactive items created **inactive**, 629 fixed-asset items **skipped** (user choices). **51 new item groups** (Services, SubContracting, Assets, Spare parts …) with the G/L accounts of Consumables / Finished Goods / Packing Material – `tools/parse_item_list.py`, `tools/load_ake_items.py` |
| 6 | AKE's real **production BOMs** loaded (user upload `Bom master list.csv`) | **4,438 BOMs**, 27,605 lines (18,053 items incl. 4,460 negative by-product/scrap lines, 9,552 resources) – `tools/parse_bom_list.py`, `tools/load_ake_boms.py`. Unit-2 mapped to Unit-1 (U2 WHn → U1 WHn, RESxxx-U2 → RESxxx-U1; old 01 → U1WH01, SubcU221 → U1 WH3) – user choice. **53 new resources** (code as name, cost/min = price on AKE's BOM lines, UoM Mins, labour / machine / subcontract), assigned to every warehouse their BOM lines use |
| 7 | 174 BOM parents AKE had on **Buy** → **Make + MRP** (planning by procurement method) | `tools/fix_bom_parents.py`; 271 BOM parents are inactive items in AKE (left as is – their BOMs can't be used in production orders) |
| 8 | Demo production order on a real AKE BOM | **Production order #4** 050.193.01 Top Plate (part of Shovel 050.193) × 10, **Released**: Z24601500008 HR plate 120.3 KGS from U1 WH8, scrap SCR220001 −3.4 / SCR220003 −3.8 to U1 WH7, resources RESPCM2-U1 12.4, RESPCO-U1 12.4, RESHRO-U1 37.2 min – `python tools/demo_finance.py PRD`. Issue/receipt pending: AKE's items have no stock yet |
| 9 | AKE's **stock + average cost** loaded (user upload `item master with average Price and Stock.csv`) | **3,047 items** received into **U1 WH1** on **2026-04-01** against 1003 Opening Balance Offset – 32 goods receipts (Ref. 2 `AKE-OB-STK`), **₹23,62,82,311**; batch items on batch `OB-260401`; 818 standard items revalued to AKE's cost in U1 WH1 first (moving-average items take the receipt price). Skipped (user choices): 68 inactive items (₹42.6 L), the 8,235 rows without stock (cost not set); 4 items whose quantity rounds to 0 at 2 decimals (5010006, 5010010, 5010012, PL01.). USD rate set for 2026-04-01 – `tools/load_ake_stock.py` (idempotent, `--dry`, `--only`) |
| 10 | **Sales cycles** for AKE's first 10 customers C001–C010 | Sales Quotation → Sales Order → Delivery → A/R Invoice, each copied from the previous one: SQ2627/4–13, SO2627/9–18, DN2627/11–20, **INV2627/9–18 = ₹32,19,566.96** (left unpaid). Items fit the customer (drum parts for Ajax / Wirtgen / BEML, stator frames for L&T / WEG …) from AKE's stock in U1 WH1 at average cost + 25 %; GST CGST+SGST (KA), IGST (C004 MH, C008 TN), IGST 0 % export (C007 WEG Euro, PT) – `tools/demo_ake_cycles.py`, `docs/04_AKE_Sales_Purchase_Cycles.md` |
| 11 | **Purchase cycles** for AKE's first 10 vendors V001–V010 | Purchase Request → Purchase Quotation → Purchase Order → GRPO → A/P Invoice: PR2627/3–12, PQ2627/6–15, PO2627/6–15, GRN2627/8–17, **PINV2627/9–18 = ₹5,45,621.97** (left unpaid). Items fit the vendor (paint for Aaruda, bearings for Accurate Bearing, welding wire for Alloyage, HR plate / tube for Ambica …) at AKE's average cost into U1 WH1. PQ2627/5 cancelled (first try copied the request with quoted qty 0) |
| 12 | **Finished goods stock: 50 of every FG item in U1 WH5** (user request) | U1 WH5 renamed **Finished Goods Warehouse** (user choice: existing warehouse instead of a new U1 WH5F). All **391 active FG inventory items** (Finished Goods + Rework groups) have **50** in U1 WH5, value **₹251.61 Cr**: 5 goods receipts (Ref. 2 `AKE-FG-STK`, 01-04-2026 / 05-10 against 1003), 224 standard items revalued in U1 WH5 first, batch items on OB-260401. Cost = AKE's average cost; **43 items without a cost got a demo standard cost** like 90,150 (₹10,000–1,50,000 rounded to 50, user choice; revalued in U1 WH5 on 05-10 against 1003, list in `data/ake_items/fg_demo_costs.csv`). 101020000649 Drum Base Frame already had 7 in U1 WH5 at cost 0 (source document not found) → revalued to 53,641.28 and topped up by 43 – `tools/load_fg_stock.py` |
| 13 | Item cost **00010 Paint sample plates = ₹150** (user request; was AKE's 578) | Standard cost 150 in all 12 warehouses (50 in U1 WH5 revalued against 1003). Further items one by one: `python tools/set_item_cost.py ITEM=PRICE ...` |
| 14 | **Fixed-asset G/L account determination** (user upload `GL Account Determination.csv`) | **11 determinations** created as in AKE: TA-CP-01 Computers, TA-FB-01 Factory Buildings, TA-FE-01 Electrical Fittings, TA-FF-02 Furniture & Fixtures, TA-MV-01/02 Four / Two Wheelers, TA-OE-03 Office Equipment, TA-PM-01/02/03 Plant & Machinery / Fixtures / Instruments, TA-SNT-01 Server & Software – asset BS, acquisition clearing 5001-99-01, ordinary + unplanned depreciation, accumulated depreciation, revaluation reserve (+ clearing), revenue clearing 2003-08. All 23 accounts checked in the COA; read back = file – `tools/load_fa_account_determination.py` |
| 15 | **Depreciation types** (user upload `Depreciation types.csv`) | **9 WDV types** as in AKE (declining balance on NBV, factor 100, round year-end book value, salvage 5 %, reduce depreciation base, special depreciation Additional): CP-01WDV@63.16% Computers, FB-01WDV@9.50% Factory Buildings, FE-01WDV@25.89% Electrical Fittings, FF-02WDV@25.89% Furniture, MV-01WDV@31.23% Four Wheelers, MV-02WDV@25.89% Two Wheelers, OE-03WDV@45.07% Office Equipment, PM-01WDV@18.10% Plant & Machinery, SS-01WDV@39.30% Server & Software (salvage **not** included in depreciation for PM-01 and SS-01, as in the file). Read back = file – `tools/load_depreciation_types.py` |

### ⛔ Waiting on user / AKE
- FA account determinations: the file has no retirement / asset-sale accounts (Revenue from Asset Sales, Retirement with Expense/Revenue, NBV) – needed before retiring or selling assets; revaluation reserve = depreciation expense account as in AKE's file – confirm. Next: asset classes (account determination + depreciation type per class; P&M Fixtures / Instruments have no own type → PM-01WDV@18.10%) for the fixed-asset item master
- AKE's TDS codes, payment terms, price lists, credit limits and bank details were **not** loaded (export columns unreliable / codes differ in AKE_DEMO) – set where needed
- 82 BPs have no GSTIN in the export (unregistered or missing) – check before GST transactions with them
- Raw `Customer list.csv` and `data/ake_customers/` are git-ignored (bank account, balances, contact data); same for the item / BOM exports and `data/ake_items/`, `data/ake_boms/`
- 53 new resources are named by code only (e.g. RESBGO-U1, SCRESVTL-2000) – give real names / check cost per minute
- 43 FG items carry a **random demo cost** in U1 WH5 – replace with real costs when AKE provides them
- HSN missing on all **Tools** group items (B1 refuses GST lines without HSN) – V006 cycle used contactor add-on blocks instead
- Stock: AKE's exported stock sits in U1 WH1 (export has no warehouse); finished goods also have 50 each in U1 WH5 – transfer FG / scrap / WIP to their warehouses as needed; quantities rounded to 2 decimals (B1 quantity accuracy)
- Items: no HSN/SAC, prices or default warehouses loaded (AKE's are Unit-2); 37 items have no description in AKE's export (e.g. `100`)
- New item groups use template G/L accounts – review per group (services / subcontracting / assets)

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
| 12 | 9 Unit-1 warehouses (user list) | U1 WH1 Raw Material, U1 WH2 Bin Storage, U1 WH3 Subcontractor, U1 WH4 Work In Progress, U1 WH5 Finished Goods (stock a/c 5002-01-01-03), U1 WH6 Rework, U1 WH7 Scrap, U1 WH8 Cutting, U1 WH9 Quality – location AKE Peenya, same G/L accounts as the U1WH0x warehouses; `python tools/build_u1_masters.py --warehouses` |
| 13 | Duplicate U1 warehouses retired (user request) | U1WH02 → U1 WH1, U1WH07 → U1 WH5, U1WH03 → U1 WH9, U1WH06 → U1 WH7: 25 item default warehouses and BOMs SA001 / FG004 / FG005 moved, standard cost of all Standard items copied into U1 WH1–WH9 (revaluation, 90 lines), old four set **Inactive** (B1 cannot delete warehouses with transactions) – `tools/merge_warehouses.py`. U1WH01 Main and U1WH04 Rejected kept (no counterpart, hold stock) |
| 14 | Production BOM **PL01 Anchor Bolt Plate** in AKE's structure (user spec) | Rows in the given order: 1 Z24631250005 HR Plate 1250x5 0.27 KGS U1 WH8 Manual · 2 SCR220001 MS Scrap melting −0.05 KGS U1 WH7 Backflush (by-product) · 3–7 resources RESPCM2-U1 0.5, RESPCO-U1 0.5, RESHRO-U1 1.5, RESGGM-U1 1.0, RESHRO-U1 1.0 Mins U1 WH4 Backflush. New items Z24631250005 (Moving Avg, ₹62/KG), SCR220001 (new item group Scrap, sales ₹32/KG), PL01 (Make, MRP, Standard cost 43, sales 60); 4 resources costed per minute, resource UoM "Mins". U2 warehouses/resources from the spec mapped to Unit-1 (U1 WH8/WH7/WH4, -U1 codes) |
| 15 | Freight setup as in AKE's B1 (user screenshot) | **Packing & Forwarding**: revenue 2001-01-05 Packing Charges Collected, expense 4002-06-06, distribution Quantity, drawing Total, Stock ✔, Last Purchase Price ✔ · **Transport & Freight**: revenue 2001-01-06 Freight Revenue, expense 4002-06-01, Quantity, Total, Stock ✘, LPP ✘; WTax liable off – `data/12_freight.json`, `python tools/sl_loader.py --step freight` (B1 freight name max 20 chars) |
| 16 | All resources in **minutes** (user request) | R-CUT-PLASMA 20, R-SAW 7.5, R-DRILL 8.33, R-WELD-MIG 10, R-BLAST 15, R-FITTER 5.83, R-WELDER 6.67 ₹/min (were per hour), UoM "Mins" on all 11 resources; resource quantities ×60 in BOMs SA-BASEPL-400, SA-GUSSET-12, FG-COL-MB300-6M, FG-PLAT-HR, FG-CTRAY-300 (e.g. 0.25 h → 15 min) so BOM cost is unchanged; `data/08_resources.json`, `data/09_boms.json` updated |
| 17 | First demo-set warehouses retired (user request) | Item defaults, BOM rows and the 7 R-* resources moved: CONS → U1WH01, FG → U1 WH5, RM-STR → U1 WH1, SHOP → U1 WH4. **All 7 inactive:** 01 (given accounts + location first), SCRAP, SHOP, then CONS, FG, RM-STR, SITE after inventory transfers of their stock (user choice): CONS + SITE → U1WH01 (11 lines), RM-STR → U1 WH1 (4 steel items, 1,305.8 KG), FG → U1 WH5 (FG-COL-MB300-6M 2). The 12 inactive items involved were reactivated only for the transfer and set inactive again |
| 18 | Finance demo (`tools/demo_finance.py`) | **Manual JEs** 60–63: salary provision Sep-26 ₹5,00,000 (Dr 4003-01-02/-01 Cr 3002-04-06), depreciation P&M ₹85,000 (Dr 4007-03 Cr 5001-01-03-10), power + factory rent accrual ₹1,82,500 (Dr 4002-01-01/-04 Cr 3002-05-01/-02), bank charges ₹590 · **A/P down payment** V0012, EL002 10 Nos: PO #5 ₹51,920 → APDP request #1 30 % ₹15,576 → advance PAY #3 → GRPO #7 → A/P invoice #8 drawing the advance (balance ₹36,344) → PAY #4, invoice closed · **A/R down payment** C0009, EL002 5 Nos: SO #8 ₹30,680 → ARDP request #1 50 % ₹15,340 → advance RCT #5 → delivery #10 → A/R invoice #8 drawing the advance → RCT #6, invoice closed. BP balances, clearing and interim accounts net to 0 |
| 20 | Inventory Transfer Request #1 (user request) | EL002 Distribution Board 3 Nos, U1 WH1 Raw Material → U1 WH2 Bin Storage, status Open (no stock moved) – `python tools/demo_finance.py TRQ` |
| 21 | Query Manager category **Monthly Performance Analysis** (code 22) | All user groups authorised – `python tools/build_reports.py --categories` |
| 22 | 13 Performance Analysis reports PAR-001 – PAR-013 (AKE's list) in Monthly Performance Analysis | Incorrect valuation method (Buy ≠ Moving Avg / Make ≠ Standard), item cost vs BOM production cost variance, pending GRPO → A/P invoice, pending delivery → A/R invoice, production orders to close, production orders with pending issue/receipt, rejection receipts pending return to vendor, purchase register, grade items with stock, closing inventory detailed / item-group, consumption detailed / item-group (period reports prompt From/To date). Query Manager now holds 52 reports |
| 19 | Down payment G/L determination (found by the demo) | Purchase DP clearing 5002-04-07-01 Advance Clearing Account, sales DP clearing 3002-02-04 Trade Debitors – Advance Received, purchase DP interim 5002-04-04-01; DP clearing account set on all 30 BPs – `sl_loader.py --step gldet` |

### ⛔ Waiting on user / AKE
- Rename in the SAP client (they have transactions, Service Layer cannot change a BP code): **U1C006 → C0012** ABC Developers and **U1V001 → V0010** Tungabhadra Steel. The demo script and guide already use C0012 / V0010.
- New BPs: choose the group by address – Karnataka → Intrastate, other Indian state → Interstate, outside India → Export / Import Vendor
- Inactive items still hold stock (e.g. RM-PL-0012 486.4 KG, RM-PL-0020 299.8 KG, RM-ST-A50 300 KG, RM-ST-MB300 219.6 KG, FG-COL-MB300-6M 2 Nos, SF001 7 Nos) and sit in the old BOMs FG-COL-MB300-6M, FG-PLAT-HR, FG-CTRAY-300, SA-BASEPL-400, SA-GUSSET-12 – decide: issue / write off the stock, and replace those BOM lines with active items
- Items now counted in NOS: steel prices (₹55–72) and FG001/FG002 standard cost (85 / 82) were per KG, RM008 ₹48 per SQFT, RM011 ₹5,600 per m3 – set real per-piece prices / costs; BOM quantities (e.g. SA001 6.5 × RM003, FG005 1.05 × RM008) now mean NOS
- Consumables now counted in NOS: check the price figures (e.g. CN005 degreaser ₹180, CN006 brazing rod ₹38 were per LTR / Gram) and the BOM quantities SA001 → CN001 0.3 and FG004 → CN005 0.2 (now NOS)
- **T0.1** TDS @ 0.1 % Purchase (and Q01) not created: section **194Q** is missing in B1 and cannot be added via Service Layer – add it in the client (Administration > Setup > Financials > Tax > Section), then re-run `--step tds`
- Swap vendor TDS codes in the client (BP Master Data > Accounting > Tax > WTax Codes; Service Layer cannot remove a BP's WT row): **V0008, V0017 C2 → TDS2**, **V0009 J10 → TJ10**. V0007 / V0018 are individuals (atOthers) and stay on C1 – TDS1 is defined for companies (COM)
- U1WH01 Main (default of 18 items, BOM SA001 + consumable lines, SF001 5 Nos) and U1WH04 Rejected (RM001 50 KG, SF001 2 Nos) have no counterpart in the new list – decide: map Main → U1 WH2 Bin Storage? Rejected → U1 WH6 Rework?
- All resources are costed **per minute**: check General Settings > Resources time unit = minutes; SCR220001 has no item cost yet, so scrap returned from production is valued at 0 until it is costed
- Freight: check **Tax Distribution = Quantity** on both rows in the client (field not exposed by Service Layer) and assign GST tax codes / SAC to freight if AKE charges GST on it
- Down payments – for AKE's accountant: GST on the advance is posted to the DP tax account 3002-03-22 **IGST Payable** (also for CGST/SGST parties) and reversed when the invoice draws it – consider a separate "GST on advances" ledger (GST on advances applies to services, not goods); account 5002-04-04-01 (DP interim) has no name in the AKE COA
- Run PAR-001 – PAR-013 once in the SAP client (Service Layer cannot test them: arithmetic/CASE rejected, OINM/OIGE/IGE1/OWHS not accessible); PAR-009 derives the grade from the item description (S355, E350, E250/Gr. BR, Fe500D, SS304) – switch to a Grade UDF if AKE has one; PAR-007 treats GRPO lines into warehouses named "Reject…"/"Rework…" as rejections
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
