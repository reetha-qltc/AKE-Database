"""Put 50 of every active finished-goods item into U1 WH5 'Finished Goods Warehouse' (user request 2026-10-05).

Items: active inventory items of the item groups named 'Finished Goods*' (Finished Goods, Finished Goods - Rework).
Cost: AKE's average cost from `item master with average Price and Stock.csv`; items without one get a random demo cost
(seeded, so a re-run gives the same values; 500-50,000 rounded to 10).  Standard items are revalued to that cost in
U1 WH5 first; moving-average items take the receipt price.  Posted 2026-04-01 against 1003 Opening Balance Offset,
batch items on batch OB-260401.  The warehouse is renamed to 'Finished Goods Warehouse'.
Idempotent: items that already have stock in U1 WH5 are skipped.
Run:  python tools/load_fg_stock.py [--dry]
"""
import argparse, random, sys

import load_ake_stock as S
import sl_loader as L

WH, NAME, QTY, DATE, OFFSET, BATCH, REF = ("U1 WH5", "Finished Goods Warehouse", 50, "2026-04-01", "1003",
                                           "OB-260401", "AKE-FG-STK")
CHUNK = 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    if sl.get(f"Warehouses('{WH}')?$select=WarehouseName")["WarehouseName"] != NAME:
        sl.dry = a.dry
        sl.patch("Warehouses", WH, {"WarehouseName": NAME}, f"{WH} -> {NAME}")
        sl.dry = False
    cost = {c: p for c, (p, q) in S.parse().items()}
    groups = [g["Number"] for g in S.all_(sl, "ItemGroups?$select=Number,GroupName") if g["GroupName"].startswith("Finished Goods")]
    flt = " or ".join(f"ItemsGroupCode eq {g}" for g in groups)
    items = sorted(S.all_(sl, f"Items?$filter=({flt}) and Valid eq 'tYES' and InventoryItem eq 'tYES'"
                              "&$select=ItemCode,CostAccountingMethod,ManageBatchNumbers"), key=lambda i: i["ItemCode"])
    rnd = random.Random(20261005)
    todo = []
    for it in items:
        c = it["ItemCode"]
        p, made_up = (cost[c], False) if cost.get(c, 0) > 0 else (rnd.randrange(50, 5001) * 10, True)
        todo.append((it, p, made_up))
    # stock / standard cost already in U1 WH5 (small OR-batches: whole warehouse collections at once drop the connection)
    cur = {}
    for k in range(0, len(todo), 20):
        f = " or ".join("ItemCode eq '{}'".format(t[0]["ItemCode"].replace("'", "''")) for t in todo[k:k + 20])
        for i in S.all_(sl, f"Items?$filter={f}&$select=ItemCode,ItemWarehouseInfoCollection"):
            cur[i["ItemCode"]] = next(((w["InStock"], w["StandardAveragePrice"]) for w in i["ItemWarehouseInfoCollection"]
                                       if w["WarehouseCode"] == WH), None)
    missing = [t[0]["ItemCode"] for t in todo if cur.get(t[0]["ItemCode"]) is None]
    if missing:
        sys.exit(f"{len(missing)} items have no {WH} row: {missing[:10]}")
    done = [t for t in todo if cur[t[0]["ItemCode"]][0] > 0]
    todo = [t for t in todo if cur[t[0]["ItemCode"]][0] == 0]
    print(f"{len(items)} active FG inventory items, {len(done)} already stocked in {WH}, {len(todo)} to receive "
          f"({sum(m for _, _, m in todo)} with a random cost)")
    for it, p, m in todo:
        if m:
            print(f"     random cost {it['ItemCode']:22s} {p:>9,.2f}")
    sl.dry = a.dry
    std = [(t[0]["ItemCode"], t[1]) for t in todo if t[0]["CostAccountingMethod"] == "bis_Standard"
           and abs(cur[t[0]["ItemCode"]][1] - t[1]) > 0.005]
    for k in range(0, len(std), CHUNK):
        part = std[k:k + CHUNK]
        sl.post("MaterialRevaluation", {"DocDate": DATE, "RevalType": "P", "Comments": f"FG standard cost {WH}",
                                        "MaterialRevaluationLines": [{"ItemCode": c, "Price": p, "WarehouseCode": WH}
                                                                     for c, p in part]},
                f"standard cost {k + 1}-{k + len(part)}")
    if sl.failures:
        sys.exit("revaluation failed - fix before receiving stock")
    for k in range(0, len(todo), CHUNK):
        part = todo[k:k + CHUNK]
        lines = []
        for it, p, _ in part:
            ln = {"ItemCode": it["ItemCode"], "WarehouseCode": WH, "Quantity": QTY, "UnitPrice": p, "AccountCode": OFFSET}
            if it["ManageBatchNumbers"] == "tYES":
                ln["BatchNumbers"] = [{"BatchNumber": BATCH, "Quantity": QTY}]
            lines.append(ln)
        sl.post("InventoryGenEntries", {"DocDate": DATE, "Reference2": REF, "Comments": f"Finished goods stock {QTY} each - {NAME}",
                                        "DocumentLines": lines},
                f"FG stock {k + 1}-{k + len(part)} ({sum(p * QTY for _, p, _ in part):,.2f})")
    print(f"Done. Failures: {sl.failures}")


if __name__ == "__main__":
    main()
