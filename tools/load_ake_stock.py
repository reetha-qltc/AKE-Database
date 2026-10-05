"""Load AKE's item stock + average cost (user upload `item master with average Price and Stock.csv`) into AKE_DEMO.

The export (B1, UTF-16, unquoted: '#,Item No.,Item Cost,In Stock,') has no warehouse. User choices 2026-10-05:
- all stock goes to U1 WH1 (Unit-1 Raw Material Warehouse), posted 2026-04-01 against 1003 Opening Balance Offset
- only rows with stock are loaded (cost-only rows ignored); inactive items are skipped
Moving-average items: Goods Receipt at AKE's cost sets the average price.  Standard items: B1 values the receipt at the
standard cost, so an inventory revaluation (price change) to AKE's cost in U1 WH1 is posted first.
Batch items get batch OB-260401.  Idempotent: items that already have stock are skipped.
Run:  python tools/load_ake_stock.py [--dry] [--only CODE ...] [--chunk 100]
"""
import argparse, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

SRC = L.ROOT / "item master with average Price and Stock.csv"
WH, DATE, OFFSET, BATCH, REF = "U1 WH1", "2026-04-01", "1003", "OB-260401", "AKE-OB-STK"
USD_RATE = 88.0  # demo INR per USD, as in demo_transactions.py
NUM = r"(-?\d{1,3}(?:,\d{3})*\.\d+)"  # amounts carry thousands separators, e.g. 19,345.00
ROW = re.compile(r"^(\d+),(.*?)," + NUM + "," + NUM + r",\s*$")


def parse():
    rows = {}
    for ln in SRC.read_bytes().decode("utf-16").splitlines()[1:]:
        m = ROW.match(ln)
        if not m:
            sys.exit(f"cannot parse: {ln!r}")
        rows[m[2]] = (float(m[3].replace(",", "")), float(m[4].replace(",", "")))
    return rows


def all_(sl, url):
    out = []
    while url:
        j = sl.get(url)
        out += j["value"]
        url = j.get("@odata.nextLink")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--chunk", type=int, default=100)
    a = ap.parse_args()
    L.LOGS.mkdir(exist_ok=True)
    logf = L.LOGS / f"ake_stock_{L.dt.datetime.now():%Y%m%d_%H%M%S}.log"

    def log(msg):
        print(msg, flush=True)
        with open(logf, "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")

    rows = parse()
    stock = {c: pq for c, pq in rows.items() if pq[1] > 0 and (not a.only or c in a.only)}
    log(f"{len(rows)} rows, {len(stock)} with stock, value {sum(p * q for p, q in stock.values()):,.2f}")
    sl = L.SL(L.read_env(), a.dry, log)
    sl.dry = False
    sl.login()
    items = {i["ItemCode"]: i for i in all_(sl, "Items?$select=ItemCode,Valid,InventoryItem,CostAccountingMethod,"
                                                "ManageBatchNumbers,QuantityOnStock")}
    todo, skip = [], {}
    for c, (p, q) in stock.items():
        it = items.get(c)
        why = ("not in AKE_DEMO" if not it else "inactive" if it["Valid"] != "tYES" else
               "not an inventory item" if it["InventoryItem"] != "tYES" else "already has stock" if it["QuantityOnStock"] else
               "quantity rounds to 0 (B1 quantity accuracy 2 decimals)" if round(q, 2) == 0 else "")
        if why:
            skip.setdefault(why, []).append(c)
        else:
            todo.append((c, p, q, it))
    for why, codes in skip.items():
        log(f"SKIP {len(codes)} {why}: {', '.join(codes[:15])}{' ...' if len(codes) > 15 else ''}")
    # B1 refuses a revaluation to the price the item already has in the warehouse (re-runs)
    std = [(c, p) for c, p, q, it in todo if it["CostAccountingMethod"] == "bis_Standard" and p > 0]
    cur = {}
    for k in range(0, len(std), 20):  # small OR-filters: the warehouse rows of all items at once drop the connection
        flt = " or ".join("ItemCode eq '{}'".format(c.replace("'", "''")) for c, _ in std[k:k + 20])
        for i in all_(sl, f"Items?$filter={flt}&$select=ItemCode,ItemWarehouseInfoCollection"):
            cur[i["ItemCode"]] = next((w["StandardAveragePrice"] for w in i["ItemWarehouseInfoCollection"]
                                       if w["WarehouseCode"] == WH), 0)
    std = [(c, p) for c, p in std if abs(cur.get(c, 0) - p) > 0.005]
    log(f"{len(todo)} items to receive into {WH} ({len(std)} standard items to revalue first)")
    sl.dry = a.dry

    for k in range(0, len(std), a.chunk):
        part = std[k:k + a.chunk]
        sl.post("MaterialRevaluation", {"DocDate": DATE, "RevalType": "P", "Comments": f"AKE standard cost {WH}",
                                        "MaterialRevaluationLines": [{"ItemCode": c, "Price": p, "WarehouseCode": WH}
                                                                     for c, p in part]},
                f"standard cost {k + 1}-{k + len(part)}")
    if sl.failures:
        sys.exit(f"{sl.failures} revaluation(s) failed - fix before receiving stock; log {logf}")
    if todo and not a.dry:  # AKE_DEMO's system currency is USD: B1 refuses documents on a date without a USD rate
        r = sl.s.post(f"{sl.base}/SBOBobService_SetCurrencyRate", timeout=60,
                      json={"Currency": "USD", "Rate": str(USD_RATE), "RateDate": DATE.replace("-", "")})
        if r.status_code not in (200, 204):
            sys.exit(f"FAIL USD rate {DATE}: {r.text[:300]}")

    for k in range(0, len(todo), a.chunk):
        part = todo[k:k + a.chunk]
        lines = []
        for c, p, q, it in part:
            ln = {"ItemCode": c, "WarehouseCode": WH, "Quantity": q, "UnitPrice": p, "AccountCode": OFFSET}
            if it["ManageBatchNumbers"] == "tYES":
                ln["BatchNumbers"] = [{"BatchNumber": BATCH, "Quantity": q}]
            lines.append(ln)
        sl.post("InventoryGenEntries", {"DocDate": DATE, "Reference2": REF, "Comments": "AKE opening stock (item master export)",
                                        "DocumentLines": lines},
                f"stock {k + 1}-{k + len(part)} ({sum(p * q for _, p, q, _ in part):,.2f})")
    log(f"Done. Failures: {sl.failures}; log {logf}")


if __name__ == "__main__":
    main()
