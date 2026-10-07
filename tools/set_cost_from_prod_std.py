"""Item cost (Inventory Data tab) = Production Std Cost (Production Data tab) for inventory items without an item cost.

Items whose item cost is 0 in every warehouse: Production Std Cost > 0 becomes the item cost.  With --random, items
without a usable Production Std Cost (0, or negative from scrap / by-product lines) get a random demo cost
(100-1,000 in steps of 50, user choice) in BOTH fields; the list goes to data/ake_items/random_costs.csv.
With --fixed PRICE, every item without an item cost gets PRICE in BOTH fields (user choice 2026-10-07: 150).
Item cost by inventory revaluation (price change) against 1003 Opening Balance Offset: standard items in all
warehouses, moving-average items where there is stock, else in all warehouses.  FIFO items are skipped.
Up to 40 items per document; a failing document is retried item by item.  B1 refuses to revalue inactive items, so
they are activated for their document and set inactive again right after.  A dropped connection -> log in, retry.
Run:  python tools/set_cost_from_prod_std.py [--random | --fixed 150] [--dry] [--only ITEM ...] [--date 2026-10-07]
"""
import argparse, csv, datetime as dt, random, time

import requests
import sys

import sl_loader as L

OFFSET = "1003"
RANDOM_CSV = L.ROOT / "data" / "ake_items" / "random_costs.csv"


INACTIVE_WH = set()  # B1 refuses revaluation lines on an inactive warehouse (e.g. CONS)


def lines_for(it, price):
    whs = [w for w in it["ItemWarehouseInfoCollection"] if w["WarehouseCode"] not in INACTIVE_WH]
    if it["CostAccountingMethod"] == "bis_MovingAverage" and any((w["InStock"] or 0) > 0 for w in whs):
        whs = [w for w in whs if (w["InStock"] or 0) > 0]
    return [{"ItemCode": it["ItemCode"], "Price": price, "WarehouseCode": w["WarehouseCode"],
             "RevaluationIncrementAccount": OFFSET, "RevaluationDecrementAccount": OFFSET} for w in whs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--random", action="store_true", help="random cost for items without Production Std Cost > 0")
    ap.add_argument("--fixed", type=float, help="this cost in both fields for every item without an item cost")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    INACTIVE_WH.update(w["WarehouseCode"] for w in sl.get("Warehouses?$select=WarehouseCode,Inactive")["value"]
                       if w["Inactive"] == "tYES")
    codes, url = [], "Items?$select=ItemCode&$filter=InventoryItem eq 'tYES'&$orderby=ItemCode"
    while url:
        r = sl.get(url)
        codes += [i["ItemCode"] for i in r["value"]]
        url = r.get("@odata.nextLink")
    if a.only:
        codes = [c for c in codes if c in a.only]
    rnd = random.Random(20261007)
    todo, fifo, rand_rows = [], [], []  # todo: (item, price)
    for k in range(0, len(codes), 20):  # small OR-filters: the warehouse rows of all items at once drop the connection
        flt = " or ".join("ItemCode eq '{}'".format(c.replace("'", "''")) for c in codes[k:k + 20])
        sel = "ItemCode,ItemName,Valid,ProdStdCost,CostAccountingMethod,ItemWarehouseInfoCollection"
        for it in sl.get(f"Items?$select={sel}&$filter={flt}")["value"]:
            if any(w["StandardAveragePrice"] for w in it["ItemWarehouseInfoCollection"]):
                continue  # has an item cost already
            ps = it["ProdStdCost"] or 0
            if ps <= 0 and not (a.random or a.fixed):
                continue
            if it["CostAccountingMethod"] == "bis_FIFO":
                fifo.append(it["ItemCode"])  # FIFO cost comes from layers
                continue
            if a.fixed:
                todo.append((it, a.fixed))
            elif ps > 0:
                todo.append((it, ps))
            else:
                price = rnd.randrange(100, 1001, 50)
                todo.append((it, price))
                rand_rows.append((it["ItemCode"], it["ItemName"], ps, price))
    print(f"{len(codes)} inventory items: {len(todo)} without item cost to set "
          f"({len(rand_rows)} random); FIFO skipped: {fifo}")
    sl.dry = a.dry
    if rand_rows and not a.dry:
        RANDOM_CSV.parent.mkdir(parents=True, exist_ok=True)
        new = not RANDOM_CSV.exists()
        with RANDOM_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["ItemCode", "ItemName", "OldProdStdCost", "DemoCost"])
            w.writerows(rand_rows)

    def call(fn, *args):
        for attempt in range(3):
            try:
                return fn(*args)
            except requests.exceptions.ConnectionError:
                print("Connection dropped - logging in again")
                time.sleep(10)
                sl.login()
        sys.exit("Service Layer unreachable")

    def post(group, label):
        body = {"DocDate": a.date, "RevalType": "P", "Comments": "Item cost = Production Std Cost",
                "MaterialRevaluationLines": [ln for it, p in group for ln in lines_for(it, p)]}
        return call(sl.post, "MaterialRevaluation", body, label)

    def set_active(group, on):
        for it, _ in group:
            call(sl.patch, "Items", it["ItemCode"], {"Valid": "tYES", "Frozen": "tNO"} if on else
                 {"Valid": "tNO", "Frozen": "tYES"}, f"{it['ItemCode']} {'activated' if on else 'inactive again'}")

    failed = []
    active = [t for t in todo if t[0]["Valid"] == "tYES"]
    inactive = [t for t in todo if t[0]["Valid"] != "tYES"]
    for kind, items in (("active", active), ("inactive", inactive)):
        for k in range(0, len(items), 40):
            group = items[k:k + 40]
            for it, p in group:
                if abs((it["ProdStdCost"] or 0) - p) > 0.005:
                    call(sl.patch, "Items", it["ItemCode"], {"ProdStdCost": p},
                         f"{it['ItemCode']} Production Std Cost = {p}")
            if kind == "inactive":
                set_active(group, True)
            try:
                if post(group, f"{kind} items {k + 1}-{k + len(group)}") is None:
                    sl.failures -= 1
                    for it, p in group:
                        if post([(it, p)], f"{it['ItemCode']} = {p}") is None:
                            failed.append(it["ItemCode"])
            finally:
                if kind == "inactive":
                    set_active(group, False)
    print(f"Done, {len(todo) - len(failed)} items set, {len(failed)} failed: {failed}")


if __name__ == "__main__":
    main()
