"""U1 master data for AKE_DEMO (fabrication unit 1): UoMs, UoM groups, warehouses U1WH*, item groups, 27 items,
fabrication customers (U1C*) and vendors (U1V*).

Run:  python tools/build_u1_masters.py --excel   (only write data/u1_masters/U1_Master_Data.xlsx)
      python tools/build_u1_masters.py           (write the Excel, then create everything missing in AKE_DEMO)
Every step skips records that already exist, so it can be re-run after fixing an error.
GST rates and SAC/HSN codes below are indicative for training - AKE's tax team should confirm them.
"""
import argparse, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

OUT = L.ROOT / "data" / "u1_masters"
DOC_DATE = "2026-10-02"  # posting date of the FG standard-cost revaluation

# ---------------------------------------------------------------------------------------------- units of measure
UOMS = {"NOS": "Nos", "KG": "KG", "MT": "MT", "BAG": "Bag", "MTR": "Meter", "FT": "Feet", "LTR": "Liter",
        "BOX": "Box", "SET": "Set"}
# group code -> (name, base UoM, [(alternate UoM, alternate qty, base qty)]):  alt qty x alt UoM = base qty x base UoM
UOM_GROUPS = {
    "STEEL":     ("Steel - KG / MT (1 MT = 1000 KG)", "KG", [("MT", 1, 1000)]),
    "CEMENT":    ("Cement - Bag / KG (1 Bag = 50 KG)", "KG", [("BAG", 1, 50)]),
    "AGGREGATE": ("Sand & aggregate - MT / KG", "MT", [("KG", 1000, 1)]),
    "LENGTH":    ("Cable & pipe - Meter / Feet (1 Feet = 0.3048 M)", "MTR", [("FT", 1, 0.3048)]),
    "ELECTRODE": ("Welding electrode - KG / Box (1 Box = 5 KG)", "KG", [("BOX", 1, 5)]),
    "DISC":      ("Abrasive discs - Nos / Box (1 Box = 25 Nos)", "NOS", [("BOX", 1, 25)]),
    "NOS":       ("Numbers", "NOS", []),
    "SET":       ("Set", "SET", []),
    "LITER":     ("Liter", "LTR", []),
}

# ---------------------------------------------------------------------------------------------- warehouses
WAREHOUSES = [  # (code, name, stock account)
    ("U1WH01", "Main Warehouse", "5002-01-01-06"),
    ("U1WH02", "Raw Material Store", "5002-01-01-06"),
    ("U1WH03", "Quality Warehouse", "5002-01-01-06"),
    ("U1WH04", "Rejected Warehouse", "5002-01-01-06"),
    ("U1WH06", "Rejected Warehouse 2 (Scrap)", "5002-01-01-06"),
    ("U1WH07", "Finished Warehouse", "5002-01-01-03"),
]

# ---------------------------------------------------------------------------------------------- item groups
# "Consumables" already exists in AKE_DEMO (group 105) and is reused; the others copy the accounts of the
# matching existing group (Raw material -> RM Plates, Safety Equipment -> PPE, Tools & Consumables -> Tools, FG -> FG).
ITEM_GROUPS = {"Raw material": "RM Plates", "Finished Goods": "FG", "Safety Equipment": "PPE",
               "Tools & Consumables": "Tools", "Consumables": "Consumables"}

HSN_TEXT = {"2505": "Natural sands", "2517": "Aggregate, crushed stone, M-sand", "2523": "Portland cement",
            "3824": "Construction chemicals", "3917": "PVC pipes and fittings", "6307": "Safety harness (textile)",
            "8413": "Pumps for liquids", "8537": "Distribution boards", "8544": "Insulated electric cables",
            "9405": "LED lamps and flood lights"}
SAC_TEXT = {"996511": "Road transport services of goods (GTA)",
            "998873": "Job work - fabricated metal products (verify SAC)"}

# ---------------------------------------------------------------------------------------------- items
# code, description, group, inv, pur, sal, UoM group, inventory/purchase/sales UoM, default whse, valuation,
# HSN/SAC, GST %, cost, purchase price, sales price (prices per inventory UoM), batch, serial
MA, FIFO, STD = "bis_MovingAverage", "bis_FIFO", "bis_Standard"
RM, FG, SF, TL, CN = "Raw material", "Finished Goods", "Safety Equipment", "Tools & Consumables", "Consumables"
ITEMS = [
    ("RM001", "TMT Steel Bar Fe500D 12mm", RM, 1, 1, 1, "STEEL", "KG", "MT", "KG", "U1WH02", MA, "7214", 18, 58, 60, 68, 0, 0),
    ("RM002", "TMT Steel Bar Fe500D 16mm", RM, 1, 1, 1, "STEEL", "KG", "MT", "KG", "U1WH02", MA, "7214", 18, 57, 59, 67, 0, 0),
    ("RM003", "Structural Steel ISMB / ISMC E250", RM, 1, 1, 1, "STEEL", "KG", "MT", "KG", "U1WH02", MA, "7216", 18, 60, 62, 72, 0, 0),
    ("RM004", "Cement OPC 53 Grade 50 KG Bag", RM, 1, 1, 0, "CEMENT", "BAG", "BAG", "BAG", "U1WH02", MA, "2523", 18, 360, 370, None, 0, 0),
    ("RM005", "River Sand", RM, 1, 1, 0, "AGGREGATE", "MT", "MT", "MT", "U1WH02", MA, "2505", 5, 1800, 1850, None, 0, 0),
    ("RM006", "M-Sand (Manufactured Sand)", RM, 1, 1, 0, "AGGREGATE", "MT", "MT", "MT", "U1WH02", MA, "2517", 5, 1100, 1150, None, 0, 0),
    ("RM007", "Aggregate 20mm", RM, 1, 1, 0, "AGGREGATE", "MT", "MT", "MT", "U1WH02", MA, "2517", 5, 950, 1000, None, 0, 0),
    ("EL001", "Electrical Cable 3.5C x 25 sqmm Armoured", RM, 1, 1, 1, "LENGTH", "MTR", "MTR", "MTR", "U1WH02", MA, "8544", 18, 210, 220, 260, 0, 0),
    ("EL002", "Distribution Board 8-Way TPN", RM, 1, 1, 1, "NOS", "NOS", "NOS", "NOS", "U1WH02", MA, "8537", 18, 4200, 4400, 5200, 0, 0),
    ("EL003", "LED Flood Light 100W", RM, 1, 1, 1, "NOS", "NOS", "NOS", "NOS", "U1WH02", MA, "9405", 18, 2300, 2400, 2900, 0, 0),
    ("PL001", "PVC Pipe 110mm 6 kgf", RM, 1, 1, 1, "LENGTH", "MTR", "FT", "MTR", "U1WH02", MA, "3917", 18, 290, 300, 350, 0, 0),
    ("PL002", "GI Pipe 50mm Medium", RM, 1, 1, 1, "LENGTH", "MTR", "MTR", "MTR", "U1WH02", MA, "7306", 18, 520, 540, 620, 0, 0),
    ("SF001", "Safety Helmet", SF, 1, 1, 0, "NOS", "NOS", "NOS", "NOS", "U1WH01", FIFO, "6506", 18, 180, 190, None, 0, 0),
    ("SF002", "Safety Shoes", SF, 1, 1, 0, "NOS", "NOS", "NOS", "NOS", "U1WH01", FIFO, "6403", 5, 950, 990, None, 0, 0),
    ("SF003", "Safety Harness Full Body with Lanyard", SF, 1, 1, 0, "SET", "SET", "SET", "SET", "U1WH01", FIFO, "6307", 5, 2600, 2700, None, 0, 0),
    ("CN001", "Welding Rod E6013 3.15mm", CN, 1, 1, 0, "ELECTRODE", "KG", "BOX", "KG", "U1WH01", FIFO, "8311", 18, 210, 220, None, 0, 0),
    ("CN002", "Cutting Disc 4 inch", CN, 1, 1, 0, "DISC", "NOS", "BOX", "NOS", "U1WH01", FIFO, "6804", 18, 28, 30, None, 0, 0),
    ("CN003", "Grinding Disc 4 inch", CN, 1, 1, 0, "DISC", "NOS", "BOX", "NOS", "U1WH01", FIFO, "6804", 18, 35, 38, None, 0, 0),
    ("TR001", "Water Pump 1 HP Monoblock", TL, 1, 1, 0, "NOS", "NOS", "NOS", "NOS", "U1WH01", MA, "8413", 18, 7800, 8200, None, 0, 0),
    ("TR002", "Power Tool Kit (Angle Grinder + Drill)", TL, 1, 1, 0, "SET", "SET", "SET", "SET", "U1WH01", MA, "8467", 18, 9500, 9900, None, 0, 0),
    ("BAT001", "Construction Chemical / Adhesive - Epoxy Grout", CN, 1, 1, 0, "LITER", "LTR", "LTR", "LTR", "U1WH02", FIFO, "3824", 18, 420, 440, None, 1, 0),
    ("SER001", "Power Drill / Equipment - Rotary Hammer 26mm", TL, 1, 1, 0, "NOS", "NOS", "NOS", "NOS", "U1WH01", MA, "8467", 18, 14500, 15200, None, 0, 1),
    ("SRV001", "Transportation Service (per trip)", None, 0, 1, 1, "NOS", "NOS", "NOS", "NOS", None, None, "996511", 5, None, 6000, 6500, 0, 0),
    ("SRV002", "Subcontracting Service - Fabrication Job Work (per KG)", None, 0, 1, 0, "STEEL", "KG", "KG", "KG", None, None, "998873", 18, None, 18, None, 0, 0),
    ("FG001", "Fabricated Steel Roof Truss", FG, 1, 0, 1, "STEEL", "KG", "KG", "MT", "U1WH07", STD, "7308", 18, 85, None, 110, 0, 0),
    ("FG002", "Fabricated Built-up Steel Column", FG, 1, 0, 1, "STEEL", "KG", "KG", "MT", "U1WH07", STD, "7308", 18, 82, None, 105, 0, 0),
    ("FG003", "MS Base Plate Assembly 300x300x20", FG, 1, 0, 1, "NOS", "NOS", "NOS", "NOS", "U1WH07", STD, "7308", 18, 2400, None, 3100, 0, 0),
]
ITEM_COLS = ["Code", "Description", "Group", "Inv", "Pur", "Sal", "UoMGroup", "InvUoM", "PurUoM", "SalUoM", "Whse",
             "Valuation", "HSN", "GST", "Cost", "PurPrice", "SalPrice", "Batch", "Serial"]
ITEMS = [dict(zip(ITEM_COLS, r)) for r in ITEMS]

# ---------------------------------------------------------------------------------------------- business partners
# code, name, state, city, PAN, payment days, TDS code, what they buy / supply
CUSTOMERS = [
    ("U1C001", "Hampi Infra Developers Pvt Ltd", "Karnataka", "Bengaluru", "AAHCH5521K", 45, None, "Industrial sheds - roof trusses, columns"),
    ("U1C002", "Kaveri Industrial Parks Ltd", "Karnataka", "Mysuru", "AABCK7734M", 30, None, "Factory buildings - structural steel"),
    ("U1C003", "Godavari Power Plant Constructions Pvt Ltd", "Telangana", "Hyderabad", "AAGCG4410P", 60, None, "Pipe racks, platforms, base plates"),
    ("U1C004", "Palar Warehousing & Logistics LLP", "Tamil Nadu", "Chennai", "AAPFP2287D", 45, None, "PEB warehouses - trusses & columns"),
    ("U1C005", "Deccan Highway Bridges Ltd", "Maharashtra", "Pune", "AADCD9063R", 60, None, "Bridge girders, TMT & site electricals"),
]
VENDORS = [
    ("U1V001", "Tungabhadra Steel Distributors", "Karnataka", "Ballari", "AAKFT3318L", 30, None, "TMT bars, structural steel (194Q pending)"),
    ("U1V002", "Chamundi Cement & Aggregates", "Karnataka", "Mysuru", "AAJFC6620B", 15, None, "Cement, river sand, M-sand, aggregate"),
    ("U1V003", "Vidyut Electricals & Lighting", "Karnataka", "Bengaluru", "AAQFV1145H", 30, None, "Cables, distribution boards, flood lights"),
    ("U1V004", "Jalavahini Pipes & Fittings", "Tamil Nadu", "Coimbatore", "AAEFJ8872N", 30, None, "PVC and GI pipes"),
    ("U1V005", "Rakshak Safety Equipments", "Maharashtra", "Mumbai", "AAMFR4409G", 30, None, "Helmets, safety shoes, harness"),
    ("U1V006", "Agni Welding & Abrasives", "Karnataka", "Bengaluru", "AABFA5536E", 15, None, "Welding rods, cutting & grinding discs"),
    ("U1V007", "Shakti Tools & Construction Chemicals", "Karnataka", "Hubballi", "AAKFS2291C", 30, None, "Pumps, power tools, drills, epoxy grout"),
    ("U1V008", "Sarathi Roadlines", "Karnataka", "Bengaluru", "AAGFS7740Q", 15, "C2", "Transport (GTA) - TDS 194C 2%"),
    ("U1V009", "Ramesh Fabrication Job Works", "Karnataka", "Doddaballapur", "BQRPR6153A", 30, "C1", "Fabrication subcontracting - TDS 194C 1%"),
]
GST_STATE = {"Karnataka": "29", "Telangana": "36", "Tamil Nadu": "33", "Maharashtra": "27"}


def gstin(state, pan):
    """15-char GSTIN with a valid check digit."""
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    body = GST_STATE[state] + pan + "1Z"
    total = sum(v // 36 + v % 36 for v in (chars.index(c) * (2 if i % 2 else 1) for i, c in enumerate(body)))
    return body + chars[(36 - total % 36) % 36]


def bps():
    for kind, rows, acct in (("cCustomer", CUSTOMERS, "5002-02-04-01"), ("cSupplier", VENDORS, "3002-02-01")):
        for code, name, state, city, pan, days, wt, note in rows:
            yield {"CardCode": code, "CardName": name, "CardType": kind, "State": state, "City": city, "PAN": pan,
                   "GSTIN": gstin(state, pan), "PaymentTermsDays": days, "WTCode": wt, "ControlAccount": acct, "Note": note}


# ---------------------------------------------------------------------------------------------- Excel
def write_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    yn = lambda v: "Y" if v else "N"
    val = {MA: "Moving Average", FIFO: "FIFO", STD: "Standard", None: "-"}
    sheets = {
        "Warehouses": (["Code", "Name", "Stock account"], WAREHOUSES),
        "UoM": (["Code", "Name"], list(UOMS.items())),
        "UoM Groups": (["Group", "Name", "Base UoM", "Conversion"],
                       [(g, n, UOMS[b], "; ".join(f"{a} {UOMS[u]} = {q} {UOMS[b]}" for u, a, q in alt) or "-")
                        for g, (n, b, alt) in UOM_GROUPS.items()]),
        "Item Groups": (["Item group", "Accounts copied from"], list(ITEM_GROUPS.items())),
        "Items": (["Item Code", "Description", "Item Group", "Inventory Item", "Purchase Item", "Sales Item", "UoM Group",
                   "UOM", "Purchase UOM", "Sales UOM", "Default Warehouse", "Valuation Method", "HSN / SAC",
                   "Tax Category", "GST % (indicative)", "Cost", "Purchase Price", "Sales Price", "Batch Managed",
                   "Serial Managed"],
                  [(i["Code"], i["Description"], i["Group"] or "Items (services)", yn(i["Inv"]), yn(i["Pur"]), yn(i["Sal"]),
                    i["UoMGroup"], UOMS[i["InvUoM"]], UOMS[i["PurUoM"]], UOMS[i["SalUoM"]], i["Whse"] or "-",
                    val[i["Valuation"]], i["HSN"], "Regular (Service)" if not i["Inv"] else "Regular (Goods)", i["GST"],
                    i["Cost"], i["PurPrice"], i["SalPrice"], yn(i["Batch"]), yn(i["Serial"])) for i in ITEMS]),
        "Customers": (["Code", "Name", "State", "City", "PAN", "GSTIN", "Payment terms (days)", "Buys"],
                      [(b["CardCode"], b["CardName"], b["State"], b["City"], b["PAN"], b["GSTIN"], b["PaymentTermsDays"], b["Note"])
                       for b in bps() if b["CardType"] == "cCustomer"]),
        "Vendors": (["Code", "Name", "State", "City", "PAN", "GSTIN", "Payment terms (days)", "TDS code", "Supplies"],
                    [(b["CardCode"], b["CardName"], b["State"], b["City"], b["PAN"], b["GSTIN"], b["PaymentTermsDays"],
                      b["WTCode"] or "-", b["Note"]) for b in bps() if b["CardType"] == "cSupplier"]),
    }
    wb = Workbook()
    wb.remove(wb.active)
    for title, (head, rows) in sheets.items():
        ws = wb.create_sheet(title)
        ws.append(head)
        for c in ws[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F4E78")
        for r in rows:
            ws.append(list(r))
        for n, col in enumerate(ws.columns, 1):
            ws.column_dimensions[get_column_letter(n)].width = min(48, max(len(str(c.value or "")) for c in col) + 2)
        ws.freeze_panes = "A2"
    OUT.mkdir(parents=True, exist_ok=True)
    wb.save(OUT / "U1_Master_Data.xlsx")
    print(f"Wrote {OUT / 'U1_Master_Data.xlsx'}")


# ---------------------------------------------------------------------------------------------- SAP
def load_sap(sl):
    v = lambda p: (sl.get(p) or {}).get("value", [])
    uom = {u["Code"]: u["AbsEntry"] for u in v("UnitOfMeasurements?$select=AbsEntry,Code")}
    for code, name in UOMS.items():
        if code not in uom:
            res = sl.post("UnitOfMeasurements", {"Code": code, "Name": name}, f"UoM {code}")
            if res:
                uom[code] = res["AbsEntry"]
    ugp = {g["Code"]: g["AbsEntry"] for g in v("UnitOfMeasurementGroups?$select=AbsEntry,Code")}
    for code, (name, base, alt) in UOM_GROUPS.items():
        if code not in ugp:
            res = sl.post("UnitOfMeasurementGroups", {
                "Code": code, "Name": name, "BaseUoM": uom[base],
                "UoMGroupDefinitionCollection": [{"AlternateUoM": uom[u], "AlternateQuantity": a, "BaseQuantity": q}
                                                 for u, a, q in alt]}, f"UoM group {code}")
            if res:
                ugp[code] = res["AbsEntry"]

    for code, name, stock in WAREHOUSES:
        if not sl.exists("Warehouses", code):
            sl.post("Warehouses", {"WarehouseCode": code, "WarehouseName": name, "Location": L.TDS_LOCATION,
                                   "StockAccount": stock, "ExpenseAccount": "4001-16", "RevenuesAccount": "2001-01-01-01",
                                   "PurchaseAccount": "4008-01", "PriceDifferencesAccount": "4001-17",
                                   "VarianceAccount": "4001-23", "DecreasingAccount": "4001-21",
                                   "IncreaseGLAccount": "4001-20", "DecreaseGLAccount": "4001-21",
                                   "WIPMaterialAccount": "5002-01-02", "WIPMaterialVarianceAccount": "4001-23"}, code)

    src = {g["GroupName"]: g for g in L.load("03_item_groups")}
    ren = {"WipAccount": "WIPMaterialAccount", "WipVarianceAccount": "WIPMaterialVarianceAccount"}
    for name, copy in ITEM_GROUPS.items():
        if not sl.find("ItemGroups", "GroupName", name):
            g = src[copy]
            sl.post("ItemGroups", {"GroupName": name, "InventorySystem": g["InventorySystem"],
                                   **{ren.get(k, k): a for k, a in g["Accounts"].items()}}, f"Item group {name}")
    groups = {g["GroupName"]: g["Number"] for g in v("ItemGroups?$select=Number,GroupName")}

    hsn = {h["ChapterID"].replace(".", ""): h["AbsEntry"] for h in v("IndiaHsn?$select=AbsEntry,ChapterID")}
    sac = {s["ServiceCode"]: s["AbsEntry"] for s in v("IndiaSacCode?$select=AbsEntry,ServiceCode")}
    for i in ITEMS:
        c = i["HSN"]
        if i["Inv"] and c not in hsn:
            res = sl.post("IndiaHsn", {"Chapter": c[:2], "Heading": c[2:4], "SubHeading": "",
                                       "Description": HSN_TEXT[c]}, f"HSN {c}")
            if res:
                hsn[c] = res["AbsEntry"]
        if not i["Inv"] and c not in sac:
            res = sl.post("IndiaSacCode", {"ServiceCode": c, "ServiceName": SAC_TEXT[c]}, f"SAC {c}")
            if res:
                sac[c] = res["AbsEntry"]

    pur, sal = L.price_list_no(sl, "PUR"), L.price_list_no(sl, "SAL")
    whs = [w[0] for w in WAREHOUSES]
    mat = {RM: "mt_RawMaterial", FG: "mt_FinishedGoods"}
    yes = lambda f: "tYES" if f else "tNO"
    new_std = []
    for i in ITEMS:
        if sl.exists("Items", i["Code"]):
            continue
        body = {"ItemCode": i["Code"], "ItemName": i["Description"],
                "ItemsGroupCode": groups[i["Group"]] if i["Group"] else 100,
                "InventoryItem": yes(i["Inv"]), "PurchaseItem": yes(i["Pur"]), "SalesItem": yes(i["Sal"]),
                "UoMGroupEntry": ugp[i["UoMGroup"]], "InventoryUoMEntry": uom[i["InvUoM"]],
                "DefaultPurchasingUoMEntry": uom[i["PurUoM"]], "DefaultSalesUoMEntry": uom[i["SalUoM"]],
                "GSTRelevnt": "tYES", "GSTTaxCategory": "gtc_Regular",
                "ItemPrices": [{"PriceList": pl, "Price": p} for pl, p in ((pur, i["PurPrice"]), (sal, i["SalPrice"])) if p]}
        if i["Inv"]:
            body.update({"ItemClass": "itcMaterial", "ChapterID": hsn.get(i["HSN"]), "GLMethod": "glm_ItemClass",
                         "CostAccountingMethod": i["Valuation"], "DefaultWarehouse": i["Whse"],
                         "ManageStockByWarehouse": "tYES", "MaterialType": mat.get(i["Group"], "mt_RawMaterial"),
                         "ProcurementMethod": "bom_Make" if i["Group"] == FG else "bom_Buy",
                         "ItemWarehouseInfoCollection": [{"WarehouseCode": w} for w in whs]})
            if i["Batch"] or i["Serial"]:
                body.update({"ManageBatchNumbers": yes(i["Batch"]), "ManageSerialNumbers": yes(i["Serial"]),
                             "SRIAndBatchManageMethod": "bomm_OnEveryTransaction"})
        else:
            # B1 India SL ignores ItemClass/SACEntry on items: set Item Class = Service + SAC in the client,
            # or give SACEntry on the document line (as demo_transactions.py does)
            body.update({"ItemClass": "itcService", "SACEntry": sac.get(i["HSN"])})
        if sl.post("Items", body, f"{i['Code']} {i['Description'][:40]}") and i["Valuation"] == STD:
            new_std.append(i)
    # B1 refuses AvgStdPrice on the item master; standard cost is set per warehouse by an inventory revaluation
    if new_std:
        sl.post("MaterialRevaluation", {"DocDate": DOC_DATE, "RevalType": "P", "Comments": "U1 FG standard cost",
                                        "MaterialRevaluationLines": [{"ItemCode": i["Code"], "Price": i["Cost"], "WarehouseCode": w}
                                                                     for i in new_std for w in whs]},
                "Standard cost " + ", ".join(i["Code"] for i in new_std))

    terms = {t["PaymentTermsGroupName"]: t["GroupNumber"] for t in v("PaymentTermsTypes?$select=GroupNumber,PaymentTermsGroupName")}
    for b in bps():
        if sl.exists("BusinessPartners", b["CardCode"]):
            continue
        st = L.state_code(sl, b["State"])
        addr = lambda t, n: {"AddressName": n, "AddressType": t, "City": b["City"], "Country": "IN",
                             "State": st, "GSTIN": b["GSTIN"], "GstType": "gstRegularTDSISD"}
        body = {"CardCode": b["CardCode"], "CardName": b["CardName"], "CardType": b["CardType"], "Currency": "INR",
                "DebitorAccount": b["ControlAccount"], "PayTermsGrpCode": terms.get(f"Net {b['PaymentTermsDays']} Days"),
                "Notes": b["Note"], "BPAddresses": [addr("bo_BillTo", "Bill To"), addr("bo_ShipTo", "Ship To")],
                "BPFiscalTaxIDCollection": [{"Address": "", "TaxId0": b["PAN"]}]}
        if b["WTCode"]:
            body.update({"TypeReport": "atOthers" if b["PAN"][3] in "PH" else "atCompany",
                         "SubjectToWithholdingTax": "boYES", "BPWithholdingTaxCollection": [{"WTCode": b["WTCode"]}]})
        sl.post("BusinessPartners", body, f"{b['CardCode']} {b['CardName']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", action="store_true", help="only write the Excel master data sheet")
    a = ap.parse_args()
    write_excel()
    if a.excel:
        return
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    load_sap(sl)
    print(f"Done. Failures: {sl.failures}")


if __name__ == "__main__":
    main()
