# AKE SAP B1 – Daily Updates

Project: AKE Infrastructure – SAP Business One 10 (HANA) training database **AKE_DEMO**, built by Qltc.
Newest day on top. Status: ✅ Completed · 🔄 In progress · ⛔ Blocked / waiting · 📌 Next

---

## 2026-10-02 (Friday)

### ✅ Completed
| # | Task | Result / where |
|---|---|---|
| 1 | Query Manager categories created in AKE_DEMO | OTC (18), PTP (19), PTS (20), FICO (21) – `python tools/build_reports.py --categories` |
| 2 | 28 reports saved into Query Manager | 7 each in OTC / PTP / PTS / FICO – `python tools/build_reports.py --no-test` |

### 🔄 In progress
| Task | Status |
|---|---|
| Query Manager reports (28) | Saved; not yet run – Service Layer SQLQueries cannot test them (rejects `\|\|`, CASE, arithmetic, OACT/OWHT), so run each once in the SAP client |
| Crystal Reports print layouts (.rpt) | Continue on SAP server SSO-WINDOWS1 |

### ⛔ Waiting on user / AKE
- Same open items as 2026-10-01 (HANA read-only user, TDS 194Q, USD rate, company address, `manager` password, bank details, Claude Code on SSO-WINDOWS1)

### 📌 Next
1. Run each of the 28 reports in the SAP client (dates 01-04-2026 to 31-03-2027) and fix any that fail
2. Crystal Tax Invoice layout on the SAP server

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
