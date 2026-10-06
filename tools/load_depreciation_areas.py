"""Create / update AKE's depreciation areas (user upload `Deprecation Area.csv`, B1 export, UTF-16) in AKE_DEMO.

Columns used: Code, Description, Direct Depreciation (D = direct posting, I = indirect posting), Retirement Method
(G = gross), Main Booking Area, Direct Revenue Posting, Tax Credit Control.  Area Type is Posting to G/L for every
area (user choice 2026-10-06; the export has L for Main Books and O for Tax Books).  Existing codes are updated (PATCH).
Run:  python tools/load_depreciation_areas.py [--dry]
"""
import argparse, sys

import sl_loader as L

SRC = L.ROOT / "Deprecation Area.csv"
POSTING = {"D": "podDirectPosting", "I": "podIndirectPosting"}
RETIRE = {"G": "rmGross", "N": "rmNet"}
yn = lambda v: "tYES" if v == "Y" else "tNO"


def parse():
    lines = SRC.read_bytes().decode("utf-16").splitlines()
    head = lines[0].split(",")
    col = {h.strip(): i for i, h in enumerate(head)}
    out = []
    for ln in lines[1:]:
        if not ln.strip():
            continue
        p = ln.split(",")
        if len(p) != len(head):
            sys.exit(f"unexpected row: {ln!r}")
        g = lambda name: p[col[name]].strip()
        out.append({
            "Code": g("Code"), "Description": g("Description"),
            "PostingOfDepreciation": POSTING[g("Direct Depreciation")],
            "RetirementMethod": RETIRE[g("Retirement Method")],
            "AreaType": "atPostingtoGL",
            "MainBookingArea": yn(g("Main Booking Area")),
            "DirectRevenuePosting": yn(g("Direct Revenue Posting")),
            "TaxCreditControl": yn(g("Tax Credit Control")),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    rows = parse()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    have = {d["Code"] for d in sl.get("DepreciationAreas?$select=Code")["value"]}
    sl.dry = a.dry
    for r in rows:
        label = f"{r['Code']:12s} {r['PostingOfDepreciation']}, {r['AreaType']}, main {r['MainBookingArea']}"
        if r["Code"] in have:
            sl.patch("DepreciationAreas", r["Code"], r, label)
        else:
            sl.post("DepreciationAreas", r, label)
    print(f"Done. {len(rows)} depreciation areas, failures: {sl.failures}")


if __name__ == "__main__":
    main()
