"""Load the AKE training data package (data/*.json) into SAP Business One 10 (HANA) via Service Layer.

Credentials come from C:\\Projects\\AKE-Database\\.env (git-ignored), never from the command line:
    SL_URL=https://<hana-server>:50000/b1s/v2
    SL_COMPANY=<company DB schema, e.g. AKE_TRAINING>
    SL_USER=manager
    SL_PASSWORD=...
    SL_CA_FILE=sl_cert.crt       # Service Layer certificate exported from the server (self-signed)
    TRAINEE_PASSWORD=...         # initial password for the 6 training users

Usage:
    python tools/sl_loader.py --dry-run              # show what would be posted, no connection
    python tools/sl_loader.py --check                # log in and list the COA drawers only
    python tools/sl_loader.py                        # run all steps in order
    python tools/sl_loader.py --step items --step bps

Every step is idempotent: records that already exist are skipped, so the loader can be re-run after fixing an error.
Results are appended to logs/load_<timestamp>.log.
"""
import argparse, datetime as dt, json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"

# Keywords used to find each AKE section's drawer (level-1 account) in the new company.
DRAWER_KEYWORDS = {
    "Asset": ["asset"],
    "Liability": ["liabilit"],
    "Equity": ["equity", "capital"],
    "Revenue": ["revenue", "turnover", "income", "sales"],
    "Expenditure": ["expens", "expendit", "cost"],
}
STEPS = ["coa", "gldet", "gst", "tds", "finyear", "states", "location", "warehouses", "paymentterms", "series", "pricelists", "itemgroups", "items", "hsn", "bps",
         "resources", "boms", "freight", "users", "ob_stock", "ob_bp", "ob_gl"]


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def read_env():
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def key(k):
    """OData key: 'X' / 5 / {"Code": "X", "Type": -100} (composite)."""
    if isinstance(k, dict):
        return ",".join(f"{n}='{v}'" if isinstance(v, str) else f"{n}={v}" for n, v in k.items())
    return f"'{k}'" if isinstance(k, str) else k


class SL:
    def __init__(self, env, dry, log):
        self.env, self.dry, self.log = env, dry, log
        self.base = env.get("SL_URL", "").rstrip("/")
        self.s = None

    def login(self):
        if self.dry:
            return
        import requests
        # Trust the Service Layer's self-signed certificate explicitly (exported .crt/.pem file).
        ca = self.env.get("SL_CA_FILE")
        verify = str(ROOT / ca) if ca else True
        self.s = requests.Session()
        self.s.verify = verify
        r = self.s.post(f"{self.base}/Login", json={"CompanyDB": self.env["SL_COMPANY"],
                                                   "UserName": self.env["SL_USER"],
                                                   "Password": self.env["SL_PASSWORD"]}, timeout=60)
        if r.status_code != 200:
            sys.exit(f"Login failed ({r.status_code}): {r.text[:300]}")
        self.log(f"Logged in to {self.env['SL_COMPANY']} as {self.env['SL_USER']}")

    def get(self, path):
        r = self.s.get(f"{self.base}/{path}", timeout=120, headers={"Prefer": "odata.maxpagesize=1000"})
        return r.json() if r.status_code == 200 else None

    def exists(self, entity, k):
        if self.dry:
            return False
        return self.s.get(f"{self.base}/{entity}({key(k)})", timeout=60).status_code == 200

    def find(self, entity, field, value):
        """Return the first record where field == value (for entities keyed by a numeric id)."""
        if self.dry:
            return None
        v = str(value).replace("'", "''")
        res = self.get(f"{entity}?$filter={field} eq '{v}'")
        return res["value"][0] if res and res.get("value") else None

    def post(self, entity, body, label):
        if self.dry:
            self.log(f"DRY  POST {entity:22s} {label}")
            return {}
        r = self.s.post(f"{self.base}/{entity}", json=body, timeout=300)
        if r.status_code in (200, 201):
            self.log(f"OK   POST {entity:22s} {label}")
            return r.json() if r.text else {}
        try:
            msg = r.json()["error"]["message"]
            msg = msg.get("value", msg) if isinstance(msg, dict) else msg
        except Exception:
            msg = r.text[:300]
        self.log(f"FAIL POST {entity:22s} {label}: {msg}")
        self.failures += 1
        return None

    def patch(self, entity, k, body, label):
        if self.dry:
            self.log(f"DRY  PATCH {entity:21s} {label}")
            return
        r = self.s.patch(f"{self.base}/{entity}({key(k)})", json=body, timeout=120)
        ok = r.status_code in (200, 204)
        self.log(f"{'OK  ' if ok else 'FAIL'} PATCH {entity:21s} {label}{'' if ok else ': ' + r.text[:300]}")
        self.failures += 0 if ok else 1

    failures = 0


# ------------------------------------------------------------------------------------------- steps
def drawers(sl):
    if sl.dry:
        return {sec: f"<{sec} drawer>" for sec in DRAWER_KEYWORDS}
    res = sl.get("ChartOfAccounts?$filter=AccountLevel eq 1&$select=Code,Name")
    found = {}
    for sec, kws in DRAWER_KEYWORDS.items():
        hits = [a for a in res["value"] if any(k in a["Name"].lower() for k in kws)]
        if len(hits) != 1:
            sys.exit(f"Cannot map AKE section '{sec}' to exactly one drawer. Level-1 accounts: "
                     + ", ".join(f"{a['Code']} {a['Name']}" for a in res["value"])
                     + " - adjust DRAWER_KEYWORDS in tools/sl_loader.py")
        found[sec] = hits[0]["Code"]
    return found


def step_coa(sl):
    d = drawers(sl)
    sl.log("Drawers: " + ", ".join(f"{k} -> {v}" for k, v in d.items()))
    control = {b["ControlAccount"] for b in load("06_business_partners")}
    for a in load("01_chart_of_accounts"):
        if sl.exists("ChartOfAccounts", a["Code"]):
            continue
        # B1 rejects Revenue/Expense account types on title accounts ([OACT.ActType]) - titles stay 'Other'
        body = {"Code": a["Code"], "Name": a["Name"], "AccountType": "at_Other" if a["Title"] else a["AccountType"],
                "ActiveAccount": "tNO" if a["Title"] else "tYES",
                "FatherAccountKey": a["Parent"] or d[a["Section"]]}
        if a["Code"] in control:
            body["LockManualTransaction"] = "tYES"  # BP control account
        sl.post("ChartOfAccounts", body, f"{a['Code']} {a['Name'][:40]}")


def step_gst(sl):
    """Attach AKE's GST ledgers to the localization's regular CGST/SGST/IGST authorities; add the 40% slab codes."""
    cfg = load("07_gst_codes")
    by_type = {v["Type"]: v for v in cfg["Accounts"].values()}
    stas = [] if sl.dry else sl.get("SalesTaxAuthorities?$select=Code,Type,AOrRTaxAccount,AOrPTaxAccount")["value"]
    for a in stas:
        acc = by_type.get(a["Type"])
        # RCGST@9, RIGST@18 ... are reverse-charge authorities - left for manual setup
        if not acc or a["Code"].startswith("R") or (a["AOrRTaxAccount"], a["AOrPTaxAccount"]) == (acc["Output"], acc["Input"]):
            continue
        sl.patch("SalesTaxAuthorities", {"Code": a["Code"], "Type": a["Type"]}, {"AOrRTaxAccount": acc["Output"], "AOrPTaxAccount": acc["Input"]},
                 f"{a['Code']} -> {acc['Output']} / {acc['Input']}")
    for slab in cfg["NewSlabs"]:
        if sl.exists("SalesTaxCodes", slab["Code"]):
            continue
        tpl = None if sl.dry else sl.get(f"SalesTaxCodes('{slab['From']}')")
        types = {} if sl.dry else {l["STACode"]: l["STAType"] for l in tpl["SalesTaxCodes_Lines"]}
        for old, (code, name, rate) in slab["Authorities"].items():
            typ = types.get(old)
            if sl.exists("SalesTaxAuthorities", {"Code": code, "Type": typ}):
                continue
            acc = by_type.get(typ, {})
            sl.post("SalesTaxAuthorities", {"Code": code, "Name": name, "Type": typ, "Rate": rate,
                                            "AOrRTaxAccount": acc.get("Output"), "AOrPTaxAccount": acc.get("Input"),
                                            "TaxDefinitions": [{"Effectivefrom": slab["EffectiveFrom"], "Rate": rate}]}, code)
        if sl.dry:
            sl.log(f"DRY  POST {'SalesTaxCodes':22s} {slab['Code']} (cloned from {slab['From']})")
            continue
        lines = [{"STACode": slab["Authorities"][l["STACode"]][0], "STAType": l["STAType"], "FormulaId": l["FormulaId"]}
                 for l in tpl["SalesTaxCodes_Lines"]]
        sl.post("SalesTaxCodes", {"Code": slab["Code"], "Name": slab["Name"], "ValidForAR": "tYES", "ValidForAP": "tYES",
                                  "Freight": tpl["Freight"], "TypeFormulaCombId": tpl["TypeFormulaCombId"],
                                  "SalesTaxCodes_Lines": lines}, slab["Code"])


def step_finyear(sl):
    """India TDS financial years (threshold accumulation); AKE_DEMO only had FY2021-22."""
    have = set() if sl.dry else {f["Code"] for f in sl.s.post(f"{sl.base}/FinancialYearsService_GetFinancialYearList",
                                                                timeout=60).json()["value"]}
    for y in (2025, 2026):
        code = f"{y}{(y + 1) % 100:02d}"
        if code not in have:
            sl.post("FinancialYears", {"Code": code, "Description": f"FY{y}-{(y + 1) % 100:02d}",
                                       "StartDate": f"{y}-04-01", "EndDate": f"{y + 1}-03-31",
                                       "AssessYear": f"{y + 1}{(y + 2) % 100:02d}",
                                       "TCSAccumulationBase": "tcsAccumulationOnInvoice"}, f"FY{y}-{(y + 1) % 100:02d}")


TDS_RECEIVABLE = "5002-05-02-05"  # AKE 'TDS Receivables' - TDS deducted by customers (A/R side of every WT code)
TDS_LOCATION = 1  # WarehouseLocations code holding GSTIN/TAN - set to AKE Peenya by step_location


def tds_line(t):
    # 206AA (no PAN): 20%, 5% for 194Q. 206AB (non-filer) was omitted by Finance Act 2025 -> normal rate.
    return {"Effectivefrom": t.get("EffectiveFrom", "2025-04-01"), "Rate": t["Rate"], "TDSRate": t["Rate"], "SurchargeRate": 0, "CessRate": 0,
            "HSCRate": 0, "PANNonCompliantRate": 5 if t["Section"] == "194Q" else 20, "ITRNonCompliantRate": t["Rate"]}


def step_tds(sl):
    lst = lambda svc: {} if sl.dry else {s["Code"]: s["AbsEntry"] for s in
                                         sl.s.post(f"{sl.base}/{svc}", timeout=60).json()["value"]}
    sections = lst("SectionsService_GetSectionList")
    assessees = lst("NatureOfAssesseesService_GetNatureOfAssesseeList")  # COM / IND / HUF
    for t in load("07_tds_codes"):
        if not sl.dry and sl.exists("WithholdingTaxCodes", t["WTCode"]):
            cur = sl.get(f"WithholdingTaxCodes('{t['WTCode']}')?$select=WithholdingTaxCodes_Lines")["WithholdingTaxCodes_Lines"]
            want = tds_line(t)
            if cur and any(cur[0].get(k) != v for k, v in want.items() if k != "Effectivefrom"):
                sl.patch("WithholdingTaxCodes", t["WTCode"], {"WithholdingTaxCodes_Lines": [{**want, "LineNum": cur[0]["LineNum"]}]},
                         f"{t['WTCode']} rates / non-compliance rates")
            continue
        if not sl.dry and t["Section"] not in sections:
            sl.log(f"FAIL {t['WTCode']}: section {t['Section']} not in B1 - add it under Administration > Setup > "
                   "Financials > Tax > Section, then re-run --step tds")
            sl.failures += 1
            continue
        sl.post("WithholdingTaxCodes", {
            "WTCode": t["WTCode"], "WTName": t["Name"], "Category": "wtcc_Invoice", "BaseType": "wtcbt_Net",
            "BaseAmount": 100, "WithholdingType": "wt_IncomeTaxWithholding", "TdsType": "wtETds",
            "Section": sections.get(t["Section"]), "Assessee": assessees.get(t["Assessee"]), "Account": t["Account"], "APTDSAccount": t["Account"],
            # mandatory in B1 India; surcharge/cess are 0% for resident payees, so they share the TDS payable ledger
            "APSurchargeAccount": t["Account"], "APCessAccount": t["Account"], "APHSCAccount": t["Account"],
            **{f"AR{k}Account": TDS_RECEIVABLE for k in ("TDS", "Surcharge", "Cess", "HSC")},
            "Location": TDS_LOCATION, "ReturnType": "rt26Q",  # 26Q = TDS on resident non-salary payments
            "WithholdingTaxCodes_Lines": [tds_line(t)],
        }, f"{t['WTCode']} {t['Name']}")


def step_warehouses(sl):
    for w in load("02_warehouses"):
        if not sl.exists("Warehouses", w["WarehouseCode"]):
            # Location = AKE Peenya (GSTIN) - B1 India takes the GST place of supply from the warehouse location
            # warehouse accounts are only fallbacks (items post via their item group); B1 still requires them
            stock = {"FG": "5002-01-01-03", "CONS": "5002-01-01-09"}.get(w["WarehouseCode"], "5002-01-01-06")
            sl.post("Warehouses", {**w, "Location": TDS_LOCATION, "StockAccount": stock,
                                   "ExpenseAccount": "4001-16", "RevenuesAccount": "2001-01-01-01",
                                   "PurchaseAccount": "4008-01", "PriceDifferencesAccount": "4001-17",
                                   "VarianceAccount": "4001-23",
                                   "DecreasingAccount": "4001-21", "IncreaseGLAccount": "4001-20",
                                   "DecreaseGLAccount": "4001-21", "WIPMaterialAccount": "5002-01-02",
                                   "WIPMaterialVarianceAccount": "4001-23"}, w["WarehouseCode"])


# Company-wide G/L account determination (period category 1 = FY 2026-27), per docs/01_Company_Setup_Checklist.md Step 4.
# Item-level inventory/COGS/price-difference accounts come from the item groups (GLMethod = item group).
GL_DETERMINATION = {
    "DefaultSaleAccount": "2001-01-01-01", "SalesReturns": "2001-01-01-01", "RoundingAccount": "2001-01-04",
    "ARCashDiscountAccount": "4004-07-24", "CustomerDownPaymentsAccount": "3002-02-07-01",
    "PurchaseAccount": "4008-01", "PurchaseReturnAccount": "4008-01", "ExpenseAccountDefault": "4008-01",
    "GoodsClearingAcc": "3002-02-05", "AllocationAcc": "3002-02-05", "VendorDownPaymentsAccount": "5002-04-01-01",
    # payments on down payment requests post to these clearing / interim accounts (found by demo_finance.py)
    "DownPaymentPClearingAcct": "5002-04-07-01", "DownPaymentSClearingAcct": "3002-02-04",
    "PurchaseDownPaymentInterimAccount": "5002-04-04-01",
    "ExchangeRateDifferencesAcct": "4006-07", "OpeningBalancesAccount": "1003", "AcountforOpeningWHBalance": "1003",
    "CostOfGoodsSold": "4001-16", "PriceDifferenceAccount": "4001-17", "VarianceAcc": "4001-23",
    "IncreaseGLAccount": "4001-20", "DecreaseGLAcc": "4001-21",
    "InventoryOffsetIncrease": "4001-20", "InventoryOffsetDecrease": "4001-21",
    "WIPMaterialAccount": "5002-01-02", "WIPMaterialVarianceAccount": "4001-23",
    "NegativeInventoryAdjustmentAccount": "4001-21",
    # system currency is USD: payments post realized conversion differences in SC (needed by incoming payments)
    # credit memos (A/R returns reduce sales, A/P credits reduce purchases)
    "SalesCreditAcc": "2001-01-01-01", "PurchaseCreditAcc": "4008-01",
    "ARGainRealizedConversionDiff": "2003-02", "ARLossRealizedConversionDiff": "4006-07",
    "APGainRealizedConversionDiff": "2003-02", "APLossRealizedConversionDiff": "4006-07",
    "GLGainRealizedConversionDiff": "2003-02", "GLLossRealizedConversionDiff": "4006-07",
}


def step_gldet(sl):
    if sl.dry:
        sl.log(f"DRY  UPDATE PeriodCategory 1     {len(GL_DETERMINATION)} default accounts")
        return
    # down payment accounts must be control accounts in B1 [OACP.CDownPymnt]
    for acct in (GL_DETERMINATION["CustomerDownPaymentsAccount"], GL_DETERMINATION["VendorDownPaymentsAccount"]):
        if sl.get(f"ChartOfAccounts('{acct}')?$select=LockManualTransaction")["LockManualTransaction"] != "tYES":
            sl.patch("ChartOfAccounts", acct, {"LockManualTransaction": "tYES"}, f"{acct} -> control account")
    cur = sl.s.post(f"{sl.base}/CompanyService_GetPeriod", json={"PeriodCategoryParams": {"AbsoluteEntry": 1}}, timeout=60).json()
    diff = {k: v for k, v in GL_DETERMINATION.items() if cur.get(k) != v}
    if not diff:
        return
    cur.pop("@odata.context", None)
    r = sl.s.post(f"{sl.base}/CompanyService_UpdatePeriod", json={"PeriodCategory": {**cur, **diff}}, timeout=120)
    ok = r.status_code in (200, 204)
    sl.log(f"{'OK  ' if ok else 'FAIL'} UPDATE PeriodCategory 1     {len(diff)} accounts{'' if ok else ': ' + r.text[:300]}")
    sl.failures += 0 if ok else 1


# Numbering series FY 2026-27: (document object type, sub-type, name max 8 chars, prefix).
# B1 India: A/R + A/P invoices and credit memos use GST sub-types GA (GST invoice) / GD (GST debit note), not '--'.
SERIES = [
    ("23", "--", "SQ2627", "SQ/26-27/"), ("17", "--", "SO2627", "SO/26-27/"), ("15", "--", "DN2627", "DN/26-27/"),
    ("16", "--", "SR2627", "SR/26-27/"), ("13", "GA", "INV2627", "INV/26-27/"), ("13", "GD", "DBN2627", "DBN/26-27/"),
    ("14", "GA", "SCN2627", "SCN/26-27/"), ("203", "--", "ARD2627", "ARDP/26-27/"), ("24", "--", "RCT2627", "RCT/26-27/"),
    ("1470000113", "--", "PR2627", "PR/26-27/"), ("540000006", "--", "PQ2627", "PQ/26-27/"), ("22", "--", "PO2627", "PO/26-27/"),
    ("20", "--", "GRN2627", "GRN/26-27/"), ("21", "--", "PRT2627", "PRT/26-27/"), ("18", "GA", "PINV2627", "PINV/26-27/"),
    ("18", "GD", "PDN2627", "PDN/26-27/"), ("19", "GA", "PCN2627", "PCN/26-27/"), ("204", "--", "APD2627", "APDP/26-27/"),
    ("46", "--", "PAY2627", "PAY/26-27/"), ("59", "--", "GR2627", "GR/26-27/"), ("60", "--", "GI2627", "GI/26-27/"),
    ("1250000001", "--", "TRQ2627", "TRQ/26-27/"), ("67", "--", "TRF2627", "TRF/26-27/"), ("202", "--", "PRD2627", "PRD/26-27/"),
    ("30", "--", "JE2627", "JE/26-27/"),
]


def step_series(sl):
    """Add the FY series and make it the default for all users. B1's 'Primary' series is open-ended (1..inf) and
    would overlap: an unused Primary moves to 900000-999999; a used one is closed at its last number and locked,
    and the FY series continues from the next number."""
    svc = lambda action, body: sl.s.post(f"{sl.base}/SeriesService_{action}", json=body, timeout=60)
    for doc, sub, name, prefix in SERIES:
        if sl.dry:
            sl.log(f"DRY  ADD  Series {doc:>12s}/{sub} {name} {prefix}")
            continue
        have = svc("GetDocumentSeries", {"DocumentTypeParams": {"Document": doc, "DocumentSubType": sub}}).json().get("value", [])
        ser = next((x for x in have if x["Name"] == name), None)
        if not ser:
            start = 1
            for p in have:
                if p["Name"] != "Primary" or p["LastNumber"] is not None:
                    continue
                used = p["NextNumber"] > p["InitialNumber"]
                upd = ({**p, "LastNumber": p["NextNumber"] - 1, "Locked": "tYES"} if used else
                       {**p, "InitialNumber": 900000, "NextNumber": 900000, "LastNumber": 999999})
                r = svc("UpdateSeries", {"Series": upd})
                ok = r.status_code in (200, 204)
                sl.log(f"{'OK  ' if ok else 'FAIL'} {'CLOSE' if used else 'MOVE '} Series {doc:>12s}/{sub} Primary "
                       + (f"at {p['NextNumber'] - 1}" if used else "-> 900000-999999") + ("" if ok else ": " + r.text[:200]))
                if used:
                    start = p["NextNumber"]
            r = svc("AddSeries", {"Series": {"Document": doc, "DocumentSubType": sub, "Name": name, "Prefix": prefix,
                                             "InitialNumber": start, "LastNumber": 99999, "PeriodIndicator": "Default",
                                             "GroupCode": "sg_Group1", "Remarks": "FY 2026-27"}})
            if r.status_code not in (200, 201):
                sl.log(f"FAIL ADD  Series {doc:>12s}/{sub} {name}: {r.json()['error']['message']}")
                sl.failures += 1
                continue
            ser = {"Series": r.json()["Series"]}
            sl.log(f"OK   ADD  Series {doc:>12s}/{sub} {name:8s} {prefix} from {start} (series {ser['Series']})")
        r = svc("SetDefaultSeriesForAllUsers", {"Series": {"Document": doc, "DocumentSubType": sub, "Series": ser["Series"]}})
        if r.status_code not in (200, 204):
            sl.log(f"FAIL DEFAULT Series {doc}/{sub} {name}: {r.json()['error']['message']}")
            sl.failures += 1


def step_paymentterms(sl):
    for days in sorted({b["PaymentTermsDays"] for b in load("06_business_partners")}):
        name = f"Net {days} Days"
        if not sl.find("PaymentTermsTypes", "PaymentTermsGroupName", name):
            sl.post("PaymentTermsTypes", {"PaymentTermsGroupName": name, "NumberOfAdditionalDays": days}, name)


def price_list_no(sl, key):
    name = next(p["PriceListName"] for p in load("04_price_lists") if p["Key"] == key)
    rec = sl.find("PriceLists", "PriceListName", name)
    return rec["PriceListNo"] if rec else None


def step_pricelists(sl):
    for p in load("04_price_lists"):
        if not sl.find("PriceLists", "PriceListName", p["PriceListName"]):
            sl.post("PriceLists", {"PriceListName": p["PriceListName"], "Factor": 1}, p["PriceListName"])


def group_no(sl, name):
    rec = sl.find("ItemGroups", "GroupName", name)
    return rec["Number"] if rec else None


def step_itemgroups(sl):
    for g in load("03_item_groups"):
        if sl.find("ItemGroups", "GroupName", g["GroupName"]):
            continue
        # data uses short names; Service Layer calls the WIP fields WIPMaterial(Variance)Account
        ren = {"WipAccount": "WIPMaterialAccount", "WipVarianceAccount": "WIPMaterialVarianceAccount"}
        body = {"GroupName": g["GroupName"], "InventorySystem": g["InventorySystem"],
                **{ren.get(k, k): v for k, v in g["Accounts"].items()}}
        sl.post("ItemGroups", body, g["GroupName"])


def step_items(sl):
    groups = {g["GroupName"]: g for g in load("03_item_groups")}
    whs = [w["WarehouseCode"] for w in load("02_warehouses")]
    pur, sal = (None, None) if sl.dry else (price_list_no(sl, "PUR"), price_list_no(sl, "SAL"))
    for i in load("05_items"):
        if sl.exists("Items", i["ItemCode"]):
            continue
        make = i["ProcurementMethod"] == "bom_Make"
        prices = []
        if pur and i["PurchasePrice"]:
            prices.append({"PriceList": pur, "Price": i["PurchasePrice"]})
        if sal and i["DummySalesPrice"]:
            prices.append({"PriceList": sal, "Price": i["DummySalesPrice"]})
        body = {
            "ItemCode": i["ItemCode"], "ItemName": i["ItemName"],
            "ItemsGroupCode": None if sl.dry else group_no(sl, i["Group"]),
            "InventoryItem": "tYES", "PurchaseItem": "tNO" if make else "tYES",
            # PPE-SHOE is also resold to customers (footwear <= Rs 2,500: GST 5%)
            "SalesItem": "tYES" if i["Group"] in ("FG", "RM Plates", "RM Structurals") or i["ItemCode"] == "PPE-SHOE" else "tNO",
            "InventoryUOM": i["UoM"], "PurchaseUnit": i["UoM"], "SalesUnit": i["UoM"],
            "CostAccountingMethod": "bis_MovingAverage", "GLMethod": "glm_ItemClass",
            "ProcurementMethod": i["ProcurementMethod"], "IssueMethod": i["IssueMethod"],
            "MaterialType": groups[i["Group"]]["MaterialType"],
            "DefaultWarehouse": i["DefaultWarehouse"], "ManageStockByWarehouse": "tYES",
            "GSTRelevnt": "tYES", "GSTTaxCategory": "gtc_Regular",
            "ItemWarehouseInfoCollection": [{"WarehouseCode": w} for w in whs],
            "ItemPrices": prices,
        }
        sl.post("Items", body, f"{i['ItemCode']} {i['ItemName'][:35]}")


# Indian states used by AKE's BPs + localization defaults: B1 code -> (name, GST state code).
# AKE_DEMO shipped 7 states with no GST codes; GST place-of-supply needs them.
STATES = {"AP": ("Andhra Pradesh", "37"), "DL": ("Delhi", "07"), "HR": ("Haryana", "06"), "KT": ("Karnataka", "29"),
          "MH": ("Maharashtra", "27"), "MP": ("Madhya Pradesh", "23"), "UP": ("Uttar Pradesh", "09"),
          "TN": ("Tamil Nadu", "33"), "TS": ("Telangana", "36"), "KL": ("Kerala", "32"),
          # added 2026-10-05 for AKE's real customer/vendor list
          "WB": ("West Bengal", "19"), "GJ": ("Gujarat", "24"), "RJ": ("Rajasthan", "08"), "BR": ("Bihar", "10"),
          "PB": ("Punjab", "03"), "JH": ("Jharkhand", "20")}


def step_states(sl):
    have = {} if sl.dry else {s["Code"]: s for s in sl.get("States?$filter=Country eq 'IN'")["value"]}
    for code, (name, gst) in STATES.items():
        if code not in have:
            sl.post("States", {"Code": code, "Country": "IN", "Name": name, "GSTCode": gst}, f"{code} {name} ({gst})")
        elif have[code].get("GSTCode") != gst:
            sl.patch("States", {"Code": code, "Country": "IN"}, {"GSTCode": gst}, f"{code} GST code {gst}")


# AKE's registered location (GST + TDS). Replaces the demo 'Delhi' location 1 that the TDS codes point to.
AKE_LOCATION = {"Name": "Bangalore - Peenya", "BuildingFloorRoom": "#424", "Street": "11th Cross, IV Phase",
                "Block": "Peenya Industrial Area", "City": "Bangalore", "ZipCode": "560058", "State": "KT",
                "Country": "IN", "GSTIN": "29AAMCA5278K1ZZ", "GstType": "gstRegularTDSISD",
                # B1 India derives the location PAN from the first 10 chars of the (legacy excise) ECC number;
                # PANNumber itself is ignored on PATCH. ECC = PAN + 'XM001', as in the localization demo.
                "RegistrationType": "XM", "EccNumber": "AAMCA5278KXM001"}


def step_location(sl):
    cur = {} if sl.dry else sl.get(f"WarehouseLocations({TDS_LOCATION})")
    diff = {k: v for k, v in AKE_LOCATION.items() if cur.get(k) != v}
    if diff:
        sl.patch("WarehouseLocations", TDS_LOCATION, diff, f"{TDS_LOCATION} -> {AKE_LOCATION['Name']} ({AKE_LOCATION['GSTIN']})")


HSN_TEXT = {  # 4-digit HSN headings used by AKE's items
    "2711": "Petroleum gases (LPG)", "2804": "Oxygen and other gases", "3208": "Paints and varnishes",
    "4203": "Leather gloves", "6403": "Footwear (safety shoes)", "6506": "Safety headgear",
    "6804": "Grinding and cutting wheels", "7208": "Flat-rolled iron/steel (plates)", "7214": "Bars and rods (TMT)",
    "7216": "Angles, shapes and sections", "7219": "Stainless steel flat-rolled", "7306": "Tubes and pipes",
    "7308": "Structures and parts of structures", "7309": "Tanks and containers", "8205": "Hand tools (clamps)",
    "8311": "Welding electrodes and wire", "8467": "Power tools (grinders)", "9004": "Protective eyewear / shields",
}


def step_hsn(sl):
    """GST documents need the HSN (B1 India 'Chapter ID') on every item: create the headings, link the items."""
    have = {} if sl.dry else {h["ChapterID"]: h["AbsEntry"] for h in sl.get("IndiaHsn?$select=AbsEntry,ChapterID")["value"]}
    for hsn in sorted({i["HSN"] for i in load("05_items")}):
        if hsn not in have:
            res = sl.post("IndiaHsn", {"Chapter": hsn[:2], "Heading": hsn[2:4], "SubHeading": "",
                                       "Description": HSN_TEXT.get(hsn, hsn)}, f"HSN {hsn}")
            if res:
                have[hsn] = res.get("AbsEntry")
    for i in load("05_items"):
        if sl.dry:
            sl.log(f"DRY  PATCH Items {i['ItemCode']} HSN {i['HSN']}")
            continue
        cur = sl.get(f"Items('{i['ItemCode']}')?$select=ChapterID")
        if cur and have.get(i["HSN"]) and cur.get("ChapterID") != have[i["HSN"]]:
            sl.patch("Items", i["ItemCode"], {"ChapterID": have[i["HSN"]]}, f"{i['ItemCode']} HSN {i['HSN']}")


def state_code(sl, name, cache={}):
    if sl.dry:
        return name
    if not cache:
        res = sl.get("States?$filter=Country eq 'IN'&$select=Code,Name")
        cache.update({s["Name"].lower(): s["Code"] for s in (res or {}).get("value", [])})
    return cache.get(name.lower())


def step_bps(sl):
    for b in load("06_business_partners"):
        if sl.exists("BusinessPartners", b["CardCode"]):
            continue
        st = state_code(sl, b["State"])
        if st is None:
            sl.log(f"FAIL state '{b['State']}' not found for {b['CardCode']}")
            sl.failures += 1
            continue
        terms = None if sl.dry else (sl.find("PaymentTermsTypes", "PaymentTermsGroupName",
                                              f"Net {b['PaymentTermsDays']} Days") or {}).get("GroupNumber")
        addr = lambda t, n: {"AddressName": n, "AddressType": t, "City": b["City"], "Country": "IN",
                             "State": st, "GSTIN": b["GSTIN"], "GstType": "gstRegularTDSISD"}
        body = {"CardCode": b["CardCode"], "CardName": b["CardName"], "CardType": b["CardType"],
                "Currency": "INR", "DebitorAccount": b["ControlAccount"], "PayTermsGrpCode": terms,
                "BPAddresses": [addr("bo_BillTo", "Bill To"), addr("bo_ShipTo", "Ship To")],
                "BPFiscalTaxIDCollection": [{"Address": "", "TaxId0": b["PAN"]}]}
        if b.get("WTCode"):
            if sl.dry or sl.exists("WithholdingTaxCodes", b["WTCode"]):
                # B1 India: BP assessee type must match the WT code's (individual/HUF PAN -> 'Others')
                body["TypeReport"] = "atOthers" if b["PAN"][3] in "PH" else "atCompany"  # assessee type
                body.update({"SubjectToWithholdingTax": "boYES", "BPWithholdingTaxCollection": [{"WTCode": b["WTCode"]}]})
            else:
                sl.log(f"WARN {b['CardCode']}: TDS code {b['WTCode']} missing - vendor created without TDS")
        sl.post("BusinessPartners", body, f"{b['CardCode']} {b['CardName']}")


def step_resources(sl):
    for r in load("08_resources"):
        if sl.find("Resources", "VisCode", r["Code"]):  # VisCode = resource number shown in B1
            continue
        body = {"VisCode": r["Code"], "Name": r["Name"], "Type": r["Type"].replace("rt_", "rt"), "IssueMethod": "rimManual",
                "Cost1": r["CostPerMin"], "UnitOfMeasure": "Mins", "DefaultWarehouse": r["Warehouse"],  # resources in minutes
                "ResourceWarehouses": [{"Warehouse": r["Warehouse"]}]}
        sl.post("Resources", body, f"{r['Code']} {r['Name']}")


def step_boms(sl):
    for b in load("09_boms"):
        if b.get("DemoWrongVariant") or sl.exists("ProductTrees", b["TreeCode"]):
            continue
        lines = [{"ItemCode": l["Code"], "Quantity": l["Qty"], "ItemType": l["Type"],
                  "IssueMethod": l["IssueMethod"], **({"Warehouse": l["Warehouse"]} if l["Warehouse"] else {})}
                 for l in b["Lines"]]
        sl.post("ProductTrees", {"TreeCode": b["TreeCode"], "TreeType": "iProductionTree",
                                 "Quantity": b["Qty"], "Warehouse": b["Warehouse"],
                                 "ProductTreeLines": lines}, f"{b['TreeCode']} ({len(lines)} lines)")


def step_freight(sl):
    """Freight setup (additional expenses) as in AKE's B1: P&F charges capitalised into stock, transport expensed."""
    yn = lambda f: "tYES" if f else "tNO"
    have = set() if sl.dry else {f["Name"] for f in sl.get("AdditionalExpenses?$select=Name")["value"]}
    for f in load("12_freight"):
        if f["Name"] in have:
            continue
        sl.post("AdditionalExpenses", {"Name": f["Name"], "RevenuesAccount": f["RevenuesAccount"],
                                       "ExpenseAccount": f["ExpenseAccount"], "WTLiable": yn(f["WTLiable"]),
                                       "DistributionMethod": f["DistributionMethod"], "DrawingMethod": f["DrawingMethod"],
                                       "Stock": yn(f["Stock"]), "LastPurchasePrice": yn(f["LastPurchasePrice"])}, f["Name"])


def step_users(sl):
    pw = sl.env.get("TRAINEE_PASSWORD")
    if not pw and not sl.dry:
        sl.log("SKIP users: set TRAINEE_PASSWORD in .env")
        return
    for u in load("10_users"):
        if sl.find("Users", "UserCode", u["UserCode"]):
            continue
        sl.post("Users", {"UserCode": u["UserCode"], "UserName": u["UserName"], "UserPassword": pw,
                          "Superuser": "tYES" if u["Role"] == "Trainer" else "tNO"}, u["UserCode"])


def ob_done(sl, ref):
    return False if sl.dry else bool((sl.get(f"JournalEntries?$filter=Reference3 eq '{ref}'&$select=JdtNum")
                                       or {}).get("value"))


def step_ob_stock(sl):
    ob = load("11_opening_balances")
    if not sl.dry and sl.find("InventoryGenEntries", "Reference2", "AKE-OB-STOCK"):
        return
    lines = [{"ItemCode": s["ItemCode"], "WarehouseCode": s["Warehouse"], "Quantity": s["Qty"],
              "UnitPrice": s["Price"], "AccountCode": ob["OffsetAccount"]} for s in ob["Stock"]]
    sl.post("InventoryGenEntries", {"DocDate": ob["Date"], "Reference2": "AKE-OB-STOCK",
                                    "Comments": "Dummy opening stock - AKE training DB",
                                    "DocumentLines": lines}, f"opening stock ({len(lines)} lines)")


def step_ob_bp(sl):
    ob = load("11_opening_balances")
    if ob_done(sl, "AKE-OB-BP"):
        return
    lines = []
    for b in ob["BP"]:
        amt = b["Amount"]
        lines.append({"ShortName": b["CardCode"], "Debit": max(amt, 0), "Credit": max(-amt, 0)})
        lines.append({"AccountCode": ob["OffsetAccount"], "Debit": max(-amt, 0), "Credit": max(amt, 0)})
    sl.post("JournalEntries", {"ReferenceDate": ob["Date"], "Reference3": "AKE-OB-BP",
                               "Memo": "Dummy BP opening balances", "JournalEntryLines": lines}, "BP opening balances")


def step_ob_gl(sl):
    ob = load("11_opening_balances")
    if ob_done(sl, "AKE-OB-GL"):
        return
    lines = [{"AccountCode": g["Account"], "Debit": max(g["Amount"], 0), "Credit": max(-g["Amount"], 0)}
             for g in ob["GL"]]
    net = sum(g["Amount"] for g in ob["GL"])
    lines.append({"AccountCode": ob["OffsetAccount"], "Debit": max(-net, 0), "Credit": max(net, 0)})
    sl.post("JournalEntries", {"ReferenceDate": ob["Date"], "Reference3": "AKE-OB-GL",
                               "Memo": "Dummy GL opening balances", "JournalEntryLines": lines}, "GL opening balances")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="log in and show the drawer mapping only")
    ap.add_argument("--step", action="append", choices=STEPS)
    a = ap.parse_args()

    LOGS.mkdir(exist_ok=True)
    logf = LOGS / f"load_{dt.datetime.now():%Y%m%d_%H%M%S}.log"
    def log(msg):
        print(msg)
        with logf.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")

    env = read_env()
    if not a.dry_run:
        missing = [k for k in ("SL_URL", "SL_COMPANY", "SL_USER", "SL_PASSWORD") if not env.get(k)]
        if missing:
            sys.exit(f"Missing in .env: {', '.join(missing)}")
    sl = SL(env, a.dry_run, log)
    sl.login()
    if a.check:
        log("Drawers: " + json.dumps(drawers(sl)))
        return
    for name in a.step or STEPS:
        log(f"--- {name}")
        globals()[f"step_{name}"](sl)
    log(f"Done. Failures: {sl.failures}. Log: {logf}")


if __name__ == "__main__":
    main()
