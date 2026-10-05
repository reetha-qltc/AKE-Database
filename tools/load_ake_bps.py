"""Create AKE's real customers and vendors (data/ake_customers/bps.json, from tools/parse_bp_list.py) in AKE_DEMO.

- CardCodes are AKE's own (C001..., V001...); they do not clash with the demo BPs C0001.../V0001...
- Inactive BPs in AKE's system are skipped.
- Group by GST place of supply like the demo BPs: Intrastate / Interstate / Export (vendors: ... Vendor / Import Vendor).
- Control + down-payment clearing accounts as on the demo BPs; PAN from the GSTIN (customers without one:
PANNOTAVBL); no TDS codes (set per vendor later).
Idempotent: existing CardCodes are skipped.  Run:  python tools/load_ake_bps.py [--dry] [--only C001 V025]
"""
import argparse, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ake_customers" / "bps.json"
HOME = "KT"
GROUPS = {"C": {"Intrastate": "Intrastate", "Interstate": "Interstate", "Export": "Export"},
          "S": {"Intrastate": "Intrastate Vendor", "Interstate": "Interstate Vendor", "Export": "Import Vendor"}}
ACCOUNTS = {"C": {"DebitorAccount": "5002-02-04-01", "DownPaymentClearAct": "3002-02-04"},
            "S": {"DebitorAccount": "3002-02-01", "DownPaymentClearAct": "5002-04-07-01"}}
GST_STATE = {gst: code for code, (_, gst) in L.STATES.items()}


def address(a, code):
    street = re.sub(r"^%s,\s*" % re.escape(code), "", a["Street"]).strip(" .,")
    zip_, block = a["Zip"], ""
    if a["Country"] == "IN" and not re.fullmatch(r"\d{6}", zip_.replace(" ", "")):
        zip_, block = "", zip_  # a locality in the zip column
    state = a["State"] or (GST_STATE.get(a["GSTIN"][:2]) if a["GSTIN"] else None) or (HOME if a["Country"] == "IN" else "")
    body = {"AddressName": a["AddressName"][:50], "AddressType": "bo_BillTo" if a["Type"] == "B" else "bo_ShipTo",
            "Street": street[:100], "Block": block[:100], "ZipCode": zip_.replace(" ", "")[:20], "City": a["City"][:100],
            "Country": a["Country"], "BuildingFloorRoom": a["Building"][:100]}
    if state:
        body["State"] = state
    if a["GSTIN"]:
        body.update(GSTIN=a["GSTIN"], GstType="gstRegularTDSISD")
    return body


def body_for(bp, grp):
    addrs, seen = [], set()
    for a in bp["Addresses"]:
        b = address(a, bp["Code"])
        name, n = b["AddressName"], 2
        while (b["AddressType"], b["AddressName"].upper()) in seen:  # names must be unique per address type
            b["AddressName"] = f"{name[:46]} ({n})"
            n += 1
        seen.add((b["AddressType"], b["AddressName"].upper()))
        addrs.append(b)
    bill = next((a for a in addrs if a["AddressType"] == "bo_BillTo"), addrs[0] if addrs else {})
    pos = "Export" if bill.get("Country", "IN") != "IN" else ("Intrastate" if bill.get("State", HOME) == HOME else "Interstate")
    body = {"CardCode": bp["Code"], "CardName": bp["Name"][:100], "CardType": "cCustomer" if bp["Type"] == "C" else "cSupplier",
            "GroupCode": grp[GROUPS[bp["Type"]][pos]], "Currency": "INR" if pos != "Export" else "##",
            **ACCOUNTS[bp["Type"]], "BPAddresses": addrs}
    if bp["Mobile"]:
        body["Cellular"] = bp["Mobile"][:50]
    if bp["Email"]:
        body["EmailAddress"] = bp["Email"][:100]
    # B1 India requires a PAN on customers; foreign / unregistered parties get the standard placeholder
    pan = bp["PAN"] or ("PANNOTAVBL" if bp["Type"] == "C" else "")
    if pan:
        body["BPFiscalTaxIDCollection"] = [{"Address": "", "TaxId0": pan}]
        if not bp["PAN"]:  # PANNOTAVBL needs a Deductee Ref. No. (TaxId13, exactly 10 alphanumerics)
            body["BPFiscalTaxIDCollection"][0]["TaxId13"] = bp["Code"].ljust(10, "0")
    if bp["PAN"]:
        body["TypeReport"] = "atOthers" if bp["PAN"][3] in "PH" else "atCompany"  # individual/HUF PAN
    return body, pos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    L.LOGS.mkdir(exist_ok=True)
    logf = L.LOGS / f"ake_bps_{L.dt.datetime.now():%Y%m%d_%H%M%S}.log"

    def log(msg):
        print(msg)
        with open(logf, "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
    sl = L.SL(L.read_env(), False, log)
    sl.login()
    grp = {g["Name"]: g["Code"] for g in sl.get("BusinessPartnerGroups")["value"]}
    have = {b["CardCode"].upper() for b in sl.get("BusinessPartners?$select=CardCode")["value"]}
    bps = [b for b in json.loads(SRC.read_text(encoding="utf-8")) if b["Active"] and (not a.only or b["Code"] in a.only)]
    done = skip = 0
    for bp in bps:
        if bp["Code"] in have:
            skip += 1
            continue
        body, pos = body_for(bp, grp)
        if a.dry:
            print(f"DRY {bp['Code']:6s} {pos:10s} {len(body['BPAddresses'])} addr  {bp['Name']}")
            continue
        if sl.post("BusinessPartners", body, f"{bp['Code']} {bp['Name']} ({pos})") is not None:
            done += 1
    print(f"created {done}, already there {skip}, failed {sl.failures} of {len(bps)} active BPs")


if __name__ == "__main__":
    main()
