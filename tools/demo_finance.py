"""Finance training demo for AKE_DEMO: manual journal entries, A/P down payment and A/R down payment.

JE    Month-end entries for Sep-2026: salary provision, depreciation, power + factory rent accrual; bank charges.
APDP  V0012 Vidyut Electricals (Karnataka, CGST+SGST), EL002 Distribution Board 10 Nos: Purchase Order ->
      A/P Down Payment Request 30 % -> advance paid -> GRPO -> A/P Invoice drawing the advance -> balance paid.
ARDP  C0009 Godavari Power Plant (Telangana, IGST), EL002 5 Nos from the stock received in APDP: Sales Order ->
      A/R Down Payment Request 50 % -> advance received -> Delivery -> A/R Invoice drawing the advance -> balance received.

Run:  python tools/demo_finance.py            (JE, APDP, ARDP - ARDP sells the stock bought in APDP)
      python tools/demo_finance.py JE         (one flow)
Posted documents are recorded in logs/txn_state.json (keys FIN-*), so a re-run continues where it stopped.
"""
import sys

import demo_transactions as T

BANK = T.BANK
RM_WH = "U1 WH1"
MONTH_END, TODAY = "2026-09-30", T.DATE
ITEM, BUY, SELL = "EL002", 4400.0, 5200.0


class Run(T.Run):
    def __init__(self):
        super().__init__()
        r = self.sl.s.post(f"{self.sl.base}/SBOBobService_SetCurrencyRate", timeout=60,
                           json={"Currency": "USD", "Rate": str(T.USD_RATE), "RateDate": MONTH_END.replace("-", "")})
        if r.status_code not in (200, 204):
            raise SystemExit(f"FAIL USD rate {MONTH_END}: {r.text[:300]}")


def head(card, ref):
    return {"CardCode": card, "DocDate": TODAY, "DocDueDate": TODAY, "TaxDate": TODAY, "NumAtCard": ref,
            "Comments": f"AKE finance demo {ref}"}


def base(btype, doc, line=0):
    return {"BaseType": btype, "BaseEntry": doc["DocEntry"], "BaseLine": line}


def show(run, entity, doc, title):
    d = run.get(entity, doc["DocEntry"])
    print(f"     {title} #{d['DocNum']}: total {d['DocTotal']:,.2f}, tax {d['VatSum']:,.2f}, "
          f"paid {d.get('PaidToDate') or d.get('DownPaymentAmount') or 0:,.2f}, status {d['DocumentStatus']}")
    return d


# ------------------------------------------------------------------------------------------- manual journal entries
JES = [  # key, memo, date, [(account, debit, credit, line memo)]
    ("FIN-JE1", "Salary provision Sep-2026", MONTH_END,
     [("4003-01-02", 350000, 0, "Salaries - production staff"), ("4003-01-01", 150000, 0, "Salaries - SGA staff"),
      ("3002-04-06", 0, 500000, "Salaries & wages payable")]),
    ("FIN-JE2", "Depreciation Sep-2026 - plant and machinery", MONTH_END,
     [("4007-03", 85000, 0, "Depreciation P&M"), ("5001-01-03-10", 0, 85000, "Accumulated depreciation P&M")]),
    ("FIN-JE3", "Power and factory rent accrual Sep-2026", MONTH_END,
     [("4002-01-01", 62500, 0, "BESCOM power Sep-2026"), ("4002-01-04", 120000, 0, "Factory rent Sep-2026"),
      ("3002-05-01", 0, 62500, "Power charges payable"), ("3002-05-02", 0, 120000, "Factory rent payable")]),
    ("FIN-JE4", "Bank charges - Kotak current account", TODAY,
     [("4006-06", 590, 0, "NEFT / RTGS charges incl. GST"), (BANK, 0, 590, "Kotak C/A debit advice")]),
]


def JE(run):
    for key, memo, d, rows in JES:
        run.doc(key, "JournalEntries", {
            "ReferenceDate": d, "TaxDate": d, "DueDate": d, "Memo": memo, "Reference": key,
            "JournalEntryLines": [{"AccountCode": a, "Debit": dr, "Credit": cr, "LineMemo": m} for a, dr, cr, m in rows]},
            f"{memo} ({sum(r[1] for r in rows):,.2f})")


# ------------------------------------------------------------------------------------------- A/P down payment
def APDP(run):
    card, qty, pct = "V0012", 10, 30
    tax = T.INTRA  # Karnataka vendor
    po = run.doc("FIN-APDP-PO", "PurchaseOrders", {**head(card, "FIN-APDP-PO"), "DocumentLines": [
        {"ItemCode": ITEM, "Quantity": qty, "UnitPrice": BUY, "WarehouseCode": RM_WH, "TaxCode": tax}]},
        f"PO {ITEM} {qty} Nos @ {BUY:,.0f}")
    p = show(run, "PurchaseOrders", po, "Purchase Order")
    dp = run.doc("FIN-APDP-DPR", "PurchaseDownPayments", {**head(card, "FIN-APDP-DPR"),
        "DownPaymentType": "dptRequest", "DownPaymentPercentage": pct, "DocumentLines": [base(22, po)]},
        f"A/P down payment request {pct} % of PO")
    d = show(run, "PurchaseDownPayments", dp, "A/P Down Payment Request")
    run.doc("FIN-APDP-PAY1", "VendorPayments", {"CardCode": card, "DocDate": TODAY, "TransferAccount": BANK,
        "TransferSum": d["DocTotal"], "TransferDate": TODAY, "TransferReference": "NEFT-APDP-ADV",
        "Remarks": "AKE finance demo - advance to vendor",
        "PaymentInvoices": [{"DocEntry": dp["DocEntry"], "SumApplied": d["DocTotal"], "InvoiceType": "it_PurchaseDownPayment"}]},
        f"Advance paid {d['DocTotal']:,.2f}")
    grn = run.doc("FIN-APDP-GRN", "PurchaseDeliveryNotes", {**head(card, "FIN-APDP-GRN"), "DocumentLines": [base(22, po)]},
                  f"GRPO {ITEM} {qty} Nos")
    d = run.get("PurchaseDownPayments", dp["DocEntry"])
    inv = run.doc("FIN-APDP-INV", "PurchaseInvoices", {**head(card, "FIN-APDP-INV"), "DocumentLines": [base(20, grn)],
        "DownPaymentsToDraw": [{"DocEntry": dp["DocEntry"], "AmountToDraw": d["DocTotal"] - d["VatSum"]}]},
        "A/P invoice drawing the advance")
    i = show(run, "PurchaseInvoices", inv, "A/P Invoice (after drawing the advance)")
    bal = round(i["DocTotal"] - i["PaidToDate"], 2)
    run.doc("FIN-APDP-PAY2", "VendorPayments", {"CardCode": card, "DocDate": TODAY, "TransferAccount": BANK,
        "TransferSum": bal, "TransferDate": TODAY, "TransferReference": "NEFT-APDP-BAL",
        "Remarks": "AKE finance demo - balance after advance",
        "PaymentInvoices": [{"DocEntry": inv["DocEntry"], "SumApplied": bal, "InvoiceType": "it_PurchaseInvoice"}]},
        f"Balance paid {bal:,.2f} (PO value {p['DocTotal']:,.2f})")
    show(run, "PurchaseInvoices", inv, "A/P Invoice")


# ------------------------------------------------------------------------------------------- A/R down payment
def ARDP(run):
    card, qty, pct = "C0009", 5, 50
    tax = T.INTER  # Telangana customer
    so = run.doc("FIN-ARDP-SO", "Orders", {**head(card, "GPPC/PO/2026/77"), "DocumentLines": [
        {"ItemCode": ITEM, "Quantity": qty, "UnitPrice": SELL, "WarehouseCode": RM_WH, "TaxCode": tax}]},
        f"Sales order {ITEM} {qty} Nos @ {SELL:,.0f}")
    s = show(run, "Orders", so, "Sales Order")
    dp = run.doc("FIN-ARDP-DPR", "DownPayments", {**head(card, "GPPC/PO/2026/77"),
        "DownPaymentType": "dptRequest", "DownPaymentPercentage": pct, "DocumentLines": [base(17, so)]},
        f"A/R down payment request {pct} % of SO")
    d = show(run, "DownPayments", dp, "A/R Down Payment Request")
    run.doc("FIN-ARDP-RCT1", "IncomingPayments", {"CardCode": card, "DocDate": TODAY, "TransferAccount": BANK,
        "TransferSum": d["DocTotal"], "TransferDate": TODAY, "TransferReference": "NEFT-ARDP-ADV",
        "Remarks": "AKE finance demo - advance from customer",
        "PaymentInvoices": [{"DocEntry": dp["DocEntry"], "SumApplied": d["DocTotal"], "InvoiceType": "it_DownPayment"}]},
        f"Advance received {d['DocTotal']:,.2f}")
    dn = run.doc("FIN-ARDP-DN", "DeliveryNotes", {**head(card, "GPPC/PO/2026/77"), "DocumentLines": [base(17, so)]},
                 f"Delivery {ITEM} {qty} Nos")
    d = run.get("DownPayments", dp["DocEntry"])
    inv = run.doc("FIN-ARDP-INV", "Invoices", {**head(card, "GPPC/PO/2026/77"), "DocumentLines": [base(15, dn)],
        "DownPaymentsToDraw": [{"DocEntry": dp["DocEntry"], "AmountToDraw": d["DocTotal"] - d["VatSum"]}]},
        "A/R invoice drawing the advance")
    i = show(run, "Invoices", inv, "A/R Invoice (after drawing the advance)")
    bal = round(i["DocTotal"] - i["PaidToDate"], 2)
    run.doc("FIN-ARDP-RCT2", "IncomingPayments", {"CardCode": card, "DocDate": TODAY, "TransferAccount": BANK,
        "TransferSum": bal, "TransferDate": TODAY, "TransferReference": "NEFT-ARDP-BAL",
        "Remarks": "AKE finance demo - balance after advance",
        "PaymentInvoices": [{"DocEntry": inv["DocEntry"], "SumApplied": bal, "InvoiceType": "it_Invoice"}]},
        f"Balance received {bal:,.2f} (SO value {s['DocTotal']:,.2f})")
    show(run, "Invoices", inv, "A/R Invoice")


FLOWS = ["JE", "APDP", "ARDP"]

if __name__ == "__main__":
    run = Run()
    for name in sys.argv[1:] or FLOWS:
        print(f"--- {name}")
        globals()[name](run)
