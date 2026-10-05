"""One-off (2026-10-05): BOM parent items that AKE had set to Buy -> Make + MRP (planning by procurement method, as on
the demo items), so production orders and MRP work on AKE's BOMs.  Run:  python tools/fix_bom_parents.py [--dry]
"""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L
from load_ake_items import all_


def main():
    dry = "--dry" in sys.argv
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    trees = {x["TreeCode"] for x in all_(sl, "ProductTrees?$select=TreeCode")}
    buy = [x["ItemCode"] for x in all_(sl, "Items?$select=ItemCode&$filter=ProcurementMethod eq 'bom_Buy'")
           if x["ItemCode"] in trees]
    print(f"{len(buy)} BOM parents set to Buy")
    for code in buy:
        if dry:
            print("DRY", code)
        else:
            sl.patch("Items", code, {"ProcurementMethod": "bom_Make", "PlanningSystem": "bop_MRP"}, f"{code} -> Make, MRP")
    print(f"failures {sl.failures}")


if __name__ == "__main__":
    main()
