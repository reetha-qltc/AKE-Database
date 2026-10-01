"""Post demo transactions in AKE_DEMO via Service Layer: Purchase, Inventory, Production, Sales (2-3 flows each).

Run:  python tools/demo_transactions.py            (all flows, in order - stock must exist before it is issued/sold)
      python tools/demo_transactions.py P1 S2      (selected flows)
Needs the master data from tools/sl_loader.py. Each posted document is recorded in logs/txn_state.json, so a re-run
skips what is already posted and continues a half-finished flow.
"""
import json, pathlib, sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

STATE = L.LOGS / "txn_state.json"
DATE = date.today().isoformat()
BANK = "5002-02-02-04"          # Kotak Mahindra Bank C/A
PROF_FEES = "4004-07-03"        # Professional & Consultancy Charges
SAC_ENGINEERING = 1             # IndiaSacCode AbsEntry of SAC 998331 Engineering advisory services
USD_RATE = 88.0                 # demo INR per USD (system currency), set for DATE
INTRA, INTER ="CG+SG@18", "IGST@18"
KA = {"V0001", "V0004", "V0005", "V0007", "V0008", "V0009", "C0003"}  # same state as AKE (Karnataka) -> CGST+SGST


class Run:
    def __init__(self):
        L.LOGS.mkdir(exist_ok=True)
        self.state = json.loads(STATE.read_text()) if STATE.exists() else {}
        self.sl = L.SL(L.read_env(), False, print)
        self.sl.login()
        # AKE_DEMO's system currency is USD: B1 refuses documents on a date without a USD rate (demo value)
        r = self.sl.s.post(f"{self.sl.base}/SBOBobService_SetCurrencyRate", timeout=60,
                           json={"Currency": "USD", "Rate": str(USD_RATE), "RateDate": DATE.replace("-", "")})
        if r.status_code not in (200, 204):
            raise SystemExit(f"FAIL USD rate: {r.text[:300]}")

    def doc(self, key, entity, body, label):
        """POST once; returns {'DocEntry', 'DocNum'} (from state on re-run)."""
        if key in self.state:
            return self.state[key]
        r = self.sl.s.post(f"{self.sl.base}/{entity}", json=body, timeout=300)
        if r.status_code not in (200, 201):
            raise SystemExit(f"FAIL {key} {entity} {label}: {r.json()['error']['message']}")
        j = r.json()
        rec = {"DocEntry": j.get("DocEntry") or j.get("AbsoluteEntry") or j.get("DocNum"), "DocNum": j.get("DocNum") or j.get("DocumentNumber"),
               "Entity": entity}
        self.state[key] = rec
        STATE.write_text(json.dumps(self.state, indent=1))
        print(f"OK   {key:8s} {entity:24s} #{rec['DocNum']} {label}")
        return rec

    def get(self, entity, entry):
        return self.sl.get(f"{entity}({entry})")

    def patch_once(self, key, entity, entry, body, label):
        if key in self.state:
            return
        r = self.sl.s.patch(f"{self.sl.base}/{entity}({entry})", json=body, timeout=120)
        if r.status_code not in (200, 204):
            raise SystemExit(f"FAIL {key} {label}: {r.json()['error']['message']}")
        self.state[key] = {"done": True}
        STATE.write_text(json.dumps(self.state, indent=1))
        print(f"OK   {key:8s} {label}")


def lines(card, items):
    tax = INTRA if card in KA else INTER
    return [{"ItemCode": i, "Quantity": q, "UnitPrice": p, "WarehouseCode": w, "TaxCode": tax} for i, q, p, w in items]


def copy(base_type, base, n):
    return [{"BaseType": base_type, "BaseEntry": base["DocEntry"], "BaseLine": i} for i in range(n)]


def head(card, ref):
    return {"CardCode": card, "DocDate": DATE, "DocDueDate": DATE, "TaxDate": DATE, "NumAtCard": ref,
            "Comments": f"AKE demo transaction {ref}"}


# ------------------------------------------------------------------------------------------------ Purchase
def purchase_cycle(run, key, card, items, invoice=True):
    po = run.doc(f"{key}-PO", "PurchaseOrders", {**head(card, key), "DocumentLines": lines(card, items)}, card)
    grn = run.doc(f"{key}-GRN", "PurchaseDeliveryNotes", {**head(card, key), "DocumentLines": copy(22, po, len(items))}, "GRPO from PO")
    if invoice:
        run.doc(f"{key}-PINV", "PurchaseInvoices", {**head(card, key), "DocumentLines": copy(20, grn, len(items))}, "A/P invoice from GRPO")


def P1(run):  # Karnataka vendor, consumables, CGST+SGST
    purchase_cycle(run, "P1", "V0004", [("CN-ELEC-E6013", 50, 165, "CONS"), ("CN-MIG-ER70", 100, 140, "CONS"),
                                        ("CN-PRIMER", 60, 210, "CONS"), ("CN-ENAMEL", 50, 290, "CONS")])


def P2(run):  # Tamil Nadu vendor, raw material, IGST
    purchase_cycle(run, "P2", "V0003", [("RM-PL-0020", 1000, 60, "RM-STR"), ("RM-PL-0012", 500, 61, "RM-STR"),
                                        ("RM-ST-MB300", 1500, 58, "RM-STR"), ("RM-ST-A50", 500, 56, "RM-STR")])


def P3(run):  # service invoice with TDS 194J (vendor V0009 carries WT code J10)
    run.doc("P3-PINV", "PurchaseInvoices", {
        **head("V0009", "P3"), "DocType": "dDocument_Service",
        "WithholdingTaxDataCollection": [{"WTCode": "J10"}],  # B1 does not add the BP's WT code on its own via SL
        "DocumentLines": [{"ItemDescription": "Structural design check - Pipe rack module", "AccountCode": PROF_FEES,
                           "LineTotal": 60000, "TaxCode": INTRA, "WTLiable": "tYES",
                           "LocationCode": 1, "SACEntry": SAC_ENGINEERING}]}, "service invoice with TDS J10")


# ------------------------------------------------------------------------------------------------ Inventory
def I1(run):
    run.doc("I1-GR", "InventoryGenEntries", {"DocDate": DATE, "Reference2": "I1", "Comments": "AKE demo - stock found in physical count",
        "DocumentLines": [{"ItemCode": i, "Quantity": q, "UnitPrice": p, "WarehouseCode": "CONS"}
                          for i, q, p in [("PPE-HELMET", 20, 180), ("PPE-SHOE", 10, 950), ("CN-GRIND-4", 50, 38)]]}, "Goods Receipt")


def I2(run):
    run.doc("I2-TRF", "StockTransfers", {"DocDate": DATE, "FromWarehouse": "CONS", "ToWarehouse": "SITE",
        "Comments": "AKE demo - consumables to project site",
        "StockTransferLines": [{"ItemCode": i, "Quantity": q, "FromWarehouseCode": "CONS", "WarehouseCode": "SITE"}
                               for i, q in [("CN-ELEC-E6013", 10), ("CN-GRIND-4", 20), ("PPE-HELMET", 5)]]}, "Inventory Transfer CONS -> SITE")


def I3(run):
    run.doc("I3-GI", "InventoryGenExits", {"DocDate": DATE, "Reference2": "I3", "Comments": "AKE demo - site consumption",
        "DocumentLines": [{"ItemCode": i, "Quantity": q, "WarehouseCode": "SITE"}
                          for i, q in [("CN-ELEC-E6013", 2), ("CN-GRIND-4", 6)]]}, "Goods Issue from SITE")


# ------------------------------------------------------------------------------------------------ Production
def production(run, key, item, qty):
    po = run.doc(f"{key}-PRD", "ProductionOrders", {"ItemNo": item, "PlannedQuantity": qty, "PostingDate": DATE,
        "DueDate": DATE, "ProductionOrderType": "bopotStandard", "Remarks": f"AKE demo {key}"}, f"{item} x {qty}")
    entry = po["DocEntry"]
    run.patch_once(f"{key}-REL", "ProductionOrders", entry, {"ProductionOrderStatus": "boposReleased"}, "released")
    order = run.get("ProductionOrders", entry)
    comp = [l for l in order["ProductionOrderLines"] if l["ItemType"] == "pit_Item"]
    run.doc(f"{key}-ISS", "InventoryGenExits", {"DocDate": DATE, "Reference2": key, "Comments": f"Issue for production {key}",
        "DocumentLines": [{"BaseType": 202, "BaseEntry": entry, "BaseLine": l["LineNumber"], "Quantity": l["PlannedQuantity"],
                           "WarehouseCode": l["Warehouse"]} for l in comp]}, f"Issue for production ({len(comp)} components)")
    run.doc(f"{key}-RCP", "InventoryGenEntries", {"DocDate": DATE, "Reference2": key, "Comments": f"Receipt from production {key}",
        "DocumentLines": [{"BaseType": 202, "BaseEntry": entry, "Quantity": qty, "TransactionType": "botrntComplete"}]},
        f"Receipt from production {item} x {qty}")
    run.patch_once(f"{key}-CLS", "ProductionOrders", entry, {"ProductionOrderStatus": "boposClosed"}, "closed")


def PR1(run):
    production(run, "PR1", "SA-BASEPL-400", 2)


def PR2(run):
    production(run, "PR2", "SA-GUSSET-12", 2)


def PR3(run):  # consumes the sub-assemblies from PR1 + PR2
    production(run, "PR3", "FG-COL-MB300-6M", 2)


# ------------------------------------------------------------------------------------------------ Sales
def S1(run):  # Karnataka customer: Quotation -> SO -> Delivery -> Invoice -> Incoming payment
    card, items = "C0003", [("FG-COL-MB300-6M", 2, 92000, "FG")]
    sq = run.doc("S1-SQ", "Quotations", {**head(card, "S1"), "DocumentLines": lines(card, items)}, card)
    so = run.doc("S1-SO", "Orders", {**head(card, "S1"), "DocumentLines": copy(23, sq, 1)}, "SO from quotation")
    dn = run.doc("S1-DN", "DeliveryNotes", {**head(card, "S1"), "DocumentLines": copy(17, so, 1)}, "Delivery from SO")
    inv = run.doc("S1-INV", "Invoices", {**head(card, "S1"), "DocumentLines": copy(15, dn, 1)}, "A/R invoice from delivery")
    total = run.get("Invoices", inv["DocEntry"])["DocTotal"]
    run.doc("S1-RCT", "IncomingPayments", {"CardCode": card, "DocDate": DATE, "TransferAccount": BANK, "TransferSum": total,
        "TransferDate": DATE, "TransferReference": "NEFT-S1", "Remarks": "AKE demo S1 receipt",
        "PaymentInvoices": [{"DocEntry": inv["DocEntry"], "SumApplied": total, "InvoiceType": "it_Invoice"}]},
        f"Incoming payment {total:,.2f} to Kotak bank")


def S2(run):  # Maharashtra customer: SO -> Delivery -> Invoice (IGST)
    card, items = "C0001", [("RM-ST-MB300", 500, 66, "RM-STR")]
    so = run.doc("S2-SO", "Orders", {**head(card, "S2"), "DocumentLines": lines(card, items)}, card)
    dn = run.doc("S2-DN", "DeliveryNotes", {**head(card, "S2"), "DocumentLines": copy(17, so, 1)}, "Delivery from SO")
    run.doc("S2-INV", "Invoices", {**head(card, "S2"), "DocumentLines": copy(15, dn, 1)}, "A/R invoice from delivery")


def S3(run):  # Tamil Nadu customer: direct A/R invoice (IGST)
    card = "C0002"
    run.doc("S3-INV", "Invoices", {**head(card, "S3"), "DocumentLines": lines(card, [("RM-PL-0020", 300, 70, "RM-STR")])},
            "direct A/R invoice")


def gst_code(card, rate):
    """Line tax code from the customer's state and the item's GST rate (CG+SG@5, IGST@18 ...)."""
    return f"CG+SG@{rate}" if card in KA else f"IGST@{rate}"


def multi_tax_order(run, key, card, items):
    """Sales order with several items at different GST rates, then a delivery copying every line."""
    body = [{"ItemCode": i, "Quantity": q, "UnitPrice": p, "WarehouseCode": w, "TaxCode": gst_code(card, r)}
            for i, q, p, w, r in items]
    so = run.doc(f"{key}-SO", "Orders", {**head(card, key), "DocumentLines": body},
                 f"{card}: {len(items)} lines, tax codes {sorted({l['TaxCode'] for l in body})}")
    run.doc(f"{key}-DN", "DeliveryNotes", {**head(card, key), "DocumentLines": copy(17, so, len(items))},
            f"Delivery from SO ({len(items)} lines)")


def S4(run):  # Karnataka customer -> CG+SG@18 (steel) and CG+SG@5 (safety shoes)
    multi_tax_order(run, "S4", "C0003", [("RM-PL-0020", 200, 70, "RM-STR", 18), ("RM-ST-MB300", 150, 66, "RM-STR", 18),
                                         ("RM-ST-A50", 100, 65, "RM-STR", 18), ("PPE-SHOE", 4, 1200, "CONS", 5)])


def S5(run):  # Tamil Nadu customer -> IGST@18 (steel) and IGST@5 (safety shoes)
    multi_tax_order(run, "S5", "C0002", [("RM-PL-0020", 150, 70, "RM-STR", 18), ("RM-ST-MB300", 100, 66, "RM-STR", 18),
                                         ("RM-ST-A50", 100, 65, "RM-STR", 18), ("PPE-SHOE", 3, 1200, "CONS", 5)])


FLOWS = ["P1", "P2", "P3", "I1", "I2", "I3", "PR1", "PR2", "PR3", "S1", "S2", "S3", "S4", "S5"]

if __name__ == "__main__":
    run = Run()
    for f in sys.argv[1:] or FLOWS:
        print(f"--- {f}")
        globals()[f](run)
    print("Done.")
