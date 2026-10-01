# Handover – continue on the SAP server (SSO-WINDOWS1)

Written 2026-10-01 on DESKTOP-TP26OE1. A new Claude Code session on the SAP server starts with no memory of the
earlier session – read this file first.

## Goal of the next session
Build **Crystal Reports print layouts (.rpt)** for AKE_DEMO and import them into SAP Business One, matching the PDF
formats produced by `tools/print_docs.py` (see `prints/` after running it). Start with the **Tax Invoice (A/R Invoice,
object 13)**, test it from SAP's Print button, then do the other documents one by one.

Check first on SSO-WINDOWS1:
1. *SAP Crystal Reports for SAP Business One* (designer) is installed – it provides the Crystal SDK
   (`CrystalDecisions.*` / RAS `ReportClientDocument`) needed to build .rpt files programmatically.
2. The SAP B1 client is installed (to import layouts: *Administration → Setup → General → Report and Layout Manager*).
3. HANA ODBC driver (HDBODBC) is available – Crystal layouts for B1 connect to the company schema **AKE_DEMO**.

## Company: AKE_DEMO (SAP B1 10.0 for HANA, SP 2511, India localization)
- Service Layer: `https://hana-sap-b1:50000/b1s/v2`, user `manager`. Credentials live in `.env` (git-ignored, copy it
  manually). Self-signed TLS certificate pinned via `SL_CA_FILE=sl_cert.crt` – never disable TLS verification.
- Company: Ake Infrastructure Pvt. Ltd., location 1 = Bangalore - Peenya, GSTIN 29AAMCA5278K1ZZ, PAN AAMCA5278K
  (B1 India derives the location PAN from the ECC number `AAMCA5278KXM001`).

## What is loaded (all via `tools/sl_loader.py`, idempotent – re-runs skip existing records)
Chart of Accounts (598, AKE's real COA), G/L account determination, GST ledgers on CGST/SGST/IGST authorities +
40% slab codes, TDS codes C1/C2/J10/I10/A10, TDS financial years, 10 states with GST codes, 6 warehouses, 9 item
groups, 37 items with HSN, SAC 998331, 7 resources, 5 BOMs, 15 dummy customers/vendors, 25 FY 2026-27 numbering series.

## Transactions (`tools/demo_transactions.py`, state in `logs/txn_state.json`)
Purchase P1–P3 (P3 = service invoice with TDS J10), Inventory I1–I3, Production PR1–PR3, Sales S1–S5
(S4/S5 = multi-line, multi-tax-code SO + delivery). 34 documents; PDFs via `python tools/print_docs.py`.

## B1 India facts the layouts must handle
- A/R + A/P invoices and credit memos use **GST sub-types GA/GD**; their FY series start at 4 because invoices 1–3 were
  posted in the old Primary series (print as "Primary-n").
- Line tax: tax code `CG+SG@x` → split CGST/SGST equally; `IGST@x` → IGST. HSN = item `ChapterID` → `IndiaHsn`
  (B1 stores `72.08.` – print digits only); SAC = line `SACEntry` → `IndiaSacCode`.
- TDS on purchase invoices: `WTAmount` / `WithholdingTaxDataCollection`; DocTotal is already net of TDS.
- Party GSTIN/state come from the BP Bill-To address; place of supply = BP state (sales) / Karnataka (purchase).

## Open items (need AKE / user)
- Section 194Q missing in B1 (add manually) → then `python tools/sl_loader.py --step tds --step bps` for Q01, V0001/V0002.
- USD system-currency rate 88.00 for 2026-10-01 is a demo value – replace with the real rate.
- Company Details address (Administration → Company Details) is empty – fill manually.
- Change the `manager` password (it was shared in chat) and update `.env`.
- AKE bank account details for invoice footers – not provided.
