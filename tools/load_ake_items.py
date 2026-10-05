"""Create AKE's real item master (data/ake_items/items.json, from tools/parse_item_list.py) in AKE_DEMO.

- Item groups by AKE's group name; missing groups are created with the G/L accounts of a template group
  (Finished Goods* -> Finished Goods, Packaging Materials -> Packing Material, everything else -> Consumables).
- UoM group + inventory / purchasing / sales UoM by AKE's UoM names (NOS, KGS, Tonnes, Meters, ...); 'OTH' = Manual.
  A UoM that is not in the item's UoM group falls back to the inventory UoM.
- Valuation (Moving Average / Standard), Buy/Make, MRP, batch management, purchase/sales/inventory flags from AKE.
- Inactive items are created inactive; Fixed Asset items are skipped (user choice 2026-10-05).
Idempotent: existing ItemCodes are skipped.  Run:  python tools/load_ake_items.py [--dry] [--only CODE ...] [--threads 4]
"""
import argparse, json, pathlib, sys, threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ake_items" / "items.json"
UOM_GROUP = {"Each": 7, "Weight": 1, "Volume": 9, "Length": 4, "Area": 10, "Manual": -1}
UOM = {"NOS": 1, "KGS": 2, "Tonnes": 3, "Meters": 5, "LTR": 7, "Set": 9, "Pairs": 10, "Packet": 11,
       "Square Meters": 12, "Square Feet": 13, "Centimeters": 14, "m3": 16, "Cubic Meters": 16, "Grams": 17}
ACCOUNT_FIELDS = ["PriceDifferencesAccount", "ExchangeRateDifferencesAccount", "IncreasingAccount",
                  "WIPMaterialVarianceAccount", "PurchaseAccount", "ReturningAccount", "ExpensesAccount", "RevenuesAccount",
                  "TransfersAccount", "InventoryAccount", "DecreaseGLAccount", "GoodsClearingAccount", "IncreaseGLAccount",
                  "WIPMaterialAccount", "DecreasingAccount", "VarianceAccount", "CostAccount", "PAReturnAccount",
                  "PurchaseCreditAcc", "SalesCreditAcc", "NegativeInventoryAdjustmentAccount"]
yn = lambda b: "tYES" if b else "tNO"


def template_for(name):
    if name.startswith("Finished Goods"):
        return "Finished Goods"
    return "Packing Material" if name == "Packaging Materials" else "Consumables"


def all_(sl, url):
    out = []
    while url:
        j = sl.get(url)
        out += j["value"]
        url = j.get("@odata.nextLink")
    return out


def ensure_groups(sl, names, dry):
    have = {g["GroupName"]: g for g in all_(sl, "ItemGroups")}
    for n in sorted(names - set(have)):
        t = have[template_for(n)]
        body = {"GroupName": n, "InventorySystem": t["InventorySystem"], **{k: t[k] for k in ACCOUNT_FIELDS if t.get(k)}}
        if dry:
            print(f"DRY group {n} (accounts of {t['GroupName']})")
        else:
            sl.post("ItemGroups", body, f"item group {n} (accounts of {t['GroupName']})")
    return {g["GroupName"]: g["Number"] for g in all_(sl, "ItemGroups?$select=Number,GroupName")}


def uom_setup(it, members):
    grp, inv = it["UoMGroup"], it["InventoryUoM"]
    if grp == "Manual" or inv not in UOM:
        u = inv or "OTH"
        return {"UoMGroupEntry": -1, "InventoryUOM": u, "PurchaseUnit": it["PurchaseUoM"] or u, "SalesUnit": it["SalesUoM"] or u}
    g = UOM_GROUP[grp]
    if UOM[inv] not in members[g]:  # e.g. Square Meters filed under Length -> the group that holds the UoM
        g = next(k for k, m in members.items() if UOM[inv] in m)
    pick = lambda name: UOM[name] if UOM.get(name) in members[g] else UOM[inv]
    return {"UoMGroupEntry": g, "InventoryUoMEntry": UOM[inv], "DefaultPurchasingUoMEntry": pick(it["PurchaseUoM"]),
            "DefaultSalesUoMEntry": pick(it["SalesUoM"]), "PricingUnit": UOM[inv]}


def body_for(it, groups, members):
    body = {"ItemCode": it["ItemCode"], "ItemName": it["ItemName"][:200], "ItemsGroupCode": groups[it["ItemGroup"]],
            "PurchaseItem": yn(it["Purchase"]), "SalesItem": yn(it["Sales"]), "InventoryItem": yn(it["Inventory"]),
            "CostAccountingMethod": "bis_Standard" if it["Valuation"] == "S" else "bis_MovingAverage",
            "GLMethod": "glm_ItemClass", "ManageBatchNumbers": yn(it["ManageBatch"] and it["Inventory"]),
            "ProcurementMethod": "bom_Make" if it["Procurement"] == "M" else "bom_Buy",
            "PlanningSystem": "bop_MRP" if it["Planning"] == "M" else "bop_None",
            "GSTRelevnt": "tYES", "GSTTaxCategory": "gtc_Regular",
            **uom_setup(it, members)}
    if not it["Active"]:
        body.update(Valid="tNO", Frozen="tYES")
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    L.LOGS.mkdir(exist_ok=True)
    logf = L.LOGS / f"ake_items_{L.dt.datetime.now():%Y%m%d_%H%M%S}.log"
    lock = threading.Lock()

    def log(msg):
        with lock:
            if not msg.startswith("OK"):
                print(msg, flush=True)
            with open(logf, "a", encoding="utf-8") as fh:
                fh.write(msg + "\n")

    env = L.read_env()
    sl = L.SL(env, False, log)
    sl.login()
    items = [i for i in json.loads(SRC.read_text(encoding="utf-8"))
             if i["ItemType"] != "F" and (not a.only or i["ItemCode"] in a.only)]
    groups = ensure_groups(sl, {i["ItemGroup"] for i in items}, a.dry)
    members = {g["AbsEntry"]: {l["AlternateUoM"] for l in g["UoMGroupDefinitionCollection"]}
               for g in all_(sl, "UnitOfMeasurementGroups") if g["AbsEntry"] != -1}
    have = {x["ItemCode"].upper() for x in all_(sl, "Items?$select=ItemCode")}
    todo = [i for i in items if i["ItemCode"].upper() not in have]
    log(f"{len(items)} items (no fixed assets), {len(items) - len(todo)} already exist, {len(todo)} to create")
    if a.dry:
        for i in todo[:20]:
            print(json.dumps(body_for(i, groups, members) if i["ItemGroup"] in groups else i, ensure_ascii=False))
        return

    # one Service Layer session per worker, logged in one after another (parallel logins invalidate each other)
    sessions = [sl]
    for _ in range(a.threads - 1):
        s2 = L.SL(env, False, log)
        s2.login()
        sessions.append(s2)
    chunks = [todo[k::len(sessions)] for k in range(len(sessions))]

    def work(k):
        return sum(sessions[k].post("Items", body_for(it, groups, members), f"{it['ItemCode']} {it['ItemName'][:40]}")
                   is not None for it in chunks[k])

    with ThreadPoolExecutor(len(sessions)) as ex:
        ok = sum(ex.map(work, range(len(sessions))))
    log(f"created {ok}, failed {len(todo) - ok}; log {logf}")


if __name__ == "__main__":
    main()
