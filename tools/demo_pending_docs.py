"""Open GRPOs (pending A/P invoice) and open deliveries (pending A/R invoice) for the reports (user request 2026-10-07).

Purchase  8 AKE vendors:   Purchase Order -> GRPO (full qty), no A/P invoice.  V040 gets an A/P invoice for part of
          its GRPO (1,000 of 2,000 KGS HR plate) to show a partly invoiced receipt.  Priced at AKE's average cost into
          U1 WH1; batch items get batch GRN-<vendor>-<yymmdd>.
Sales     10 AKE customers: Sales Order -> Delivery (full qty) from the finished goods in U1 WH5, no A/R invoice.
          C011 gets an A/R invoice for 1 of its 2 drum assemblies.  Price = item cost in U1 WH5 + 25 %.
Dates are spread over 18-09 ... 07-10-2026 so the reports show different ages.  GST: Karnataka party -> CG+SG@18,
other state -> IGST@18.  Shows in PAR - 003 / PAR - 004, PTP02 / OTC03.
Run:  python tools/demo_pending_docs.py [V040 C011 ...]
Posted documents are recorded in logs/txn_state.json (keys AKE-<party>-P..), so a re-run continues where it stopped.
"""
import sys

import demo_ake_cycles as C

PWH, SWH, BATCH, MARKUP = "U1 WH1", "U1 WH5", "OB-260401", 1.25
VENDORS = {  # card: (PO date, GRPO date, vendor DC, [(item, qty)])
    "V040": ("2026-09-15", "2026-09-18", "DSI/DC/26-27/0388", [("RMS219932", 2000), ("RMS219920", 500)]),  # HR plate, square tube (KGS)
    "V044": ("2026-09-19", "2026-09-24", "ELGI/DC/7781520", [("CON120059", 20), ("CON120058", 10)]),         # compressor lube oil (LTR)
    "V051": ("2026-09-25", "2026-09-26", "GSTG/DC/1142", [("CON120076", 10), ("CON120074", 5)]),            # LPG cylinders
    "V052": ("2026-09-26", "2026-09-29", "GEC/DC/0597", [("SPO250008", 100), ("SPO250061", 20)]),          # armoured cable (m), cable gland
    "V057": ("2026-09-29", "2026-10-01", "GPC/BLR/DC/2213", [("CON120214", 200), ("CON120321", 60)]),      # primer, epoxy thinner (LTR)
    "V063": ("2026-09-30", "2026-10-03", "HHPL/DC/26-27/419", [("CON120166", 210), ("CON120165", 210)]),   # hydraulic oil (LTR)
    "V071": ("2026-10-03", "2026-10-06", "INDIGO/DC/0815", [("RMS219921", 1000), ("RMS219910", 600)]),     # rect / square tube (KGS)
    "V074": ("2026-10-05", "2026-10-07", "IBC/DC/3364", [("CON120141", 500), ("CON120150", 500), ("CON120205", 500)]),  # bolts, nuts, washers M12
}
CUSTOMERS = {  # card: (SO date, delivery date, customer PO, [(item, qty)])
    "C011": ("2026-09-14", "2026-09-18", "CGY/PO/26-27/0291", [("101100000713", 2), ("101020000470", 2)]),  # drum assy Argo 2300, sliding gate bucket
    "C012": ("2026-09-17", "2026-09-22", "CHPL/PO/4471", [("100248165", 3)]),                              # G330N stick boom
    "C013": ("2026-09-20", "2026-09-24", "JIDOKA/PO/2026/118", [("6237714", 2), ("6236614", 5)]),          # stator frame 4X, service cover
    "C016": ("2026-09-22", "2026-09-26", "CGYIM/PO/0733", [("101100009099", 2), ("65001585", 1)]),         # loading arm A3000, drum 8 m3
    "C017": ("2026-09-25", "2026-09-29", "ASARA/PO/26-27/052", [("101040000821", 1), ("L.027.236", 2)]),   # drum A4800, hopper Argo 1000
    "C018": ("2026-09-27", "2026-10-01", "OWM/PO/2026/0610", [("10014143559", 1), ("AVOMEGA0013", 2)]),     # tub frame 560 H/G, main conveyor
    "C021": ("2026-09-29", "2026-10-03", "RRPS/PO/1187", [("21091125", 5), ("21064825", 4)]),              # terminal box, end shield NDE
    "C022": ("2026-10-01", "2026-10-05", "VFE/PO/26-27/077", [("113-010-W-02", 4), ("J1065T1", 1)]),       # hopper side, hopper assy
    "C026": ("2026-10-02", "2026-10-06", "ZE/PO/2026/0094", [("80217336", 2)]),                            # mixing trough (TN, IGST)
    "C029": ("2026-10-03", "2026-10-07", "MRK/PO/0412", [("S0000230", 5), ("AN3 /24 /071", 2)]),           # gear box support, BM1 fabrication
}
PART_PINV = {"V040": (0, 1000, "2026-10-01", "DSI/INV/26-27/1129")}  # vendor: (GRPO line, qty, date, bill no)
PART_INV = {"C011": (0, 1, "2026-09-25")}                           # customer: (delivery line, qty, date)


def head(card, ref, d, due=None, note="pending"):
    return {"CardCode": card, "DocDate": d, "DocDueDate": due or d, "TaxDate": d, "NumAtCard": ref,
            "Comments": f"AKE demo {note} {card} - {ref}"}


def set_rates(run, dates):
    for d in sorted(dates):  # system currency USD: every posting date needs a rate
        r = run.sl.s.post(f"{run.sl.base}/SBOBobService_SetCurrencyRate", timeout=60,
                          json={"Currency": "USD", "Rate": str(C.T.USD_RATE), "RateDate": d.replace("-", "")})
        if r.status_code not in (200, 204):
            raise SystemExit(f"FAIL USD rate {d}: {r.text[:300]}")


def purchase(run, card):
    pod, grd, ref, lines = VENDORS[card]
    name, tax = run.tax(card)
    print(f"--- {card} {name} ({tax})")
    for code, _ in lines:
        if run.item(code)["PurchaseItem"] != "tYES" or not run.cost.get(code):
            raise SystemExit(f"{card}: {code} is not a purchase item or has no AKE cost")
    k = f"AKE-{card}-P"
    po = run.doc(k + "PO", "PurchaseOrders", {**head(card, ref.replace("/DC/", "/SO/", 1), pod, due=grd), "DocumentLines": [
        {"ItemCode": c, "Quantity": q, "UnitPrice": round(run.cost[c], 2), "WarehouseCode": PWH, "TaxCode": tax}
        for c, q in lines]}, "Purchase Order " + ", ".join(f"{c} x {q}" for c, q in lines))
    batch = lambda i: ({"BatchNumbers": [{"BatchNumber": f"GRN-{card}-{grd[2:].replace('-', '')}", "Quantity": lines[i][1]}]}
                       if run.item(lines[i][0])["ManageBatchNumbers"] == "tYES" else {})
    grn = run.doc(k + "GRN", "PurchaseDeliveryNotes", {**head(card, ref, grd), "DocumentLines": C.copy(22, po, len(lines), batch)},
                  "GRPO from purchase order (full quantity, not invoiced)")
    print(f"     PO #{po['DocNum']}  GRPO #{grn['DocNum']}: {C.total(run, 'PurchaseDeliveryNotes', grn)}")
    if card in PART_PINV:
        line, qty, d, bill = PART_PINV[card]
        inv = run.doc(k + "PINV", "PurchaseInvoices", {**head(card, bill, d, due="2026-10-31", note="partial invoice"),
                      "DocumentLines": [{"BaseType": 20, "BaseEntry": grn["DocEntry"], "BaseLine": line, "Quantity": qty}]},
                      f"A/P Invoice for {qty} of GRPO line {line}")
        print(f"     A/P Invoice #{inv['DocNum']} (part): {C.total(run, 'PurchaseInvoices', inv)}")


def sales(run, card):
    sod, dnd, ref, lines = CUSTOMERS[card]
    name, tax = run.tax(card)
    print(f"--- {card} {name} ({tax})")
    body = []
    for code, qty in lines:
        it = run.item(code)
        w = next(w for w in it["ItemWarehouseInfoCollection"] if w["WarehouseCode"] == SWH)
        if it["SalesItem"] != "tYES" or w["InStock"] < qty or not w["StandardAveragePrice"]:
            raise SystemExit(f"{card}: {code} not a sales item / {w['InStock']} in {SWH} (need {qty}) / cost {w['StandardAveragePrice']}")
        body.append({"ItemCode": code, "Quantity": qty, "UnitPrice": round(w["StandardAveragePrice"] * MARKUP),
                     "WarehouseCode": SWH, "TaxCode": tax})
    k = f"AKE-{card}-P"
    so = run.doc(k + "SO", "Orders", {**head(card, ref, sod, due=dnd), "DocumentLines": body},
                 "Sales Order " + ", ".join(f"{c} x {q}" for c, q in lines))
    batch = lambda i: ({"BatchNumbers": [{"BatchNumber": BATCH, "Quantity": lines[i][1]}]}
                       if run.item(lines[i][0])["ManageBatchNumbers"] == "tYES" else {})
    dn = run.doc(k + "DN", "DeliveryNotes", {**head(card, ref, dnd), "DocumentLines": C.copy(17, so, len(lines), batch)},
                 "Delivery from sales order (full quantity, not invoiced)")
    print(f"     SO #{so['DocNum']}  Delivery #{dn['DocNum']}: {C.total(run, 'DeliveryNotes', dn)}")
    if card in PART_INV:
        line, qty, d = PART_INV[card]
        inv = run.doc(k + "INV", "Invoices", {**head(card, ref, d, due="2026-10-25", note="partial invoice"),
                      "DocumentLines": [{"BaseType": 15, "BaseEntry": dn["DocEntry"], "BaseLine": line, "Quantity": qty}]},
                      f"A/R Invoice for {qty} of delivery line {line}")
        print(f"     A/R Invoice #{inv['DocNum']} (part): {C.total(run, 'Invoices', inv)}")


if __name__ == "__main__":
    run = C.Run()
    set_rates(run, {d for v in VENDORS.values() for d in v[:2]} | {d for v in CUSTOMERS.values() for d in v[:2]}
              | {v[2] for v in PART_PINV.values()} | {v[2] for v in PART_INV.values()})
    for p in sys.argv[1:] or [*VENDORS, *CUSTOMERS]:
        (sales if p.startswith("C") else purchase)(run, p)
    print("Done.")
