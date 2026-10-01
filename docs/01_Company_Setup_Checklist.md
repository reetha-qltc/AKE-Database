# AKE Training Database – Company Setup Checklist

**Target:** SAP Business One 10.0 FP 2511 (10.00.310) for SAP HANA · India localization · INR
**Spiral 1 – Prototype.** Steps marked **[Manual]** are done by Qltc in the B1 client; steps marked **[Loader]** are posted by `tools/sl_loader.py` through Service Layer.

---

## Step 1 – Create the company [Manual]
*Administration → Choose Company → New*

| Field | Value |
|---|---|
| Company Name | AKE Infrastructure Pvt Ltd (TRAINING) |
| Database Name | `AKE_TRAINING` |
| Localization | India |
| Chart of Accounts | **User-Defined** (AKE's own COA is loaded in Step 3) |
| Base language | English (United States) |
| Posting Periods | FY 2026-27, Period code `2026-27`, sub-periods **Months**, 01.04.2026 – 31.03.2027 |

Then, before posting anything (these cannot be changed after the first transaction):

*Administration → System Initialization → Company Details*
- **General:** Address – Plot (dummy), KIADB Industrial Area, Dabaspet, Bengaluru Rural, Karnataka 562111 · Country IN · State Karnataka
- **Accounting Data:** GSTIN `29AAKCA5520T1ZY` (dummy) · PAN `AAKCA5520T` (dummy) · TAN `BLRA12345B` (dummy)
- **Basic Initialization:**
  - ☑ Use Perpetual Inventory
  - Default valuation method: **Moving Average**
  - Set G/L Accounts by: **Item Group** (the loader sets AKE's accounts on each item group)
  - ☐ Manage Item Cost per Warehouse
  - ☐ Allow Stock Release Without Item Cost

*Administration → System Initialization → General Settings → Inventory*
- Block negative inventory: **Yes** (this is what stops the stock drifting below zero when Issue for Production is wrong – topic B1)

## Step 2 – Send Service Layer access [Manual]
Create `C:\Projects\AKE-Database\.env` (it is git-ignored – never pushed):
```
SL_URL=https://<hana-server>:50000/b1s/v2
SL_COMPANY=AKE_TRAINING
SL_USER=manager
SL_PASSWORD=<password>
SL_VERIFY_TLS=false
TRAINEE_PASSWORD=<initial password for the 6 users>
```
Then Claude runs `python tools/sl_loader.py --check` to confirm the login and the COA drawers.

## Step 3 – Load master data [Loader]
`python tools/sl_loader.py` – in order:

| Step | What | Count |
|---|---|---|
| coa | AKE Chart of Accounts **as given** (92 titles, 506 postable) | 598 |
| warehouses | RM-STR, CONS, SHOP, FG, SCRAP, SITE | 6 |
| paymentterms | Net 15 / 30 / 45 / 60 days | 4 |
| pricelists | Purchase Price (Dummy), Sales Price (Dummy – Restricted) | 2 |
| itemgroups | AKE's item groups with their own inventory / consumption accounts | 9 |
| items | Dummy plates, structurals, special grades, TMT, consumables, PPE, tools, sub-assemblies, FG | 37 |
| bps | 9 vendors + 6 customers, fictional names, dummy GSTIN/PAN (KA, TN, MH, TS, KL) | 15 |
| resources | Plasma cutter, band saw, drill, MIG welding, blasting booth, fitter, welder | 7 |
| boms | 2 sub-assemblies + 3 FG production BOMs, manual issue | 5 |
| users | RASHMI, NAMRATA, ASHOK, SUNIL, VEENA, TRAINER | 6 |
| ob_stock / ob_bp / ob_gl | Dummy opening balances at 01.04.2026 against `1003 Opening Balance Offset Account` | 3 docs |

## Step 4 – G/L Account Determination (company defaults) [Manual]
*Administration → Setup → Financials → G/L Account Determination* – all are AKE's own accounts:

| Tab / Field | Account |
|---|---|
| Sales – Domestic Accounts Receivable | 5002-02-04-01 Trade Debtors (Domestic) |
| Sales – Foreign Accounts Receivable | 5002-02-04-02 Trade Debtors (Foreign) |
| Sales – Revenue Account | 2001-01-01-01 *(unnamed in AKE COA – see finding F14)* |
| Sales – Down Payment Clearing | 3002-02-07-01 Down Payment |
| Sales – Cash Discount | 4004-07-24 Cash Discount Account |
| Sales – Rounding | 2001-01-04 Invoice Paise Round off Account |
| Purchasing – Domestic Accounts Payable | 3002-02-01 Trade Creditors – Domestic |
| Purchasing – Foreign Accounts Payable | 3002-02-02 Trade Creditors – Foreign |
| Purchasing – Goods Clearing (GRNI) | 3002-02-05 Goods Received Not Invoiced |
| Purchasing – Down Payment | 5002-04-01-01 Advance to Suppliers |
| General – Exchange Rate Differences | 4006-07 Foreign Currency Exchange Rate (Loss/Gain) |
| General – Bank Charges | 4006-06 Bank Charges |
| General – Opening Balance | 1003 Opening Balance Offset Account |
| Inventory – Inventory Offset Increase / Decrease | 4001-20 Stock Difference Gains / 4001-21 Stock Difference Losses |
| Inventory – Price Difference | 4001-17 Materials – Purchase Price Variance |
| Inventory – WIP / WIP Variance | 5002-01-02 Work in Progress / 4001-23 Material – Production Cost Variance |
| Resources – Resource cost / Overheads | 3003-02-02 Labour Cost, 3003-02-03 Manufacturing Conversion Cost / 3003-02-04 Overheads |

## Step 5 – GST [Manual]
*Administration → Setup → Financials → Tax → Tax Codes* (tax types CGST / SGST / IGST), with AKE's accounts:

| Code | Rate | Components | Output account(s) | Input account(s) |
|---|---|---|---|---|
| CGST+SGST18 | 18% | CGST 9 + SGST 9 | 3002-03-24 / 3002-03-25 | 5002-05-02-02 / 5002-05-02-01 |
| IGST18 | 18% | IGST 18 | 3002-03-22 | 5002-05-02-03 |
| CGST+SGST12 | 12% | CGST 6 + SGST 6 | 3002-03-24 / 3002-03-25 | 5002-05-02-02 / 5002-05-02-01 |
| IGST12 | 12% | IGST 12 | 3002-03-22 | 5002-05-02-03 |

Tax Code Determination: same state (KA → KA) → CGST+SGST; other state → IGST. Item HSN codes are listed in `data/05_items.json` (field `HSN`) and are entered in the item master (Chapter ID).

## Step 6 – TDS [Manual]
*Administration → Setup → Financials → Tax → Withholding Tax* – one code per section, posting to AKE's existing TDS accounts:

| WT Code | Section | Rate | Account |
|---|---|---|---|
| 194Q | Purchase of goods | 0.1% | 3002-03-23 TDS Payable on Purchases |
| 194C1 | Contractor – Individual/HUF | 1% | 3002-03-18 TDS Payable @ 1% |
| 194C2 | Contractor – Others | 2% | 3002-03-14 TDS Payable @ 2% |
| 194J | Professional fees | 10% | 3002-03-16 TDS on Professional Charges @ 10% |
| 194I | Rent | 10% | 3002-03-15 TDS Payable on Rent |
| 194A | Interest | 10% | 3002-03-26 TDS Payable on Pvt Finances |

Then tick *Subject to Withholding Tax* and assign the code on vendors **V0001, V0002 (194Q), V0007, V0008 (194C2), V0009 (194J)**.

## Step 7 – Licences and authorizations [Manual]
*Administration → License → License Administration*: assign the 6 licences to RASHMI, NAMRATA, ASHOK, SUNIL, VEENA, TRAINER.

**Selling-price confidentiality (topic A5)** – two layers:
1. **At source:** the database contains only dummy sales prices – no real AKE price exists anywhere in it.
2. **Authorizations** (*Administration → System Initialization → Authorizations → General Authorizations*), for every user except TRAINER:
   - Inventory → Price Lists → **No Authorization**
   - Sales – A/R → Gross Profit → **No Authorization**
   - Reports → Sales Analysis → **No Authorization**

| User | Role focus | Modules – Full |
|---|---|---|
| RASHMI, NAMRATA | Directors | Read-only across modules + Financial reports |
| ASHOK | Planning, SCM | Purchasing, Inventory, Production, MRP |
| SUNIL | Finance | Financials, Banking, Financial reports |
| VEENA | Accounts | A/R and A/P invoices, Banking, Journal Entries |
| TRAINER | Qltc | Superuser |

## Step 8 – Smoke test (Spiral 1 – Test)
1. Trial Balance at 01.04.2026 balances; 1003 carries the offset.
2. Inventory Status report shows the opening stock per warehouse.
3. One OTC cycle (C0003, FG-CTRAY-300), one PTP cycle (V0001, RM-ST-A50 with GRPO), one Production to Stock cycle (FG-COL-MB300-6M: production order → manual issue → receipt).
4. Log in as SUNIL and confirm that no price list and no gross profit is visible.
