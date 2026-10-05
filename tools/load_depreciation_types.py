"""Create AKE's depreciation types (user upload `Depreciation types.csv`, B1 export) in AKE_DEMO.

The export is unquoted (a description may contain commas), so each row is read from the right: the last 31 fields are
fixed, everything between the code and them is the description.  Fields the export does not carry (period control,
pro-rata type, rounding) keep the defaults of the existing WDV30 declining-balance type.  Valid From/To '01/01/00' -
'31/12/99' are B1's open range 1900-01-01 - 2099-12-31.  Existing codes are updated (PATCH) to match the file.
Run:  python tools/load_depreciation_types.py [--dry]
"""
import argparse, sys

import sl_loader as L

SRC = L.ROOT / "Depreciation types.csv"
METHOD = {"DB": "dmDecliningBalance", "SL": "dmStraightLine", "SLP": "dmStraightLinePeriodControl", "MD": "dmManualDepreciation"}
SPECIAL = {"D": "spcmAdditional"}
yn = lambda v: "tYES" if v == "Y" else "tNO"
num = lambda v: float(v) if v else 0.0


def parse():
    out = []
    for ln in SRC.read_bytes().decode("utf-16").splitlines()[1:]:
        if not ln.strip():
            continue
        p = ln.split(",")
        t = p[-31:]  # Method Code ... Multilevel Amount, '' (trailing comma)
        if t[-1] != "" or len(p) < 34:
            sys.exit(f"unexpected row: {ln!r}")
        out.append({
            "Code": p[1], "Description": ",".join(p[2:-31])[:100],
            "DepreciationMethod": METHOD[t[0]],
            "MinimumDepreciatedValue": num(t[2]),
            "RoundYearEndBookValue": yn(t[3]),
            "IncludeSalvageInDepreciation": yn(t[5]),
            "SalvagePercentage": num(t[7]),
            "PercentageOfDepreciationReversedInRetirementYear": num(t[8]),
            "ValidFrom": "1900-01-01", "ValidTo": "2099-12-31",
            "StraightLineCalculationMethod": "slcmAuquisitionValueDividedByTotalUsefulLife",  # APC
            "StraightLinePercentage": num(t[13]),
            "DecliningPercentage": num(t[16]),
            "DecliningFactor": num(t[17]),
            "DecliningChangeTo": t[18] or None,
            "ManualDepreciationReduceDepreciationBase": yn(t[19]),
            "SpecialDepreciationCalculationMethod": SPECIAL[t[21]],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    rows = parse()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    have = {d["Code"] for d in sl.get("DepreciationTypes?$select=Code")["value"]}
    sl.dry = a.dry
    for r in rows:
        label = f"{r['Code']:16s} {r['Description']} ({r['DecliningPercentage']}%, salvage {r['SalvagePercentage']}%)"
        if r["Code"] in have:
            sl.patch("DepreciationTypes", r["Code"].replace("%", "%25"), r, label)  # codes contain %
        else:
            sl.post("DepreciationTypes", r, label)
    print(f"Done. {len(rows)} depreciation types, failures: {sl.failures}")


if __name__ == "__main__":
    main()
