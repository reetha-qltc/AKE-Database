# AKE_DEMO – Procure-to-Pay and Order-to-Cash demonstration

Training scenarios posted in AKE_DEMO on 02-10-2026 by `tools/demo_o2c_p2p.py` (U1 masters from
`tools/build_u1_masters.py`). All parties are in Karnataka, the same state as AKE, so GST is CGST 9% + SGST 9%.
The one exception is the comparison quotation from V0002 (Telangana), which is IGST 18%.
Open each document in the SAP client by its number and use **Relationship Map** (right-click → Relationship Map) to
show the whole chain.

Reports PTP08 and PTP09 were tested against this data. PTP01, OTC02 and FIN04 are saved in Query Manager but have not
yet been run in the SAP client (see DAILY_UPDATES.md), so run them once before the session.

Posting dates are spread over 21-09 to 02-10-2026 to tell the story in order. P2P comes first because its GRPOs
supply the RM001 stock that the O2C deliveries use.

---

## 1. Procure to Pay – RM001 TMT Steel Bar 12mm, 1,000 KG

| # | Step | Document | Date | Amount (₹) | What to show |
|---|---|---|---|---|---|
| 1 | Purchase Request | PR/26-27/1 | 21-09 | – | 1,000 KG for U1WH02, required by 30-09, preferred vendor U1V001 |
| 2 | Purchase Quotation – U1V001 Tungabhadra Steel | PQ/26-27/1 | 22-09 | 73,160.00 | ₹62.00/KG, delivery 30-09 – **lowest** |
| 3 | Purchase Quotation – V0001 Shree Ganesh Steel | PQ/26-27/2 | 22-09 | 75,520.00 | ₹64.00/KG, delivery 03-10 |
| 4 | Purchase Quotation – V0002 Deccan Structural | PQ/26-27/3 | 22-09 | 74,930.00 | ₹63.50/KG, delivery 05-10, IGST (Telangana) |
| 5 | Quotation comparison | Query **PTP08** | – | – | Sorted by rate; U1V001 is cheapest and fastest |
| 6 | Purchase Order (copied from PQ/26-27/1) | PO/26-27/3 | 24-09 | 73,160.00 | 1,000 KG @ ₹62; B1 closed the PR and the two losing quotations |
| 7 | GRPO #1 – partial | GRN/26-27/3 | 26-09 | 43,896.00 | 600 KG received |
| 8 | **Validate the PO** | PO/26-27/3 | – | – | Ordered **1,000** · Received **600** · Open **400** |
| 9 | A/P Invoice for GRPO #1 | PINV/26-27/5 | 26-09 | 43,896.00 | 37,200 + CGST 3,348 + SGST 3,348 |
| 10 | Partial vendor payment | PAY/26-27/1 | 29-09 | 25,000.00 | Invoice stays open with balance 18,896.00 |
| 11 | GRPO #2 – remaining | GRN/26-27/4 | 01-10 | 29,264.00 | 400 KG → PO closes |
| 12 | A/P Invoice for GRPO #2 | PINV/26-27/6 | 01-10 | 29,264.00 | 24,800 + CGST 2,232 + SGST 2,232 |

**Result:** U1V001 is still owed ₹48,160.00 (18,896.00 left on invoice 1 + 29,264.00 on invoice 2).

### How to show each point in SAP

- **Partial GRPO:** open PO/26-27/3 and look at the Open Qty column, or use Relationship Map to see PO → 2 GRPOs → 2 invoices.
- **Open PO report:** Query Manager → PTP → **PTP01 Open Purchase Orders – Pending GRPO**. Between GRPO #1 and GRPO #2 the
  PO appeared there with 400 KG open. The PO is now fully received, so use **PTP09 PO Receipt Status by GRPO** instead. It
  lists PO/26-27/3 with both receipts (600 + 400) and Open Qty 0. In the standard reports you can also use
  Purchasing Reports → Open Items List → Purchase Orders.
- **GST:** in either A/P invoice, open the Tax amount (golden arrow) or the Tax tab: tax code CG+SG@18 splits into
  CGST 9% and SGST 9%. Query **FIN04 GST Summary** shows the input credit.
- **Partial vendor payment:** open PINV/26-27/5. Paid to date is 25,000.00 and the balance is 18,896.00. Business Partner
  Master Data U1V001 → Account Balance shows 48,160.00.

> Re-doing the open-PO step live: create a new PO, receive part of it, run PTP01, then receive the rest.

---

## 2. Order to Cash – ABC Developers Pvt Ltd (U1C006)

Stock setup: Goods Receipt GR/26-27/6 (25-09) brought 25 Nos SF001 into U1WH01 at ₹180. RM001 came from the P2P GRPOs.

| # | Step | Document | Date | Amount (₹) | What to show |
|---|---|---|---|---|---|
| 1 | Sales Quotation | SQ/26-27/2 | 25-09 | 86,140.00 | RM001 1,000 KG @ ₹68 + SF001 20 Nos @ ₹250 |
| 2 | Sales Order (from quotation) | SO/26-27/6 | 26-09 | 86,140.00 | Customer PO ABC/PO/2026/118 |
| 3 | Delivery #1 | DN/26-27/6 | 28-09 | 54,044.00 | **Partial:** RM001 600 of 1,000 KG · **Full:** SF001 20 of 20 Nos |
| 4 | **Remaining open quantity** | SO/26-27/6 | – | – | RM001 open **400 KG**, SF001 open 0 |
| 5 | Return before invoice | SR/26-27/1 | 29-09 | 590.00 | 2 cracked helmets back to U1WH04 Rejected Warehouse |
| 6 | A/R Invoice #1 (from DN #1) | INV/26-27/5 | 29-09 | 53,454.00 | 600 KG + **18** Nos (20 − 2 returned): 45,300 + CGST 4,077 + SGST 4,077 |
| 7 | Incoming Payment | RCT/26-27/2 | 30-09 | 53,454.00 | Invoice #1 paid in full |
| 8 | Delivery #2 | DN/26-27/7 | 01-10 | 32,096.00 | Remaining 400 KG → **Sales Order fully delivered** (closed) |
| 9 | A/R Invoice #2 (from DN #2) | INV/26-27/6 | 01-10 | 32,096.00 | 27,200 + CGST 2,448 + SGST 2,448 |
| 10 | A/R Credit Memo (from invoice #2) | SCN/26-27/1 | 02-10 | 4,012.00 | 50 KG bent bars rejected at site → U1WH04; 3,400 + CGST 306 + SGST 306 |
| 11 | Incoming Payment | RCT/26-27/3 | 02-10 | 28,084.00 | Invoice #2 balance after the credit memo (32,096 − 4,012) |

**Result:** ABC Developers balance is ₹0.00. Stock left: RM001 50 KG in U1WH04 (rejected), SF001 5 Nos in
U1WH01 + 2 Nos in U1WH04.

### The five points to demonstrate

1. **Full delivery:** SF001 on DN/26-27/6 (20 of 20). The whole order is fully delivered after DN/26-27/7, and SO/26-27/6 closes.
2. **Partial delivery:** RM001 on DN/26-27/6, 600 of 1,000 KG.
3. **Remaining open quantity:** open SO/26-27/6 after DN #1 and look at the Open Qty column (400 KG). Query **OTC02 Open Sales
   Orders – Pending Delivery** lists it while it is open.
4. **Return before invoice:** SR/26-27/1 is copied from DN/26-27/6. The invoice copied afterwards brings only 18 Nos,
   because B1 deducts returned quantities.
5. **A/R Credit Memo after invoice:** SCN/26-27/1 is copied from INV/26-27/6. B1 offsets it against the invoice, so the
   customer pays only the net amount (RCT/26-27/3).

---

## Re-running

`python tools/demo_o2c_p2p.py` records every posted document in `logs/txn_state.json` (keys `P2P-*`, `O2C-*`) and
skips them on a re-run. To post the scenario again as a new set, remove those keys from the file. The script
sets the demo USD rate (88.00) for each posting date, because AKE_DEMO's system currency is USD.

### Setup fixed while building the demo

- Company G/L determination: **realized conversion difference** accounts (gain 2003-02, loss 4006-07) – incoming payments
  failed without them (system currency USD).
- **Sales credit / purchase credit** accounts (2001-01-01-01 / 4008-01) on all item groups and in G/L determination –
  A/R credit memos failed with "G/L account is missing".
- SF001 Safety Helmet made a sales item (₹250); new customer U1C006 ABC Developers Pvt Ltd (Bengaluru).
