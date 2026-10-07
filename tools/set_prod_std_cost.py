"""Production Std Cost (item master, Production Data tab) = item cost (Inventory Data tab) for all inventory items.

The item cost is kept per warehouse: one cost -> that cost; several costs -> the cost of the warehouse with the largest
stock value (no stock: the most common cost).  Items without an item cost are left as they are (not set to 0).
Run:  python tools/set_prod_std_cost.py [--dry] [--only ITEM ...]
"""
import argparse, collections

import sl_loader as L


def item_cost(whs):
    priced = [w for w in whs if w["StandardAveragePrice"]]
    if not priced:
        return None
    stocked = [w for w in priced if (w["InStock"] or 0) > 0]
    if stocked:
        return max(stocked, key=lambda w: w["InStock"] * w["StandardAveragePrice"])["StandardAveragePrice"]
    return collections.Counter(w["StandardAveragePrice"] for w in priced).most_common(1)[0][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    codes, url = [], "Items?$select=ItemCode&$filter=InventoryItem eq 'tYES'&$orderby=ItemCode"
    while url:
        r = sl.get(url)
        codes += [i["ItemCode"] for i in r["value"]]
        url = r.get("@odata.nextLink")
    if a.only:
        codes = [c for c in codes if c in a.only]
    todo, skipped = [], 0
    for k in range(0, len(codes), 20):  # small OR-filters: the warehouse rows of all items at once drop the connection
        flt = " or ".join("ItemCode eq '{}'".format(c.replace("'", "''")) for c in codes[k:k + 20])
        for it in sl.get(f"Items?$select=ItemCode,ProdStdCost,ItemWarehouseInfoCollection&$filter={flt}")["value"]:
            cost = item_cost(it["ItemWarehouseInfoCollection"])
            if cost is None:
                skipped += 1
            elif abs((it["ProdStdCost"] or 0) - cost) > 0.005:
                todo.append((it["ItemCode"], it["ProdStdCost"] or 0, cost))
    print(f"{len(codes)} inventory items: {len(todo)} to change, {skipped} without item cost (left as is)")
    sl.dry = a.dry
    for code, old, cost in todo:
        sl.patch("Items", code, {"ProdStdCost": cost}, f"{code} Production Std Cost {old} -> {cost}")
    print(f"Done, {sl.failures} failures")


if __name__ == "__main__":
    main()
