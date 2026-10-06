"""Five production orders on AKE's real BOMs that show the cases of report PAR - 005 (production orders to be closed).

A  101030000070 Cylinder Mtg Brkt As-Rh x 10      fully issued, fully received, left Released   -> close
B  101100004070 Drum Fabrication x 2              fully issued, fully received, left Released   -> close
C  101030000122 Bucket Pin Mtg Plate Assly-Rh x 10 fully received, Bottom Wear Plate 8 of 10 issued -> close (1 line short)
D  10-MECH-12-8-25/A1/R1F Rail Clamp Bracket x 20 fully issued, 12 of 20 received, due 03-10     -> past due, review
E  101100012777 Loading Arm Argo 2300 x 5         fully issued, nothing received, due 03-10      -> past due, review

Orders 28-09-2026, issue 01-10, receipt 03-10.  Components are issued from U1 WH1 (AKE's stock, batch OB-260401);
order lines are moved there before release.  Sub-assemblies are received into U1 WH4 (WIP, where their parents issue
them from), finished goods into U1 WH5; batch parents on batch PRD-<order no>.  Scrap lines (backflush) and
resources stay as on the BOM.  A and C are standard items: cost set to the sum of their components first
(python tools/set_item_cost.py 101030000070=170.51 101030000122=3095.82 --date 2026-09-28).

Run:  python tools/demo_par005.py [A C ...]
Posted documents are recorded in logs/txn_state.json (keys PAR5-<case>-...), so a re-run continues where it stopped.
"""
import sys

import demo_transactions as T

COMP_WH, BATCH = "U1 WH1", "OB-260401"
D_ORDER, D_ISSUE, D_RCPT = "2026-09-28", "2026-10-01", "2026-10-03"
CASES = {  # case: (product, qty, receipt whse, due date, {component: qty issued if short}, qty received)
    "A": ("101030000070", 10, "U1 WH4", "2026-10-09", {}, 10),
    "B": ("101100004070", 2, "U1 WH5", "2026-10-09", {}, 2),
    "C": ("101030000122", 10, "U1 WH4", "2026-10-09", {"101030000123": 8}, 10),
    "D": ("10-MECH-12-8-25/A1/R1F", 20, "U1 WH4", "2026-10-03", {}, 12),
    "E": ("101100012777", 5, "U1 WH4", "2026-10-03", {}, 0),
}


def case(run, k):
    item, qty, whse, due, short, rcpt = CASES[k]
    key = f"PAR5-{k}"
    print(f"--- {k} {item} x {qty}")
    po = run.doc(f"{key}-PRD", "ProductionOrders", {
        "ItemNo": item, "PlannedQuantity": qty, "PostingDate": D_ORDER, "DueDate": due, "Warehouse": whse,
        "ProductionOrderType": "bopotStandard", "Remarks": f"AKE demo PAR-005 case {k}"}, f"Production order {item} x {qty} -> {whse}")
    entry = po["DocEntry"]
    order = run.get("ProductionOrders", entry)
    lines = [{"LineNumber": l["LineNumber"], "Warehouse": COMP_WH} for l in order["ProductionOrderLines"]
             if l["ItemType"] == "pit_Item" and l["PlannedQuantity"] > 0 and l["Warehouse"] != COMP_WH]
    if lines:
        run.patch_once(f"{key}-WH", "ProductionOrders", entry, {"ProductionOrderLines": lines},
                       f"{len(lines)} component lines -> {COMP_WH}")
    run.patch_once(f"{key}-REL", "ProductionOrders", entry, {"ProductionOrderStatus": "boposReleased"}, "released")
    order = run.get("ProductionOrders", entry)
    comp = [l for l in order["ProductionOrderLines"] if l["ItemType"] == "pit_Item" and l["PlannedQuantity"] > 0]
    body = []
    for l in comp:
        q = short.get(l["ItemNo"], l["PlannedQuantity"])
        body.append({"BaseType": 202, "BaseEntry": entry, "BaseLine": l["LineNumber"], "Quantity": q,
                     "WarehouseCode": l["Warehouse"], "BatchNumbers": [{"BatchNumber": BATCH, "Quantity": q}]}
                    if run.sl.get(f"Items('{l['ItemNo']}')?$select=ManageBatchNumbers")["ManageBatchNumbers"] == "tYES"
                    else {"BaseType": 202, "BaseEntry": entry, "BaseLine": l["LineNumber"], "Quantity": q,
                          "WarehouseCode": l["Warehouse"]})
    run.doc(f"{key}-ISS", "InventoryGenExits", {"DocDate": D_ISSUE, "Reference2": key,
        "Comments": f"Issue for production #{order['DocumentNumber']} (PAR-005 case {k})", "DocumentLines": body},
        "Issue for production " + ", ".join(f"{b['Quantity']:g}" for b in body))
    if rcpt:
        ln = {"BaseType": 202, "BaseEntry": entry, "Quantity": rcpt, "TransactionType": "botrntComplete", "WarehouseCode": whse}
        if run.sl.get(f"Items('{item}')?$select=ManageBatchNumbers")["ManageBatchNumbers"] == "tYES":
            ln["BatchNumbers"] = [{"BatchNumber": f"PRD-{order['DocumentNumber']}", "Quantity": rcpt}]
        run.doc(f"{key}-RCP", "InventoryGenEntries", {"DocDate": D_RCPT, "Reference2": key,
            "Comments": f"Receipt from production #{order['DocumentNumber']} (PAR-005 case {k})", "DocumentLines": [ln]},
            f"Receipt from production {rcpt} of {qty}")
    d = run.get("ProductionOrders", entry)
    print(f"     Production order #{d['DocumentNumber']} {d['ProductionOrderStatus']}: planned {d['PlannedQuantity']:g}, "
          f"completed {d['CompletedQuantity']:g}, due {d['DueDate'][:10]}")


if __name__ == "__main__":
    run = T.Run()
    for dte in (D_ORDER, D_ISSUE, D_RCPT):  # system currency USD: every posting date needs a rate
        r = run.sl.s.post(f"{run.sl.base}/SBOBobService_SetCurrencyRate", timeout=60,
                          json={"Currency": "USD", "Rate": str(T.USD_RATE), "RateDate": dte.replace("-", "")})
        if r.status_code not in (200, 204):
            raise SystemExit(f"FAIL USD rate {dte}: {r.text[:300]}")
    for k in sys.argv[1:] or CASES:
        case(run, k)
    print("Done.")
