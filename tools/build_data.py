"""Build the AKE training-database data package (data/*.json) from AKE's COA export + dummy masters.

Run:  python tools/build_data.py
Output is consumed by tools/sl_loader.py. All master data except the Chart of Accounts is DUMMY.
"""
import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

def dump(name, obj):
    (DATA / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{name:22s} {len(obj) if isinstance(obj, list) else '-':>5}")

# ---------------------------------------------------------------- Chart of Accounts (AKE real, as-is)
COA_FILES = [  # (section, file, B1 AccountType)
    ("Asset", "Chart of Accounts Assest.csv", "at_Other"),
    ("Liability", "Chart of Accounts .csv liability.csv", "at_Other"),
    ("Equity", "Chart of Accounts equity.csv", "at_Other"),
    ("Revenue", "Chart of Accounts Revenue.csv", "at_Revenues"),
    ("Expenditure", "Chart of Accounts Expendiature.csv", "at_Expenses"),
]

def build_coa():
    """The export lost the tree indentation, so the parent of each account is reconstructed:
    1. longest code-prefix ancestor (e.g. 5001-01 for 5001-01-02) that appears EARLIER in the same section file;
    2. otherwise the nearest preceding title account in the file (keeps AKE's misplaced accounts where they are,
       e.g. 3002-xx lender accounts stay under 5002-05-06 Others in the Asset drawer);
    3. top-level codes (one segment) hang directly under the drawer."""
    accounts, review = [], []
    for section, fname, atype in COA_FILES:
        rows = []
        for ln in (ROOT / fname).read_text(encoding="utf-16").splitlines()[1:]:
            ln = ln.strip().strip('"')
            if not ln:
                continue
            m = re.match(r"^(\S+)\s*-\s*(.*)$", ln)
            rows.append((m.group(1), m.group(2).strip()))
        codes = [c for c, _ in rows]
        # a row is a title if some other row in the section has it as a code-prefix ancestor
        titles = {c for c in codes if any(o != c and o.startswith(c + "-") for o in codes)}
        seen, last_title = set(), None
        for code, name in rows:
            segs = code.split("-")
            parent, how = None, "drawer"
            if len(segs) > 1:
                for k in range(len(segs) - 1, 0, -1):
                    p = "-".join(segs[:k])
                    if p in seen:
                        parent, how = p, "code"
                        break
                if parent is None:
                    parent, how = last_title, "position"
            elif not re.fullmatch(r"\d{4}", code):  # malformed single-segment code, e.g. 3002007
                parent, how = last_title, "position"
            if how == "position":
                review.append({"Code": code, "Name": name, "Section": section, "PlacedUnder": parent})
            accounts.append({"Code": code, "Name": name or f"(No name in AKE COA) {code}",
                             "NameBlankInSource": not name, "Section": section, "AccountType": atype,
                             "Parent": parent, "ParentRule": how})
            seen.add(code)
            if code in titles:
                last_title = code
    has_child = {a["Parent"] for a in accounts if a["Parent"]}
    for a in accounts:
        a["Title"] = a["Code"] in has_child
    # creation order: parents before children
    depth = {}
    byc = {a["Code"]: a for a in accounts}
    def d(c):
        if c not in depth:
            p = byc[c]["Parent"]
            depth[c] = 0 if p is None else d(p) + 1
        return depth[c]
    for a in accounts:
        a["Depth"] = d(a["Code"])
    accounts.sort(key=lambda a: a["Depth"])
    return accounts, review

coa, coa_review = build_coa()
dump("01_chart_of_accounts", coa)
dump("01_coa_placement_review", coa_review)

# ---------------------------------------------------------------- Warehouses
warehouses = [
    {"WarehouseCode": "RM-STR", "WarehouseName": "Raw Material Store - Dabaspet"},
    {"WarehouseCode": "CONS", "WarehouseName": "Consumables & PPE Store"},
    {"WarehouseCode": "SHOP", "WarehouseName": "Shop Floor / Fabrication Bay"},
    {"WarehouseCode": "FG", "WarehouseName": "Finished Goods Yard"},
    {"WarehouseCode": "SCRAP", "WarehouseName": "Scrap & Off-cuts"},
    {"WarehouseCode": "SITE", "WarehouseName": "Project Site Store"},
]
dump("02_warehouses", warehouses)

# ---------------------------------------------------------------- Item groups -> AKE's own inventory / consumption accounts
GRNI, PPV, STKDIFF_G, STKDIFF_L, REVAL_G, REVAL_L = "3002-02-05", "4001-17", "4001-20", "4001-21", "4001-18", "4001-19"
item_groups = [
    # (name, inventory acct, consumption/expense acct, material type)
    ("RM Plates", "5002-01-01-06", "4001-06", "mt_RawMaterial"),
    ("RM Structurals", "5002-01-01-08", "4001-08", "mt_RawMaterial"),
    ("RM Special Grades", "5002-01-01-07", "4001-07", "mt_RawMaterial"),
    ("TMT Rod", "5002-01-01-18", "4001-08", "mt_RawMaterial"),
    ("Consumables", "5002-01-01-09", "4001-09", "mt_RawMaterial"),
    ("PPE", "5002-01-01-04", "4001-04", "mt_RawMaterial"),
    ("Tools", "5002-01-01-05", "4001-05", "mt_RawMaterial"),
    ("Sub Assembly", "5002-01-01-01", "4001-01", "mt_GoodsInProcess"),
    ("FG", "5002-01-01-03", "4001-16", "mt_FinishedGoods"),
]
dump("03_item_groups", [{
    "GroupName": n, "InventorySystem": "bis_MovingAverage", "MaterialType": mt,
    "Accounts": {"InventoryAccount": inv, "CostAccount": "4001-16", "ExpensesAccount": exp,
                 "PurchaseAccount": "4008-01", "RevenuesAccount": "2001-01-01-01",  # 2001-01-01 is a title in AKE COA; its only child is unnamed
                 "PriceDifferencesAccount": PPV, "GoodsClearingAccount": GRNI,
                 "IncreasingAccount": STKDIFF_G, "DecreasingAccount": STKDIFF_L,
                 "WipAccount": "5002-01-02", "WipVarianceAccount": "4001-23"}}
    for n, inv, exp, mt in item_groups])

# ---------------------------------------------------------------- Price lists (DUMMY prices; trainees get no authorization)
price_lists = [
    {"PriceListName": "Purchase Price (Dummy)", "Key": "PUR"},
    {"PriceListName": "Sales Price (Dummy - Restricted)", "Key": "SAL"},
]
dump("04_price_lists", price_lists)

# ---------------------------------------------------------------- Items (DUMMY, realistic fabrication masters)
# (code, name, group, uom, hsn, gst%, purchase price, dummy sales price, default whs, make/buy)
I = [
    ("RM-PL-0010", "MS Plate IS2062 E250 10mm", "RM Plates", "KG", "7208", 18, 62, None, "RM-STR", "B"),
    ("RM-PL-0012", "MS Plate IS2062 E250 12mm", "RM Plates", "KG", "7208", 18, 61, None, "RM-STR", "B"),
    ("RM-PL-0016", "MS Plate IS2062 E250 16mm", "RM Plates", "KG", "7208", 18, 60, None, "RM-STR", "B"),
    ("RM-PL-0020", "MS Plate IS2062 E250 20mm", "RM Plates", "KG", "7208", 18, 60, None, "RM-STR", "B"),
    ("RM-PL-0006", "MS Chequered Plate 6mm", "RM Plates", "KG", "7208", 18, 66, None, "RM-STR", "B"),
    ("RM-ST-MB200", "ISMB 200 Beam", "RM Structurals", "KG", "7216", 18, 58, None, "RM-STR", "B"),
    ("RM-ST-MB300", "ISMB 300 Beam", "RM Structurals", "KG", "7216", 18, 58, None, "RM-STR", "B"),
    ("RM-ST-MC100", "ISMC 100 Channel", "RM Structurals", "KG", "7216", 18, 57, None, "RM-STR", "B"),
    ("RM-ST-MC150", "ISMC 150 Channel", "RM Structurals", "KG", "7216", 18, 57, None, "RM-STR", "B"),
    ("RM-ST-A50", "ISA 50x50x6 Angle", "RM Structurals", "KG", "7216", 18, 56, None, "RM-STR", "B"),
    ("RM-ST-A75", "ISA 75x75x8 Angle", "RM Structurals", "KG", "7216", 18, 56, None, "RM-STR", "B"),
    ("RM-ST-PIPE50", "MS ERW Pipe 50NB Medium", "RM Structurals", "KG", "7306", 18, 68, None, "RM-STR", "B"),
    ("RM-SG-E350-12", "Plate IS2062 E350 12mm", "RM Special Grades", "KG", "7208", 18, 72, None, "RM-STR", "B"),
    ("RM-SG-SS304-3", "SS304 Sheet 3mm", "RM Special Grades", "KG", "7219", 18, 245, None, "RM-STR", "B"),
    ("RM-TMT-12", "TMT Bar Fe500D 12mm", "TMT Rod", "KG", "7214", 18, 55, None, "RM-STR", "B"),
    ("RM-TMT-16", "TMT Bar Fe500D 16mm", "TMT Rod", "KG", "7214", 18, 55, None, "RM-STR", "B"),
    ("CN-ELEC-E6013", "Welding Electrode E6013 3.15mm", "Consumables", "KG", "8311", 18, 165, None, "CONS", "B"),
    ("CN-MIG-ER70", "MIG Wire ER70S-6 1.2mm", "Consumables", "KG", "8311", 18, 140, None, "CONS", "B"),
    ("CN-GRIND-4", "Grinding Wheel 4 inch", "Consumables", "NOS", "6804", 18, 38, None, "CONS", "B"),
    ("CN-CUT-14", "Cut-off Wheel 14 inch", "Consumables", "NOS", "6804", 18, 210, None, "CONS", "B"),
    ("CN-OXY", "Oxygen Gas Cylinder 7 m3", "Consumables", "NOS", "2804", 18, 420, None, "CONS", "B"),
    ("CN-LPG", "LPG Cutting Gas 19kg", "Consumables", "NOS", "2711", 18, 1850, None, "CONS", "B"),
    ("CN-PRIMER", "Red Oxide Zinc Chromate Primer", "Consumables", "LTR", "3208", 18, 210, None, "CONS", "B"),
    ("CN-ENAMEL", "Synthetic Enamel Paint Grey", "Consumables", "LTR", "3208", 18, 290, None, "CONS", "B"),
    ("PPE-HELMET", "Safety Helmet ISI", "PPE", "NOS", "6506", 18, 180, None, "CONS", "B"),
    ("PPE-GLOVE-W", "Welding Gloves Leather", "PPE", "PAIR", "4203", 12, 145, None, "CONS", "B"),
    ("PPE-SHOE", "Safety Shoes Steel Toe", "PPE", "PAIR", "6403", 5, 950, 1200, "CONS", "B"),
    ("PPE-SHIELD", "Welding Face Shield", "PPE", "NOS", "9004", 18, 260, None, "CONS", "B"),
    ("TL-GRINDER", "Angle Grinder 4 inch 850W", "Tools", "NOS", "8467", 18, 3200, None, "CONS", "B"),
    ("TL-CLAMP", "C-Clamp 8 inch", "Tools", "NOS", "8205", 18, 420, None, "CONS", "B"),
    ("SA-BASEPL-400", "Base Plate Assembly 400x400x20", "Sub Assembly", "NOS", "7308", 18, 0, None, "SHOP", "M"),
    ("SA-GUSSET-12", "Gusset Plate Set 12mm", "Sub Assembly", "SET", "7308", 18, 0, None, "SHOP", "M"),
    ("FG-COL-MB300-6M", "Steel Column ISMB300 6m with Base Plate", "FG", "NOS", "7308", 18, 0, 92000, "FG", "M"),
    ("FG-PRACK-6M", "Pipe Rack Module 6m x 3m", "FG", "NOS", "7308", 18, 0, 485000, "FG", "M"),
    ("FG-PLAT-HR", "Access Platform with Handrail 3m x 1.5m", "FG", "NOS", "7308", 18, 0, 128000, "FG", "M"),
    ("FG-CTRAY-300", "Cable Tray Ladder Type 300mm x 2.5m", "FG", "NOS", "7308", 18, 0, 3400, "FG", "M"),
    ("FG-TANK-5KL", "MS Storage Tank 5 KL", "FG", "NOS", "7309", 18, 0, 210000, "FG", "M"),
]
items = [{
    "ItemCode": c, "ItemName": n, "Group": g, "UoM": u, "HSN": h, "GSTRate": gst,
    "PurchasePrice": pp, "DummySalesPrice": sp, "DefaultWarehouse": w,
    "ProcurementMethod": "bom_Make" if mb == "M" else "bom_Buy",
    "IssueMethod": "im_Manual",  # AKE issues for production manually (confirmed 1 Oct 2026)
} for c, n, g, u, h, gst, pp, sp, w, mb in I]
dump("05_items", items)

# ---------------------------------------------------------------- Business partners (DUMMY - fictional names, structurally valid GSTIN)
def gstin(state, pan):
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    body = f"{state}{pan}1Z"
    total = 0
    for i, ch in enumerate(body):
        v = chars.index(ch) * (2 if i % 2 else 1)
        total += v // 36 + v % 36
    return body + chars[(36 - total % 36) % 36]

STATES = {"29": "Karnataka", "33": "Tamil Nadu", "27": "Maharashtra", "36": "Telangana", "32": "Kerala"}
BP = [  # code, name, type, state, PAN, city, payment terms days, TDS section (vendors)
    ("V0001", "Shree Ganesh Steel Traders", "S", "29", "AAKFS4821K", "Bengaluru", 30, "194Q"),
    ("V0002", "Deccan Structural Steels Pvt Ltd", "S", "36", "AADCD7315M", "Hyderabad", 45, "194Q"),
    ("V0003", "Kaveri Special Alloys LLP", "S", "33", "AAQFK2290B", "Chennai", 30, None),
    ("V0004", "Nandi Welding Consumables", "S", "29", "ABNPN6612R", "Bengaluru", 15, None),
    ("V0005", "Vayu Industrial Gases", "S", "29", "AAHCV3304L", "Tumakuru", 15, None),
    ("V0006", "Suraksha Safety Solutions", "S", "27", "AAPFS9087C", "Pune", 30, None),
    ("V0007", "Bharathi Blasting & Coating Works", "S", "29", "ACBPB4410J", "Nelamangala", 30, "194C"),
    ("V0008", "Mysore Freight Carriers", "S", "29", "AAJFM1176E", "Mysuru", 15, "194C"),
    ("V0009", "Prakash & Associates Chartered Engineers", "S", "29", "AAEFP5521Q", "Bengaluru", 30, "194J"),
    ("C0001", "Sahyadri Infra Projects Pvt Ltd", "C", "27", "AAGCS6631P", "Mumbai", 45, None),
    ("C0002", "Coromandel Power Engineering Ltd", "C", "33", "AABCC8842H", "Chennai", 60, None),
    ("C0003", "Vijayanagar Petrochem Industries Ltd", "C", "29", "AACCV2207N", "Ballari", 45, None),
    ("C0004", "Nila Cement Works Pvt Ltd", "C", "32", "AAICN4419D", "Palakkad", 30, None),
    ("C0005", "Telangana Urban Metro Contractors", "C", "36", "AAFFT7753G", "Hyderabad", 60, None),
    ("C0006", "Hosur Auto Components Pvt Ltd", "C", "33", "AAHCH3398F", "Hosur", 30, None),
]
bps = [{
    "CardCode": c, "CardName": n, "CardType": "cSupplier" if t == "S" else "cCustomer",
    "State": STATES[s], "GSTStateCode": s, "City": city, "PAN": pan, "GSTIN": gstin(s, pan),
    "PaymentTermsDays": days, "TDSSection": tds,
    # 194C: 1% for individual/HUF (PAN 4th char P/H), else 2%
    "WTCode": {"194Q": "Q01", "194J": "J10", "194C": "C1" if pan[3] in "PH" else "C2"}.get(tds),
    "ControlAccount": "3002-02-01" if t == "S" else "5002-02-04-01",
} for c, n, t, s, pan, city, days, tds in BP]
dump("06_business_partners", bps)

# ---------------------------------------------------------------- Tax: GST codes + TDS (per AKE's existing TDS accounts)
# B1 India localization ships GST tax types CGST(-100) / SGST(-110) / IGST(-120) with authorities (CGST@9 ...) and
# tax codes (CG+SG@18, IGST@18 ...) but no accounts. The loader attaches AKE's ledgers to every regular (non-RCM)
# authority of each type, and adds the GST 2.0 40% slab (w.e.f. 22-Sep-2025) by cloning the 18% codes.
gst_codes = {
    "Accounts": {  # tax type -> AKE output (A/R) / input (A/P) ledger
        "CGST": {"Type": -100, "Output": "3002-03-24", "Input": "5002-05-02-02"},
        "SGST": {"Type": -110, "Output": "3002-03-25", "Input": "5002-05-02-01"},
        "IGST": {"Type": -120, "Output": "3002-03-22", "Input": "5002-05-02-03"},
    },
    "NewSlabs": [  # new code cloned from template code, authorities renamed by rate
        {"Code": "CG+SG@40", "Name": "CGST 20% + SGST 20%", "From": "CG+SG@18", "EffectiveFrom": "2025-09-22",
         "Authorities": {"CGST@9": ("CGST@20", "CGST @ 20%", 20), "SGST@9": ("SGST@20", "SGST @ 20%", 20)}},
        {"Code": "IGST@40", "Name": "IGST 40%", "From": "IGST@18", "EffectiveFrom": "2025-09-22",
         "Authorities": {"IGST@18": ("IGST@40", "IGST @ 40%", 40)}},
    ],
}
# B1 withholding tax codes are max 4 characters. Assessee = B1 nature of assessee (COM / IND / HUF). Section = code in B1's India section list (194Q added if missing).
tds_codes = [
    {"WTCode": "Q01", "Name": "TDS on Purchase of Goods 0.1%", "Section": "194Q", "Assessee": "COM", "Rate": 0.1, "Account": "3002-03-23"},
    {"WTCode": "C1", "Name": "TDS Contractor Individual/HUF 1%", "Section": "194C", "Assessee": "IND", "Rate": 1, "Account": "3002-03-18"},
    {"WTCode": "C2", "Name": "TDS Contractor Others 2%", "Section": "194C", "Assessee": "COM", "Rate": 2, "Account": "3002-03-14"},
    {"WTCode": "J10", "Name": "TDS Professional Fees 10%", "Section": "194J", "Assessee": "COM", "Rate": 10, "Account": "3002-03-16"},
    {"WTCode": "I10", "Name": "TDS on Rent 10%", "Section": "194I", "Assessee": "COM", "Rate": 10, "Account": "3002-03-15"},
    {"WTCode": "A10", "Name": "TDS on Interest 10%", "Section": "194A", "Assessee": "COM", "Rate": 10, "Account": "3002-03-26"},
]
dump("07_gst_codes", gst_codes)
dump("07_tds_codes", tds_codes)

# ---------------------------------------------------------------- Resources (Production to Stock) -> AKE conversion accounts 3003-02-xx
resources = [
    {"Code": "R-CUT-PLASMA", "Name": "CNC Plasma Cutting Machine", "Type": "rt_Machine", "CostPerHour": 1200, "Warehouse": "SHOP"},
    {"Code": "R-SAW", "Name": "Band Saw Machine", "Type": "rt_Machine", "CostPerHour": 450, "Warehouse": "SHOP"},
    {"Code": "R-DRILL", "Name": "Radial Drilling Machine", "Type": "rt_Machine", "CostPerHour": 500, "Warehouse": "SHOP"},
    {"Code": "R-WELD-MIG", "Name": "MIG Welding Station", "Type": "rt_Machine", "CostPerHour": 600, "Warehouse": "SHOP"},
    {"Code": "R-BLAST", "Name": "Shot Blasting & Painting Booth", "Type": "rt_Machine", "CostPerHour": 900, "Warehouse": "SHOP"},
    {"Code": "R-FITTER", "Name": "Fitter (Labour)", "Type": "rt_Labor", "CostPerHour": 350, "Warehouse": "SHOP"},
    {"Code": "R-WELDER", "Name": "Welder (Labour)", "Type": "rt_Labor", "CostPerHour": 400, "Warehouse": "SHOP"},
]
for r in resources:
    r["Accounts"] = {"ResourceCostAccount": "3003-02-02" if r["Type"] == "rt_Labor" else "3003-02-03",
                     "OverheadAccount": "3003-02-04"}
dump("08_resources", resources)

# ---------------------------------------------------------------- BOMs (production trees). Weights are realistic (kg per unit).
boms = [
    {"TreeCode": "SA-BASEPL-400", "Qty": 1, "Warehouse": "SHOP", "Lines": [
        ("RM-PL-0020", 25.1, "RM-STR"), ("CN-ELEC-E6013", 0.4, "CONS"),
        ("R-CUT-PLASMA", 0.25, None), ("R-WELDER", 0.5, None)]},
    {"TreeCode": "SA-GUSSET-12", "Qty": 1, "Warehouse": "SHOP", "Lines": [
        ("RM-PL-0012", 6.8, "RM-STR"), ("R-CUT-PLASMA", 0.2, None)]},
    {"TreeCode": "FG-COL-MB300-6M", "Qty": 1, "Warehouse": "FG", "Lines": [
        ("RM-ST-MB300", 265.2, "RM-STR"), ("SA-BASEPL-400", 1, "SHOP"), ("SA-GUSSET-12", 1, "SHOP"),
        ("CN-MIG-ER70", 1.5, "CONS"), ("CN-PRIMER", 2.5, "CONS"), ("CN-ENAMEL", 2.0, "CONS"),
        ("R-SAW", 0.5, None), ("R-DRILL", 0.5, None), ("R-WELD-MIG", 2, None), ("R-FITTER", 3, None),
        ("R-WELDER", 2, None), ("R-BLAST", 1, None)]},
    {"TreeCode": "FG-PLAT-HR", "Qty": 1, "Warehouse": "FG", "Lines": [
        ("RM-PL-0006", 212.0, "RM-STR"), ("RM-ST-MC150", 96.0, "RM-STR"), ("RM-ST-PIPE50", 58.0, "RM-STR"),
        ("CN-MIG-ER70", 3.0, "CONS"), ("CN-PRIMER", 4.0, "CONS"), ("CN-ENAMEL", 3.5, "CONS"),
        ("R-CUT-PLASMA", 1, None), ("R-WELD-MIG", 5, None), ("R-FITTER", 8, None), ("R-WELDER", 6, None), ("R-BLAST", 2, None)]},
    {"TreeCode": "FG-CTRAY-300", "Qty": 1, "Warehouse": "FG", "Lines": [
        ("RM-ST-A50", 11.3, "RM-STR"), ("CN-ELEC-E6013", 0.15, "CONS"), ("CN-ENAMEL", 0.3, "CONS"),
        ("R-SAW", 0.2, None), ("R-WELDER", 0.5, None)]},
    # Deliberately WRONG BOM for the B3 demonstration: MB300 entered as 2652 kg instead of 265.2 kg (decimal slip)
    {"TreeCode": "FG-COL-MB300-6M", "Qty": 1, "Warehouse": "FG", "DemoWrongVariant": True,
     "Note": "Training exercise only - NOT loaded. Trainer edits the live BOM line to 2652 to show the effect, then corrects it.",
     "Lines": [("RM-ST-MB300", 2652, "RM-STR")]},
]
for b in boms:
    b["Lines"] = [{"Code": c, "Qty": q, "Warehouse": w,
                   "Type": "pit_Resource" if c.startswith("R-") else "pit_Item",
                   "IssueMethod": "im_Manual"} for c, q, w in b["Lines"]]
dump("09_boms", boms)

# ---------------------------------------------------------------- Users (6 licences)
users = [
    {"UserCode": "RASHMI", "UserName": "Rashmi - Director", "Role": "Director"},
    {"UserCode": "NAMRATA", "UserName": "Namrata - Director", "Role": "Director"},
    {"UserCode": "ASHOK", "UserName": "Ashok - Planning & SCM", "Role": "Planning"},
    {"UserCode": "SUNIL", "UserName": "Sunil - Finance", "Role": "Finance"},
    {"UserCode": "VEENA", "UserName": "Veena - Accounts", "Role": "Accounts"},
    {"UserCode": "TRAINER", "UserName": "Qltc Trainer", "Role": "Trainer"},
]
dump("10_users", users)

# ---------------------------------------------------------------- Dummy opening balances (as of 01-Apr-2026, FY 2026-27)
OB_DATE = "2026-04-01"
stock_ob = [  # item, warehouse, qty  (valued at purchase price)
    ("RM-PL-0010", "RM-STR", 4200), ("RM-PL-0012", "RM-STR", 3800), ("RM-PL-0016", "RM-STR", 2500),
    ("RM-PL-0020", "RM-STR", 3000), ("RM-PL-0006", "RM-STR", 1800), ("RM-ST-MB200", "RM-STR", 2200),
    ("RM-ST-MB300", "RM-STR", 3500), ("RM-ST-MC100", "RM-STR", 1500), ("RM-ST-MC150", "RM-STR", 1600),
    ("RM-ST-A50", "RM-STR", 1200), ("RM-ST-A75", "RM-STR", 900), ("RM-ST-PIPE50", "RM-STR", 800),
    ("RM-SG-E350-12", "RM-STR", 1000), ("RM-SG-SS304-3", "RM-STR", 250), ("RM-TMT-12", "RM-STR", 2000),
    ("RM-TMT-16", "RM-STR", 1500), ("CN-ELEC-E6013", "CONS", 120), ("CN-MIG-ER70", "CONS", 150),
    ("CN-GRIND-4", "CONS", 200), ("CN-CUT-14", "CONS", 40), ("CN-OXY", "CONS", 12), ("CN-LPG", "CONS", 6),
    ("CN-PRIMER", "CONS", 80), ("CN-ENAMEL", "CONS", 60), ("PPE-HELMET", "CONS", 40), ("PPE-GLOVE-W", "CONS", 60),
    ("PPE-SHOE", "CONS", 25), ("PPE-SHIELD", "CONS", 20), ("TL-GRINDER", "CONS", 6), ("TL-CLAMP", "CONS", 30),
]
price = {i["ItemCode"]: i["PurchasePrice"] for i in items}
ob = {
    "Date": OB_DATE, "OffsetAccount": "1003",
    "Stock": [{"ItemCode": c, "Warehouse": w, "Qty": q, "Price": price[c]} for c, w, q in stock_ob],
    "BP": [  # open balances (customer receivable +, vendor payable -)
        {"CardCode": "C0001", "Amount": 1250000}, {"CardCode": "C0002", "Amount": 860000},
        {"CardCode": "C0003", "Amount": 415000},
        {"CardCode": "V0001", "Amount": -640000}, {"CardCode": "V0002", "Amount": -385000},
        {"CardCode": "V0004", "Amount": -42000}],
    "GL": [  # dummy balances; debit +, credit -
        {"Account": "5001-01-03-01", "Amount": 18500000}, {"Account": "5001-01-03-10", "Amount": -6200000},
        {"Account": "5001-01-02-01", "Amount": 12000000}, {"Account": "5001-01-02-10", "Amount": -2400000},
        {"Account": "5002-02-02-01", "Amount": 2350000}, {"Account": "5002-02-03-01", "Amount": 45000},
        {"Account": "3002-01-02", "Amount": -9500000}, {"Account": "1001-01-01-01", "Amount": -5000000},
        {"Account": "1001-01-01-02", "Amount": -3000000}, {"Account": "1001-01-01-03", "Amount": -2000000}],
}
dump("11_opening_balances", ob)
print("COA accounts placed by file position (verify):", len(coa_review))
