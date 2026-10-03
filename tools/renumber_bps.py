"""One-off (2026-10-03): move the U1 BPs onto the normal C0xxx / V0xxx numbering and regroup customers by GST place
of supply (company state Karnataka) - customers and vendors: Intrastate = Karnataka, Interstate = other Indian state, Export = outside India.

Service Layer cannot change a CardCode, so a BP without transactions is re-created under the new code and the old one
deleted. A BP with transactions (U1C006, U1V001) must be renamed in the SAP client - the script only lists them.
Run:  python tools/renumber_bps.py [--dry]
"""
import argparse, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

RENAME = {"U1C001": "C0007", "U1C002": "C0008", "U1C003": "C0009", "U1C004": "C0010", "U1C005": "C0011",
          "U1C006": "C0012",
          "U1V001": "V0010", "U1V002": "V0011", "U1V003": "V0012", "U1V004": "V0013", "U1V005": "V0014",
          "U1V006": "V0015", "U1V007": "V0016", "U1V008": "V0017", "U1V009": "V0018"}
HOME_STATE = "KT"
# B1 group names are unique across customer and vendor groups
GROUPS = {"cCustomer": {"Intrastate": "Intrastate", "Interstate": "Interstate", "Export": "Export"},
          "cSupplier": {"Intrastate": "Intrastate Vendor", "Interstate": "Interstate Vendor", "Export": "Import Vendor"}}
TXN = ["Quotations", "Orders", "DeliveryNotes", "Invoices", "CreditNotes", "Returns", "DownPayments",
       "PurchaseRequests", "PurchaseQuotations", "PurchaseOrders", "PurchaseDeliveryNotes", "PurchaseInvoices",
       "PurchaseCreditNotes", "PurchaseReturns", "PurchaseDownPayments", "IncomingPayments", "VendorPayments"]
TYPES = {"cCustomer": "bbpgt_CustomerGroup", "cSupplier": "bbpgt_VendorGroup"}
KEEP = ["CardName", "CardType", "GroupCode", "Currency", "PayTermsGrpCode", "PriceListNum", "Cellular",
        "EmailAddress", "ContactPerson", "Notes", "DebitorAccount", "Series", "TypeReport", "SubjectToWithholdingTax"]


def group_for(bp):
    bill = next((a for a in bp["BPAddresses"] if a["AddressType"] == "bo_BillTo"), {})
    if bill.get("Country", "IN") != "IN":
        return "Export"
    return "Intrastate" if bill.get("State") == HOME_STATE else "Interstate"


def copy_body(bp, code):
    body = {k: bp[k] for k in KEEP}
    body["CardCode"] = code
    body["BPAddresses"] = [{k: v for k, v in a.items() if k not in ("BPCode", "RowNum", "CreateDate", "CreateTime")}
                           for a in bp["BPAddresses"]]
    body["ContactEmployees"] = [{k: c[k] for k in ("Name", "FirstName", "LastName", "Position", "MobilePhone", "E_Mail")}
                                for c in bp["ContactEmployees"]]
    body["BPFiscalTaxIDCollection"] = [{"Address": "", "TaxId0": t["TaxId0"]} for t in bp["BPFiscalTaxIDCollection"]
                                       if t["Address"] == ""]
    wt = [{"WTCode": w["WTCode"]} for w in bp.get("BPWithholdingTaxCollection", [])]
    if wt:
        body["BPWithholdingTaxCollection"] = wt
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    v = lambda path: sl.get(path)["value"]

    have = {(g["Type"], g["Name"]) for g in v("BusinessPartnerGroups")}
    for kind, gtype in TYPES.items():
        for name in GROUPS[kind].values():
            if (gtype, name) not in have:
                if a.dry:
                    print(f"DRY  group {gtype} {name}")
                else:
                    sl.post("BusinessPartnerGroups", {"Name": name, "Type": gtype}, f"BP group {gtype} {name}")
    grp = {(g["Type"], g["Name"]): g["Code"] for g in v("BusinessPartnerGroups")}
    used = set()
    for e in TXN:
        used |= {x["CardCode"] for x in (sl.get(f"{e}?$select=CardCode") or {"value": []})["value"]}

    manual = []
    for old, new in RENAME.items():
        if not sl.exists("BusinessPartners", old):
            continue
        if old in used:
            manual.append((old, new))
            continue
        if sl.exists("BusinessPartners", new):
            print(f"FAIL {new} already exists - {old} left alone")
            sl.failures += 1
            continue
        bp = sl.get(f"BusinessPartners('{old}')")
        body = copy_body(bp, new)
        body["GroupCode"] = grp.get((TYPES[bp["CardType"]], GROUPS[bp["CardType"]][group_for(bp)]), body["GroupCode"])
        if a.dry:
            print(f"DRY  {old} -> {new} {bp['CardName']}")
            continue
        if sl.post("BusinessPartners", body, f"{new} {bp['CardName']} (was {old})") is not None:
            r = sl.s.delete(f"{sl.base}/BusinessPartners('{old}')", timeout=60)
            print(f"{'OK  ' if r.status_code == 204 else 'FAIL'} DELETE {old}{'' if r.status_code == 204 else ': ' + r.text[:300]}")

    # every BP (incl. the ones still to be renamed) gets its place-of-supply group
    for bp in v("BusinessPartners?$select=CardCode,CardType,GroupCode,BPAddresses"):
        g = grp.get((TYPES[bp["CardType"]], GROUPS[bp["CardType"]][group_for(bp)]))
        if g and bp["GroupCode"] != g:
            if a.dry:
                print(f"DRY  {bp['CardCode']} group -> {group_for(bp)}")
            else:
                sl.patch("BusinessPartners", bp["CardCode"], {"GroupCode": g}, f"{bp['CardCode']} group {group_for(bp)}")

    # old segment groups are no longer used
    if not a.dry:
        for g in v("BusinessPartnerGroups"):
            if all(g["Name"] not in n.values() for n in GROUPS.values()):
                r = sl.s.delete(f"{sl.base}/BusinessPartnerGroups({g['Code']})", timeout=60)
                print(f"{'OK  ' if r.status_code == 204 else 'FAIL'} DELETE group {g['Code']} {g['Name']}"
                      f"{'' if r.status_code == 204 else ': ' + r.text[:200]}")

    for old, new in manual:
        print(f"TODO {old} has transactions - rename to {new} in the SAP client (BP Master Data > change BP code)")
    print(f"Done. Failures: {sl.failures}")


if __name__ == "__main__":
    main()
