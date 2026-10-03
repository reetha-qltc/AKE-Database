"""Training demo for AKE_DEMO: Procure-to-Pay and Order-to-Cash scenarios on the U1 masters.

P2P  RM001 1,000 KG: Purchase Request -> 3 Purchase Quotations -> comparison -> PO -> GRPO #1 600 KG (validate
     ordered 1000 / received 600 / open 400) -> A/P invoice 600 -> partial vendor payment -> GRPO #2 400 -> A/P invoice 400.
O2C  ABC Developers (C0012), RM001 1,000 KG + SF001 20 Nos: Sales Quotation -> Sales Order -> Delivery #1 (RM001 600
     partial, SF001 20 full) -> open qty 400 -> Return 2 helmets before invoice -> A/R invoice #1 -> payment ->
     Delivery #2 400 (order fully delivered) -> A/R invoice #2 -> A/R credit memo 50 KG -> payment net of credit memo.

Run:  python tools/demo_o2c_p2p.py            (P2P then O2C - the O2C deliveries use the stock received in P2P)
      python tools/demo_o2c_p2p.py P2P        (one scenario)
Posted documents are recorded in logs/txn_state.json (keys P2P-* / O2C-*), so a re-run continues where it stopped.
"""
import sys

import demo_transactions as T

BANK = T.BANK
RM_WH, MAIN_WH, REJ_WH = "U1WH02", "U1WH01", "U1WH04"
# posting dates tell the story in order; each date needs the demo USD rate (system currency)
D = {"PR": "2026-09-21", "PQ": "2026-09-22", "PO": "2026-09-24", "GRN1": "2026-09-26", "PAY": "2026-09-29",
     "GRN2": "2026-10-01", "SQ": "2026-09-25", "SO": "2026-09-26", "DN1": "2026-09-28", "RET": "2026-09-29",
     "INV1": "2026-09-29", "RCT1": "2026-09-30", "DN2": "2026-10-01", "INV2": "2026-10-01", "CM": "2026-10-02",
     "RCT2": "2026-10-02"}
QUOTES = [("V0010", 62.00, "2026-09-30"), ("V0001", 64.00, "2026-10-03"), ("V0002", 63.50, "2026-10-05")]  # vendor, rate, delivery


class Run(T.Run):
    def __init__(self):
        super().__init__()
        for d in sorted(set(D.values())):
            r = self.sl.s.post(f"{self.sl.base}/SBOBobService_SetCurrencyRate", timeout=60,
                               json={"Currency": "USD", "Rate": str(T.USD_RATE), "RateDate": d.replace("-", "")})
            if r.status_code not in (200, 204):
                raise SystemExit(f"FAIL USD rate {d}: {r.text[:300]}")
        uom = self.sl.get("UnitOfMeasurements?$select=AbsEntry,Code")["value"]
        self.uom = {u["Code"]: u["AbsEntry"] for u in uom}

    def gst18(self, card):
        """Karnataka party (same state as AKE) -> CGST 9% + SGST 9%, other states -> IGST 18%."""
        if card not in self.state.setdefault("_bp_state", {}):
            adr = self.sl.get(f"BusinessPartners('{card}')?$select=BPAddresses")["BPAddresses"]
            self.state["_bp_state"][card] = next(a["State"] for a in adr if a["AddressType"] == "bo_BillTo")
        return "CG+SG@18" if self.state["_bp_state"][card] == "KT" else "IGST@18"

    def close(self, key, entity, entry, label):
        if key in self.state:
            return
        r = self.sl.s.post(f"{self.sl.base}/{entity}({entry})/Close", timeout=120)
        if r.status_code not in (200, 204):
            if self.get(entity, entry)["DocumentStatus"] != "bost_Close":
                raise SystemExit(f"FAIL {key} {label}: {r.json()['error']['message']}")
            label += " - already closed by B1 when the PO was created"
        self.state[key] = {"done": True}
        T.STATE.write_text(T.json.dumps(self.state, indent=1))
        print(f"OK   {key:8s} {label}")


def head(card, ref, d, due=None):
    return {"CardCode": card, "DocDate": D[d], "DocDueDate": due or D[d], "TaxDate": D[d], "NumAtCard": ref,
            "Comments": f"AKE training demo {ref}"}


def base(btype, doc, line, qty=None, **extra):
    l = {"BaseType": btype, "BaseEntry": doc["DocEntry"], "BaseLine": line, **extra}
    return l | ({"Quantity": qty} if qty is not None else {})


def show_lines(run, entity, doc, title):
    """Print ordered / delivered / open per line (what the Open PO / Open SO reports show)."""
    d = run.get(entity, doc["DocEntry"])
    print(f"     {title} #{d['DocNum']} status {d['DocumentStatus']}")
    for l in d["DocumentLines"]:
        done = l["Quantity"] - l["RemainingOpenQuantity"]
        print(f"       {l['ItemCode']:6s} ordered {l['Quantity']:>7,.0f} {l['UoMCode']:4s} | done {done:>7,.0f} | "
              f"open {l['RemainingOpenQuantity']:>7,.0f}")
    return d


def gst_of(run, entity, doc):
    d = run.get(entity, doc["DocEntry"])
    split = (f"CGST 9% {d['VatSum'] / 2:,.2f} + SGST 9% {d['VatSum'] / 2:,.2f}"
             if run.gst18(d["CardCode"]).startswith("CG") else f"IGST 18% {d['VatSum']:,.2f}")
    print(f"     {entity} #{d['DocNum']}: before tax {d['DocTotal'] - d['VatSum']:,.2f} + GST {d['VatSum']:,.2f} "
          f"({split}) = {d['DocTotal']:,.2f}")
    return d


# ------------------------------------------------------------------------------------------------ Procure to Pay
def P2P(run):
    kg = run.uom["KG"]  # RM001 is bought in MT by default; the demo works in KG (1 MT = 1000 KG)
    pr = run.doc("P2P-PR", "PurchaseRequests", {
        "DocDate": D["PR"], "DocDueDate": "2026-10-21", "TaxDate": D["PR"], "RequriedDate": "2026-09-30",
        "ReqType": 12, "Requester": "manager", "Comments": "AKE training demo P2P - TMT 12mm for fabrication job U1",
        "DocumentLines": [{"ItemCode": "RM001", "Quantity": 1000, "UoMEntry": kg, "WarehouseCode": RM_WH,
                           "RequiredDate": "2026-09-30", "LineVendor": "V0010", "TaxCode": run.gst18("V0010")}]},
        "Purchase Request RM001 1,000 KG")
    pqs = []
    for n, (card, rate, ship) in enumerate(QUOTES, 1):
        pqs.append(run.doc(f"P2P-PQ{n}", "PurchaseQuotations", {
            **head(card, f"P2P-RFQ-{n}", "PQ", due="2026-10-15"), "RequriedDate": ship,
            "DocumentLines": [base(1470000113, pr, 0, 1000, UoMEntry=kg, UnitPrice=rate, TaxCode=run.gst18(card),
                                   WarehouseCode=RM_WH, RequiredDate=ship)]},
            f"Purchase Quotation {card} @ {rate}/KG, delivery {ship}"))
    print("     Quotation comparison (RM001 1,000 KG):")
    best = None
    for (card, rate, ship), pq in sorted(zip(QUOTES, pqs), key=lambda x: x[0][1]):
        d = run.get("PurchaseQuotations", pq["DocEntry"])
        best = best or (card, pq)
        print(f"       {card:7s} {d['CardName'][:32]:32s} {rate:6.2f}/KG  net {d['DocTotal'] - d['VatSum']:>10,.2f}  "
              f"GST {d['VatSum']:>9,.2f}  total {d['DocTotal']:>10,.2f}  delivery {ship}" + ("  <- lowest" if best[1] is pq else ""))
    card, win = best
    po = run.doc("P2P-PO", "PurchaseOrders", {**head(card, "P2P-PO", "PO", due="2026-09-30"),
                                              "DocumentLines": [base(540000006, win, 0, 1000)]},
                 f"Purchase Order from quotation of {card} (lowest rate)")
    for n, pq in enumerate(pqs, 1):
        if pq is not win:
            run.close(f"P2P-PQ{n}-CLS", "PurchaseQuotations", pq["DocEntry"], f"quotation {n} closed (not selected)")
    run.close("P2P-PR-CLS", "PurchaseRequests", pr["DocEntry"], "purchase request closed (ordered)")
    grn1 = run.doc("P2P-GRN1", "PurchaseDeliveryNotes", {**head(card, "P2P-GRN1", "GRN1"),
                                                         "DocumentLines": [base(22, po, 0, 600)]}, "GRPO #1 600 KG")
    show_lines(run, "PurchaseOrders", po, "Validation after GRPO #1 - PO")
    inv1 = run.doc("P2P-PINV1", "PurchaseInvoices", {**head(card, "P2P-BILL-1", "GRN1", due="2026-10-26"),
                                                     "DocumentLines": [base(20, grn1, 0)]}, "A/P invoice for GRPO #1 (600 KG)")
    i1 = gst_of(run, "PurchaseInvoices", inv1)
    part = 25000.00
    run.doc("P2P-PAY1", "VendorPayments", {"CardCode": card, "DocDate": D["PAY"], "TransferAccount": BANK,
        "TransferSum": part, "TransferDate": D["PAY"], "TransferReference": "NEFT-P2P-1",
        "Remarks": "AKE training demo - part payment of A/P invoice 1",
        "PaymentInvoices": [{"DocEntry": inv1["DocEntry"], "SumApplied": part, "InvoiceType": "it_PurchaseInvoice"}]},
        f"Partial vendor payment {part:,.2f} of {i1['DocTotal']:,.2f}")
    d = run.get("PurchaseInvoices", inv1["DocEntry"])
    print(f"     A/P invoice #{d['DocNum']}: total {d['DocTotal']:,.2f}, paid {d['PaidToDate']:,.2f}, "
          f"balance {d['DocTotal'] - d['PaidToDate']:,.2f}, status {d['DocumentStatus']}")
    grn2 = run.doc("P2P-GRN2", "PurchaseDeliveryNotes", {**head(card, "P2P-GRN2", "GRN2"),
                                                         "DocumentLines": [base(22, po, 0, 400)]}, "GRPO #2 400 KG")
    inv2 = run.doc("P2P-PINV2", "PurchaseInvoices", {**head(card, "P2P-BILL-2", "GRN2", due="2026-10-31"),
                                                     "DocumentLines": [base(20, grn2, 0)]}, "A/P invoice for GRPO #2 (400 KG)")
    gst_of(run, "PurchaseInvoices", inv2)
    show_lines(run, "PurchaseOrders", po, "After GRPO #2 - PO")


# ------------------------------------------------------------------------------------------------ Order to Cash
def O2C(run):
    card = "C0012"
    run.doc("O2C-GR", "InventoryGenEntries", {"DocDate": D["SQ"], "Reference2": "O2C",
        "Comments": "AKE training demo O2C - opening stock of safety helmets",
        "DocumentLines": [{"ItemCode": "SF001", "Quantity": 25, "UnitPrice": 180, "WarehouseCode": MAIN_WH}]},
        "Goods Receipt SF001 25 Nos (stock for the demo)")
    sq = run.doc("O2C-SQ", "Quotations", {**head(card, "ABC/PO-REQ/118", "SQ", due="2026-10-10"), "DocumentLines": [
        {"ItemCode": "RM001", "Quantity": 1000, "UoMEntry": run.uom["KG"], "UnitPrice": 68, "WarehouseCode": RM_WH, "TaxCode": run.gst18(card)},
        {"ItemCode": "SF001", "Quantity": 20, "UnitPrice": 250, "WarehouseCode": MAIN_WH, "TaxCode": run.gst18(card)}]},
        "Sales Quotation RM001 1,000 KG @ 68 + SF001 20 Nos @ 250")
    so = run.doc("O2C-SO", "Orders", {**head(card, "ABC/PO/2026/118", "SO", due="2026-10-05"),
                                      "DocumentLines": [base(23, sq, 0), base(23, sq, 1)]}, "Sales Order from quotation")
    dn1 = run.doc("O2C-DN1", "DeliveryNotes", {**head(card, "ABC/PO/2026/118", "DN1"),
                                               "DocumentLines": [base(17, so, 0, 600), base(17, so, 1, 20)]},
                  "Delivery #1: RM001 600 KG (partial) + SF001 20 Nos (full)")
    show_lines(run, "Orders", so, "After delivery #1 - Sales Order")
    ret = run.doc("O2C-RET", "Returns", {**head(card, "ABC/RET/07", "RET"), "Comments": "2 helmets cracked - returned before invoicing",
                                         "DocumentLines": [base(15, dn1, 1, 2, WarehouseCode=REJ_WH)]},
                  "Return before invoice: SF001 2 Nos to Rejected Warehouse")
    show_lines(run, "DeliveryNotes", dn1, "Delivery #1 after the return (open = still to invoice)")
    inv1 = run.doc("O2C-INV1", "Invoices", {**head(card, "ABC/PO/2026/118", "INV1", due="2026-10-29"),
                                            "DocumentLines": [base(15, dn1, 0, 600), base(15, dn1, 1, 18)]},
                   "A/R invoice #1 from delivery #1 (600 KG + 18 Nos)")
    i1 = gst_of(run, "Invoices", inv1)
    run.doc("O2C-RCT1", "IncomingPayments", {"CardCode": card, "DocDate": D["RCT1"], "TransferAccount": BANK,
        "TransferSum": i1["DocTotal"], "TransferDate": D["RCT1"], "TransferReference": "NEFT-ABC-1",
        "Remarks": "AKE training demo - ABC Developers payment for invoice 1",
        "PaymentInvoices": [{"DocEntry": inv1["DocEntry"], "SumApplied": i1["DocTotal"], "InvoiceType": "it_Invoice"}]},
        f"Incoming payment {i1['DocTotal']:,.2f} (invoice #1 in full)")
    dn2 = run.doc("O2C-DN2", "DeliveryNotes", {**head(card, "ABC/PO/2026/118", "DN2"),
                                               "DocumentLines": [base(17, so, 0, 400)]}, "Delivery #2: RM001 remaining 400 KG")
    show_lines(run, "Orders", so, "After delivery #2 - Sales Order (fully delivered)")
    inv2 = run.doc("O2C-INV2", "Invoices", {**head(card, "ABC/PO/2026/118", "INV2", due="2026-10-31"),
                                            "DocumentLines": [base(15, dn2, 0, 400)]}, "A/R invoice #2 from delivery #2 (400 KG)")
    i2 = gst_of(run, "Invoices", inv2)
    cm = run.doc("O2C-CM", "CreditNotes", {**head(card, "ABC/DN/2026/31", "CM"),
                                           "Comments": "50 KG bent bars rejected at site after invoicing",
                                           "DocumentLines": [base(13, inv2, 0, 50, WarehouseCode=REJ_WH)]},
                 "A/R credit memo: RM001 50 KG returned to Rejected Warehouse")
    c = gst_of(run, "CreditNotes", cm)
    # a credit memo copied from the invoice is offset against that invoice by B1 itself (memo closes at once)
    d = run.get("Invoices", inv2["DocEntry"])
    net = round(d["DocTotal"] - d["PaidToDate"], 2)
    print(f"     A/R invoice #{d['DocNum']}: total {d['DocTotal']:,.2f}, credit memo {d['PaidToDate']:,.2f}, open {net:,.2f}")
    run.doc("O2C-RCT2", "IncomingPayments", {"CardCode": card, "DocDate": D["RCT2"], "TransferAccount": BANK,
        "TransferSum": net, "TransferDate": D["RCT2"], "TransferReference": "NEFT-ABC-2",
        "Remarks": "AKE training demo - invoice 2 less credit memo",
        "PaymentInvoices": [{"DocEntry": inv2["DocEntry"], "SumApplied": net, "InvoiceType": "it_Invoice"}]},
        f"Incoming payment {net:,.2f} (invoice #2 {i2['DocTotal']:,.2f} less credit memo {c['DocTotal']:,.2f})")


FLOWS = ["P2P", "O2C"]

if __name__ == "__main__":
    run = Run()
    for f in sys.argv[1:] or FLOWS:
        print(f"--- {f}")
        globals()[f](run)
    print("Done.")
