"""Set the item cost of individual items in every warehouse by an inventory revaluation (price change).

Standard items: the standard cost in all warehouses.  Moving-average items: the average cost wherever there is stock.
The revaluation difference goes to 1003 Opening Balance Offset.  Warehouses already at the price are skipped.
Run:  python tools/set_item_cost.py 00010=150 FG001=90150 [--date 2026-10-05]
"""
import argparse, datetime as dt

import sl_loader as L

OFFSET = "1003"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prices", nargs="+", help="ITEM=PRICE")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    lines = []
    for arg in a.prices:
        code, price = arg.rsplit("=", 1)
        price = float(price.replace(",", ""))
        it = sl.get("Items('{}')?$select=ItemCode,CostAccountingMethod,ItemWarehouseInfoCollection".format(code.replace("'", "''")))
        if not it:
            print(f"SKIP {code}: not found")
            continue
        std = it["CostAccountingMethod"] == "bis_Standard"
        for w in it["ItemWarehouseInfoCollection"]:
            if (std or w["InStock"] > 0) and abs(w["StandardAveragePrice"] - price) > 0.005:
                lines.append({"ItemCode": code, "Price": price, "WarehouseCode": w["WarehouseCode"],
                              "RevaluationIncrementAccount": OFFSET, "RevaluationDecrementAccount": OFFSET})
    if not lines:
        print("Nothing to change.")
        return
    sl.post("MaterialRevaluation", {"DocDate": a.date, "RevalType": "P", "Comments": "Item cost set by user request",
                                    "MaterialRevaluationLines": lines}, f"{len(lines)} item/warehouse prices: {' '.join(a.prices)}")


if __name__ == "__main__":
    main()
