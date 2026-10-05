"""Full sales and purchase cycles for AKE's first 10 real customers (C001-C010) and vendors (V001-V010) in AKE_DEMO.

Sales     per customer: Sales Quotation -> Sales Order -> Delivery -> A/R Invoice (each copied from the previous one)
Purchase  per vendor:   Purchase Request -> Purchase Quotation -> Purchase Order -> GRPO -> A/P Invoice
Items fit the party (drum parts for Ajax, stator frames for WEG / L&T, paint for Aaruda Paints, bearings for Accurate
Bearing ...).  Sales come from AKE's stock in U1 WH1 (tools/load_ake_stock.py) at AKE's average cost + 25 %; purchases
are priced at AKE's average cost and received into U1 WH1.  GST: Karnataka party -> CG+SG@18, other state -> IGST@18,
export (C007 WEG Euro, Portugal) -> IGST@0.  Batch items: deliveries draw batch OB-260401, GRPOs create GRN-<vendor>.

Run:  python tools/demo_ake_cycles.py                 (all)
      python tools/demo_ake_cycles.py C003 V004       (selected parties)
Posted documents are recorded in logs/txn_state.json (keys AKE-<party>-<doc>), so a re-run continues where it stopped.
"""
import sys

import demo_transactions as T
import load_ake_stock as S

WH, BATCH, MARKUP = "U1 WH1", "OB-260401", 1.25
D = {"PR": "2026-09-28", "PQ": "2026-09-29", "PO": "2026-09-30", "GRN": "2026-10-02", "PINV": "2026-10-03",
     "SQ": "2026-09-29", "SO": "2026-09-30", "DN": "2026-10-03", "INV": "2026-10-05"}

CUSTOMERS = {  # card: (customer PO, [(item, qty)])
    "C001": ("AJAX/PO/26-27/0412", [("101010000151", 2), ("101010000168", 4)]),          # drum assembly, roller ring
    "C002": ("BIPL/4500178823", [("101010000184", 20), ("101010000159", 100)]),          # roller brackets, gaskets
    "C003": ("ME/PO/118", [("CON120082", 200), ("CON120064", 300)]),                     # grinding wheels, flap discs
    "C004": ("WIPL/PO/7700451", [("101020000649", 2), ("094.025", 4)]),                  # drum base frame, support ring
    "C005": ("HOM/PO/2026/066", [("101010020018", 20), ("101010020013", 20)]),           # bucket mounting plate, bush
    "C006": ("LT/HED/PO/24519", [("11031526", 1), ("6236614", 10)]),                     # TD125 stator frame, cover
    "C007": ("WEG-EU/PO/4511873", [("11051525F", 2), ("6235028A", 5)]),                   # export: stator frame, cover
    "C008": ("WEGI/PO/3300981", [("10004974851-06", 5), ("10005613030-19", 10)]),        # endshield cyl., foot support
    "C009": ("BEML/MM/PO/88213", [("101020000700", 2), ("101010000152", 5)]),            # swivel drum frame, dish assy
    "C010": ("NBT/PO/2026/31", [("PPE180010", 20), ("PPE180017", 50)]),                  # safety shoes, goggles
}
VENDORS = {  # card: (vendor quotation ref, [(item, qty)])
    "V001": ("AARUDA/Q/261", [("CON120213", 200), ("CON120175", 40)]),                   # primer, enamel paint (LTR)
    "V002": ("ACCFIN/Q/0915", [("OFS170001", 10), ("OFS170008", 20)]),                   # cartridge refill, report books
    "V003": ("ARC/Q/2026/77", [("PPE180004", 10), ("PPE180005", 25)]),                   # safety harness, apron
    "V004": ("ABC/Q/1182", [("CON120455", 4), ("SPO250014", 20)]),                       # SKF 6312 2Z, 6205ZZ bearings
    "V005": ("ADD/Q/339", [("CON120002", 500), ("CON120119", 100)]),                     # cable ties, insulation tape
    "V006": ("ADRTEK/Q/0072", [("SPO250005", 20), ("SPO250007", 20)]),                  # contactor add-on blocks
    "V007": ("AJAXE/SP/Q/5521", [("SPO250002", 2), ("SPO250004", 5)]),                   # speed switch, LPG adaptor
    "V008": ("ALLOY/Q/26-27/14", [("CON120236", 500), ("CON120234", 300)]),              # MIG / SAW welding wire (KGS)
    "V009": ("ATC/Q/2026/208", [("CP24652500030", 2000), ("CT2063200100008", 1000)]),     # HR cut plate, ERW tube (KGS)
    "V010": ("AMCO/Q/0931", [("0231.000016", 100), ("2610.000302", 50)]),                # M30 nyloc nut, grease nipple
}


class Run(T.Run):
    def __init__(self):
        super().__init__()
        for d in sorted(set(D.values())):  # system currency USD: every posting date needs a rate
            r = self.sl.s.post(f"{self.sl.base}/SBOBobService_SetCurrencyRate", timeout=60,
                               json={"Currency": "USD", "Rate": str(T.USD_RATE), "RateDate": d.replace("-", "")})
            if r.status_code not in (200, 204):
                raise SystemExit(f"FAIL USD rate {d}: {r.text[:300]}")
        self.cost = {c: p for c, (p, q) in S.parse().items()}
        self.items = {}

    def item(self, code):
        if code not in self.items:
            self.items[code] = self.sl.get(f"Items('{code}')?$select=ItemCode,ItemName,SalesItem,PurchaseItem,"
                                           "ManageBatchNumbers,ItemWarehouseInfoCollection")
        return self.items[code]

    def tax(self, card):
        bp = self.sl.get(f"BusinessPartners('{card}')?$select=CardName,BPAddresses")
        adr = next(a for a in bp["BPAddresses"] if a["AddressType"] == "bo_BillTo")
        code = "IGST@0" if adr["Country"] != "IN" else "CG+SG@18" if adr["State"] == "KT" else "IGST@18"
        return bp["CardName"], code


def head(card, ref, d, due=None):
    return {"CardCode": card, "DocDate": D[d], "DocDueDate": due or D[d], "TaxDate": D[d], "NumAtCard": ref,
            "Comments": f"AKE demo cycle {card} - {ref}"}


def copy(btype, doc, n, extra):
    return [{"BaseType": btype, "BaseEntry": doc["DocEntry"], "BaseLine": i, **extra(i)} for i in range(n)]


def total(run, entity, doc):
    d = run.get(entity, doc["DocEntry"])
    return f"net {d['DocTotal'] - d['VatSum']:,.2f} + GST {d['VatSum']:,.2f} = {d['DocTotal']:,.2f}"


def sales(run, card):
    ref, lines = CUSTOMERS[card]
    name, tax = run.tax(card)
    print(f"--- {card} {name} ({tax})")
    body = []
    for code, qty in lines:
        it = run.item(code)
        stock = next(w["InStock"] for w in it["ItemWarehouseInfoCollection"] if w["WarehouseCode"] == WH)
        if it["SalesItem"] != "tYES" or stock < qty:
            raise SystemExit(f"{card}: {code} is not a sales item or has only {stock} in {WH} (need {qty})")
        body.append({"ItemCode": code, "Quantity": qty, "UnitPrice": round(run.cost[code] * MARKUP),
                     "WarehouseCode": WH, "TaxCode": tax})
    k = f"AKE-{card}-"
    sq = run.doc(k + "SQ", "Quotations", {**head(card, ref.replace("/PO/", "/ENQ/", 1), "SQ", due="2026-10-15"),
                                          "DocumentLines": body}, "Sales Quotation " + ", ".join(f"{c} x {q}" for c, q in lines))
    so = run.doc(k + "SO", "Orders", {**head(card, ref, "SO", due="2026-10-03"),
                                      "DocumentLines": copy(23, sq, len(lines), lambda i: {})}, "Sales Order from quotation")
    batch = lambda i: ({"BatchNumbers": [{"BatchNumber": BATCH, "Quantity": lines[i][1]}]}
                       if run.item(lines[i][0])["ManageBatchNumbers"] == "tYES" else {})
    dn = run.doc(k + "DN", "DeliveryNotes", {**head(card, ref, "DN"), "DocumentLines": copy(17, so, len(lines), batch)},
                 "Delivery from sales order (full quantity)")
    inv = run.doc(k + "INV", "Invoices", {**head(card, ref, "INV", due="2026-11-04"),
                                          "DocumentLines": copy(15, dn, len(lines), lambda i: {})}, "A/R Invoice from delivery")
    print(f"     A/R Invoice #{inv['DocNum']}: {total(run, 'Invoices', inv)}")


def purchase(run, card):
    ref, lines = VENDORS[card]
    name, tax = run.tax(card)
    print(f"--- {card} {name} ({tax})")
    for code, _ in lines:
        if run.item(code)["PurchaseItem"] != "tYES":
            raise SystemExit(f"{card}: {code} is not a purchase item")
    k = f"AKE-{card}-"
    pr = run.doc(k + "PR", "PurchaseRequests", {
        "DocDate": D["PR"], "DocDueDate": "2026-10-28", "TaxDate": D["PR"], "RequriedDate": "2026-10-02",
        "ReqType": 12, "Requester": "manager", "Comments": f"AKE demo cycle {card} - stores requirement U1",
        "DocumentLines": [{"ItemCode": c, "Quantity": q, "WarehouseCode": WH, "RequiredDate": "2026-10-02",
                           "LineVendor": card, "TaxCode": tax} for c, q in lines]},
        "Purchase Request " + ", ".join(f"{c} x {q}" for c, q in lines))
    pq = run.doc(k + "PQ", "PurchaseQuotations", {**head(card, ref, "PQ", due="2026-10-15"), "RequriedDate": "2026-10-02",
        "DocumentLines": copy(1470000113, pr, len(lines), lambda i: {  # quoted qty is not copied from the request
            "Quantity": lines[i][1], "UnitPrice": round(run.cost[lines[i][0]], 2), "TaxCode": tax, "RequiredDate": "2026-10-02"})},
        "Purchase Quotation from request (AKE average cost)")
    po = run.doc(k + "PO", "PurchaseOrders", {**head(card, ref.replace("/Q/", "/PO/", 1), "PO", due="2026-10-02"),
                                              "DocumentLines": copy(540000006, pq, len(lines), lambda i: {})},
                 "Purchase Order from quotation")
    batch = lambda i: ({"BatchNumbers": [{"BatchNumber": f"GRN-{card}-261002", "Quantity": lines[i][1]}]}
                       if run.item(lines[i][0])["ManageBatchNumbers"] == "tYES" else {})
    grn = run.doc(k + "GRN", "PurchaseDeliveryNotes", {**head(card, f"DC-{ref.split('/')[0]}-{card}", "GRN"),
                                                       "DocumentLines": copy(22, po, len(lines), batch)},
                  "GRPO from purchase order (full quantity)")
    inv = run.doc(k + "PINV", "PurchaseInvoices", {**head(card, f"{ref.split('/')[0]}/INV/26-27/{card[1:]}", "PINV",
                                                          due="2026-11-02"),
                                                   "DocumentLines": copy(20, grn, len(lines), lambda i: {})},
                  "A/P Invoice from GRPO")
    print(f"     A/P Invoice #{inv['DocNum']}: {total(run, 'PurchaseInvoices', inv)}")


if __name__ == "__main__":
    run = Run()
    for p in sys.argv[1:] or [*CUSTOMERS, *VENDORS]:
        (sales if p.startswith("C") else purchase)(run, p)
    print("Done.")
