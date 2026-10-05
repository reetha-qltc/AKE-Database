"""Create AKE's production BOMs (data/ake_boms/boms.json, from tools/parse_bom_list.py) in AKE_DEMO.

User choices 2026-10-05: Unit-2 is mapped onto Unit-1 (U2 WHn -> U1 WHn, RESxxx-U2 -> RESxxx-U1); resources missing
in AKE_DEMO are created with the code as name, cost per minute = most common price on their BOM lines, UoM Mins,
warehouse U1 WH4 (operators = labour, SCRES*/RESSUB* subcontract = other, rest = machine).
Retired warehouse 01 -> U1WH01, SubcU221 -> U1 WH3. A BOM whose parent or a component item is missing is skipped
and listed. Idempotent: existing BOMs are skipped.
Run:  python tools/load_ake_boms.py [--dry] [--only TREE ...] [--threads 3]
"""
import argparse, collections, json, pathlib, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L
from load_ake_items import all_

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ake_boms" / "boms.json"
WHS = {"01": "U1WH01", "SubcU221": "U1 WH3"}


def whs(w):
    return WHS.get(w) or re.sub(r"^U2 ", "U1 ", w) or "U1 WH4"


def res(code):
    return re.sub(r"-U2$", "-U1", code)


def res_type(code):
    if code.startswith(("SCRES", "RESSUB")):
        return "rtOther"
    base = code.split("-")[0]
    return "rtLabor" if code.startswith("REOP") or base.endswith("O") else "rtMachine"


def ensure_resources(sl, boms, dry):
    have = {r["VisCode"]: r for r in all_(sl, "Resources?$select=VisCode,ResourceWarehouses")}
    prices, used = collections.defaultdict(collections.Counter), collections.defaultdict(set)
    for b in boms:
        for l in b["Lines"]:
            if l["Type"] == 290:
                prices[res(l["Code"])][l["Price"]] += 1
                used[res(l["Code"])].add(whs(l["Warehouse"]))
    for code in sorted(prices):
        whs_ = sorted(used[code] | {"U1 WH4"})  # a resource line's warehouse must be one of the resource's warehouses
        if code in have:
            new = [w for w in whs_ if w not in {x["Warehouse"] for x in have[code]["ResourceWarehouses"]}]
            if new and not dry:
                sl.patch("Resources", code, {"ResourceWarehouses": [{"Warehouse": w} for w in new]},
                         f"resource {code} + warehouses {', '.join(new)}")
            continue
        nz = [p for p, _ in prices[code].most_common() if p] or [0]
        body = {"VisCode": code, "Name": code, "Type": res_type(code), "IssueMethod": "rimBackflush", "Cost1": nz[0],
                "UnitOfMeasure": "Mins", "DefaultWarehouse": "U1 WH4",
                "ResourceWarehouses": [{"Warehouse": w} for w in whs_]}
        if dry:
            print("DRY resource", body)
        else:
            sl.post("Resources", body, f"resource {code} {body['Type']} {nz[0]}/min")


def body_for(b):
    lines = []
    for l in sorted(b["Lines"], key=lambda l: l["LineNo"]):
        r = l["Type"] == 290
        lines.append({"ItemCode": res(l["Code"]) if r else l["Code"], "Quantity": l["Qty"],
                      "ItemType": "pit_Resource" if r else "pit_Item",
                      "IssueMethod": "im_Backflush" if l["IssueMethod"] == "B" or r else "im_Manual",
                      "Warehouse": whs(l["Warehouse"])})
    return {"TreeCode": b["TreeCode"], "TreeType": "iProductionTree", "Quantity": b["Qty"],
            "Warehouse": whs(b["Warehouse"]), "ProductTreeLines": lines}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--threads", type=int, default=3)
    a = ap.parse_args()
    L.LOGS.mkdir(exist_ok=True)
    logf = L.LOGS / f"ake_boms_{L.dt.datetime.now():%Y%m%d_%H%M%S}.log"

    def log(msg):
        if not msg.startswith("OK"):
            print(msg, flush=True)
        with open(logf, "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")

    env = L.read_env()
    sl = L.SL(env, False, log)
    sl.login()
    boms = [b for b in json.loads(SRC.read_text(encoding="utf-8")) if not a.only or b["TreeCode"] in a.only]
    ensure_resources(sl, boms, a.dry)
    items = {x["ItemCode"] for x in all_(sl, "Items?$select=ItemCode")}
    have = {x["TreeCode"] for x in all_(sl, "ProductTrees?$select=TreeCode")}
    todo, missing = [], []
    for b in boms:
        if b["TreeCode"] in have:
            continue
        gone = [c for c in [b["TreeCode"]] + [l["Code"] for l in b["Lines"] if l["Type"] == 4] if c not in items]
        (missing.append((b["TreeCode"], gone)) if gone else todo.append(b))
    for t, gone in missing:
        log(f"SKIP {t}: items not in AKE_DEMO: {', '.join(sorted(set(gone)))}")
    log(f"{len(boms)} BOMs: {len(boms) - len(todo) - len(missing)} exist, {len(missing)} skipped (missing items), "
        f"{len(todo)} to create")
    if a.dry:
        for b in todo[:3]:
            print(json.dumps(body_for(b), ensure_ascii=False))
        return
    sessions = [sl]
    for _ in range(a.threads - 1):  # log in one after another - parallel logins invalidate each other
        s2 = L.SL(env, False, log)
        s2.login()
        sessions.append(s2)
    chunks = [todo[k::len(sessions)] for k in range(len(sessions))]

    def work(k):
        return sum(sessions[k].post("ProductTrees", body_for(b), f"{b['TreeCode']} ({len(b['Lines'])} lines)")
                   is not None for b in chunks[k])

    with ThreadPoolExecutor(len(sessions)) as ex:
        ok = sum(ex.map(work, range(len(sessions))))
    log(f"created {ok}, failed {len(todo) - ok}; log {logf}")


if __name__ == "__main__":
    main()
