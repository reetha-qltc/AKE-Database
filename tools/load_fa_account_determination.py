"""Create AKE's fixed-asset account determinations (user upload `GL Account Determination.csv`) in AKE_DEMO.

The B1 export is UTF-16 and unquoted (descriptions may contain commas, e.g. 'Computers,Desktop, Laptop & Printers'),
so each row is parsed by its 9 G/L account codes; the text before the first code is the description.
Existing codes are updated (PATCH) so the accounts match the file; nothing else is changed.
Run:  python tools/load_fa_account_determination.py [--dry]
"""
import argparse, re, sys

import sl_loader as L

SRC = L.ROOT / "GL Account Determination.csv"
ACC = re.compile(r",(\d{4}(?:-\d{2})+),")
CODE = re.compile(r"\d{4}(?:-\d{2})+")
# CSV column order -> Service Layer field (FAAccountDeterminations)
FIELDS = ["AssetBalanceSheetAccount", "ClearingAccountAcquisition", "OrdinaryDepreciation", "AccumulatedOrdinaryDepr",
          "UnplannedDepreciation", "AccumulatedUnplannedDepr", "RevaluationReserveAccount", "RevenueClearingAccount",
          "RevaluationReserveClearing"]


def parse():
    out = []
    for ln in SRC.read_bytes().decode("utf-16").splitlines()[1:]:
        if not ln.strip():
            continue
        _, code, rest = ln.split(",", 2)
        first = ACC.search("," + rest)
        desc = rest[:first.start() - 1]
        # after the description: account code, account name, account code, ... (names never look like codes)
        codes = [t for t in rest[first.start():].split(",") if CODE.fullmatch(t)]
        if len(codes) != len(FIELDS):
            sys.exit(f"{code}: found {len(codes)} accounts, expected {len(FIELDS)}")
        out.append({"Code": code, "Description": desc[:100], **dict(zip(FIELDS, codes))})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    rows = parse()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    for r in rows:
        missing = [r[f] for f in FIELDS if not sl.exists("ChartOfAccounts", r[f])]
        if missing:
            sys.exit(f"{r['Code']}: accounts not in the chart of accounts: {missing}")
    sl.dry = a.dry
    for r in rows:
        label = f"{r['Code']} {r['Description']}"
        if not a.dry and sl.exists("FAAccountDeterminations", r["Code"]):
            sl.patch("FAAccountDeterminations", r["Code"], r, label)
        else:
            sl.post("FAAccountDeterminations", r, label)
    print(f"Done. {len(rows)} determinations, failures: {sl.failures}")


if __name__ == "__main__":
    main()
