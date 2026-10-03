"""One-off (2026-10-03): bring the existing items onto the UoM groups Each / Area / Length / Volume / Weight and the
valuation rule (bought items Moving Average, items made in production Standard).

- U1 items (build_u1_masters.ITEMS): UoM group / UoMs / pricing unit / valuation as defined there
  (sand & aggregate AGGREGATE -> Weight in Tonnes, harness & tool kit SET -> Each in Set, FIFO -> Moving Average).
- First demo set (Manual UoM group): moved onto the matching group by its manual unit text; steel bought in Tonnes.
  Manufactured FG-* items -> Standard with an indicative standard cost (78 % of the sales price).
- B1 refuses these changes once an item has transactions; such items are left as they are and listed.
- The groups AGGREGATE and SET are deleted once no item uses them (duplicates of Weight / Each).
Run:  python tools/update_item_uoms.py [--dry]
"""
import argparse, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L
import build_u1_masters as M

DOC_DATE = "2026-10-03"
TXN = ["Quotations", "Orders", "DeliveryNotes", "Invoices", "CreditNotes", "Returns", "PurchaseRequests",
       "PurchaseQuotations", "PurchaseOrders", "PurchaseDeliveryNotes", "PurchaseInvoices", "PurchaseCreditNotes",
       "PurchaseReturns", "InventoryGenEntries", "InventoryGenExits", "StockTransfers"]
MANUAL_UNIT = {"KG": ("WEIGHT", "KG"), "NOS": ("EACH", "NOS"), "PAIR": ("EACH", "PAIR"), "SET": ("EACH", "SET"),
               "LTR": ("VOLUME", "LTR")}
STEEL_PREFIX = ("RM-PL-", "RM-SG-", "RM-ST-", "RM-TMT-")  # bought per Tonne, stocked and priced per KG
STD_COST_SHARE = 0.78
OBSOLETE_GROUPS = ["AGGREGATE", "SET"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    v = lambda p: sl.get(p)["value"]
    uom = {u["Code"]: u["AbsEntry"] for u in v("UnitOfMeasurements?$select=AbsEntry,Code")}
    ugp = {g["Code"]: g["AbsEntry"] for g in v("UnitOfMeasurementGroups?$select=AbsEntry,Code")}
    used = set()
    for e in TXN:
        for d in (sl.get(f"{e}?$select=DocumentLines") or {"value": []})["value"]:
            used |= {l["ItemCode"] for l in d["DocumentLines"]}
    for p in (sl.get("ProductionOrders?$select=ItemNo,ProductionOrderLines") or {"value": []})["value"]:
        used |= {p["ItemNo"]} | {l["ItemNo"] for l in p["ProductionOrderLines"]}
    sal = L.price_list_no(sl, "SAL")
    u1 = {i["Code"]: i for i in M.ITEMS}
    skipped, revalue = [], []

    def change(item, body, label):
        if item["ItemCode"] in used or item["QuantityOnStock"]:
            skipped.append((item["ItemCode"], label))
        elif a.dry:
            print(f"DRY  {item['ItemCode']}: {label} {body}")
        else:
            sl.patch("Items", item["ItemCode"], body, f"{item['ItemCode']} {label}")
            return sl.failures == fails
        return False

    fields = ("ItemCode,ItemName,UoMGroupEntry,InventoryUOM,InventoryUoMEntry,DefaultPurchasingUoMEntry,"
              "DefaultSalesUoMEntry,PricingUnit,CostAccountingMethod,QuantityOnStock,InventoryItem,ItemPrices,"
              "ItemWarehouseInfoCollection")
    for it in v(f"Items?$select={fields}&$orderby=ItemCode"):
        code, fails = it["ItemCode"], sl.failures
        if code in u1:
            d = u1[code]
            want = {"UoMGroupEntry": ugp[d["UoMGroup"]], "InventoryUoMEntry": uom[d["InvUoM"]],
                    "DefaultPurchasingUoMEntry": uom[d["PurUoM"]], "DefaultSalesUoMEntry": uom[d["SalUoM"]],
                    "PricingUnit": uom[d["PriceUoM"]]}
            if d["Valuation"]:
                want["CostAccountingMethod"] = d["Valuation"]
            diff = {k: x for k, x in want.items() if it[k] != x}
            if "UoMGroupEntry" in diff:  # B1 clears the price list prices when the UoM group changes
                diff["ItemPrices"] = [{"PriceList": pl, "Price": p} for pl, p in
                                      ((L.price_list_no(sl, "PUR"), d["PurPrice"]), (sal, d["SalPrice"])) if p]
            if diff:
                change(it, diff, "-> " + ", ".join(sorted(diff)))
            continue
        if it["UoMGroupEntry"] != -1 or it["InventoryItem"] != "tYES":
            continue
        grp, unit = MANUAL_UNIT[it["InventoryUOM"]]
        body = {"UoMGroupEntry": ugp[grp], "InventoryUoMEntry": uom[unit], "DefaultSalesUoMEntry": uom[unit],
                "DefaultPurchasingUoMEntry": uom["MT" if code.startswith(STEEL_PREFIX) else unit],
                "PricingUnit": uom[unit]}
        price = next((p["Price"] for p in it["ItemPrices"] if p["PriceList"] == sal and p["Price"]), None)
        made = code.startswith("FG-") or code.startswith("SA-")
        if made:
            body["CostAccountingMethod"] = M.STD
        if change(it, body, f"-> {grp} / {unit}" + (" / Standard" if made else "")) and made and price:
            revalue.append((code, round(price * STD_COST_SHARE, -1),
                            [w["WarehouseCode"] for w in it["ItemWarehouseInfoCollection"]]))

    # B1 refuses AvgStdPrice on the item; the standard cost is set per warehouse by an inventory revaluation
    if revalue:
        sl.post("MaterialRevaluation", {"DocDate": DOC_DATE, "RevalType": "P", "Comments": "Indicative standard cost",
                                        "MaterialRevaluationLines": [{"ItemCode": c, "Price": p, "WarehouseCode": w}
                                                                     for c, p, ws in revalue for w in ws]},
                "Standard cost " + ", ".join(f"{c} {p:,.0f}" for c, p, _ in revalue))

    in_use = {i["UoMGroupEntry"] for i in v("Items?$select=UoMGroupEntry")}
    for code in OBSOLETE_GROUPS:
        if code in ugp and ugp[code] not in in_use and not a.dry:
            r = sl.s.delete(f"{sl.base}/UnitOfMeasurementGroups({ugp[code]})", timeout=60)
            print(f"{'OK  ' if r.status_code == 204 else 'FAIL'} DELETE UoM group {code}"
                  f"{'' if r.status_code == 204 else ': ' + r.text[:200]}")
        elif code in ugp:
            print(f"KEEP UoM group {code} (still used or dry run)")
    for code, label in skipped:
        print(f"SKIP {code} has transactions/stock - not changed: {label}")
    print(f"Done. Failures: {sl.failures}")


if __name__ == "__main__":
    main()
