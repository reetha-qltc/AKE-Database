"""Create AKE's asset classes (user upload `Assest Classes.csv`, B1 export, UTF-16) in AKE_DEMO.

The export is unquoted (a name may contain commas), so each row is read from the right: the last 14 fields are fixed,
everything between the code and them is the name.  One row = one depreciation-area line of a class; rows with the same
code are grouped.  AKE's Branch ID (1 = Unit 1, 3 = Unit 2) is not set: AKE_DEMO has no branches.  Existing codes are
updated (PATCH) to match the file.
Run:  python tools/load_asset_classes.py [--dry]
"""
import argparse, sys

import sl_loader as L

SRC = L.ROOT / "Assest Classes.csv"
TYPE = {"General": "atAssetTypeGeneral", "Low Value Asset": "atAssetTypeLowValueAsset"}


def parse():
    classes = {}
    for ln in SRC.read_bytes().decode("utf-16").splitlines()[1:]:
        if not ln.strip():
            continue
        p = ln.split(",")
        t = p[-14:]  # Asset Type ... Updated Date, '' (trailing comma)
        if t[-1] != "" or len(p) < 17:
            sys.exit(f"unexpected row: {ln!r}")
        code = p[1]
        c = classes.setdefault(code, {
            "Code": code, "Description": ",".join(p[2:-14])[:100],
            "AssetType": TYPE[t[0]],
            "ValueLimitFrom": float(t[1]), "ValueLimitTo": float(t[2]),
            "AssetClassCollection": [],
        })
        c["AssetClassCollection"].append({
            "DepreciationAreaID": t[6],
            "ActiveStatus": "tYES" if t[7] == "Yes" else "tNO",
            "AccountDetermination": t[8],
            "DepreciationTypeID": t[9],
            "UseLife": int(t[10]),
        })
    return list(classes.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    rows = parse()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    have = {d["Code"] for d in sl.get("AssetClasses?$select=Code")["value"]}
    sl.dry = a.dry
    for r in rows:
        ln = r["AssetClassCollection"][0]
        label = f"{r['Code']:16s} {r['Description'][:45]:45s} {ln['AccountDetermination']} / {ln['DepreciationTypeID']} / {ln['UseLife']} m"
        if r["Code"] in have:
            sl.patch("AssetClasses", r["Code"], r, label)
        else:
            sl.post("AssetClasses", r, label)
    print(f"Done. {len(rows)} asset classes, failures: {sl.failures}")


if __name__ == "__main__":
    main()
