"""One-off (2026-10-03): retire the old U1 warehouses that duplicate the AKE Unit-1 list U1 WH1-WH9.

Item default warehouses and BOM warehouses move to the new code, Standard items get their standard cost in the
new warehouses (B1 keeps it per warehouse), then the old warehouse is deleted - or set inactive when B1 refuses
because it has transactions. U1WH01 Main and U1WH04 Rejected have no counterpart in the new list and stay.
Run:  python tools/merge_warehouses.py
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

DUPLICATES = {"U1WH02": "U1 WH1", "U1WH03": "U1 WH9", "U1WH06": "U1 WH7", "U1WH07": "U1 WH5"}
NEW = [f"U1 WH{n}" for n in range(1, 10)]
DOC_DATE = "2026-10-03"


def main():
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    v = lambda p: sl.get(p)["value"]

    items = v("Items?$select=ItemCode,DefaultWarehouse,CostAccountingMethod,ItemWarehouseInfoCollection")
    for i in items:
        if i["DefaultWarehouse"] in DUPLICATES:
            sl.patch("Items", i["ItemCode"], {"DefaultWarehouse": DUPLICATES[i["DefaultWarehouse"]]},
                     f"{i['ItemCode']} default {i['DefaultWarehouse']} -> {DUPLICATES[i['DefaultWarehouse']]}")

    for t in v("ProductTrees"):
        lines = t["ProductTreeLines"]
        if t["Warehouse"] not in DUPLICATES and not any(l["Warehouse"] in DUPLICATES for l in lines):
            continue
        body = {"Warehouse": DUPLICATES.get(t["Warehouse"], t["Warehouse"]),
                "ProductTreeLines": [{"ItemCode": l["ItemCode"], "Quantity": l["Quantity"], "ItemType": l["ItemType"],
                                      "IssueMethod": l["IssueMethod"], "Warehouse": DUPLICATES.get(l["Warehouse"], l["Warehouse"])}
                                     for l in lines]}
        r = sl.s.patch(f"{sl.base}/ProductTrees('{t['TreeCode']}')", json=body,
                       headers={"B1S-ReplaceCollectionsOnPatch": "true"}, timeout=120)
        ok = r.status_code == 204
        sl.failures += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'} BOM {t['TreeCode']} warehouses{'' if ok else ': ' + r.text[:300]}")

    # standard cost per warehouse: copy the item's existing standard cost into the new warehouses
    lines = []
    for i in items:
        if i["CostAccountingMethod"] != "bis_Standard":
            continue
        whs = {w["WarehouseCode"]: w["StandardAveragePrice"] for w in i["ItemWarehouseInfoCollection"]}
        cost = max([c for c in whs.values() if c] or [0])
        lines += [{"ItemCode": i["ItemCode"], "Price": cost, "WarehouseCode": w}
                  for w in NEW if cost and whs.get(w) != cost]
    if lines:
        sl.post("MaterialRevaluation", {"DocDate": DOC_DATE, "RevalType": "P", "Comments": "Standard cost U1 WH1-WH9",
                                        "MaterialRevaluationLines": lines},
                f"Standard cost in new warehouses ({len(lines)} lines)")

    for old in DUPLICATES:
        r = sl.s.delete(f"{sl.base}/Warehouses('{old}')", timeout=60)
        if r.status_code == 204:
            print(f"OK   DELETE warehouse {old}")
            continue
        print(f"INFO {old} cannot be deleted ({r.json()['error']['message'][:120]}) - setting inactive")
        sl.patch("Warehouses", old, {"Inactive": "tYES"}, f"{old} inactive")
    print(f"Done. Failures: {sl.failures}")


if __name__ == "__main__":
    main()
