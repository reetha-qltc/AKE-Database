"""U1 master data for AKE_DEMO (fabrication unit 1): UoMs, UoM groups, warehouses U1WH*, item groups, 27 items,
fabrication customers (C0007-C0012, created as U1C001-U1C006) and vendors (V0010-V0018, created as U1V001-U1V009).

Run:  python tools/build_u1_masters.py --excel   (only write data/u1_masters/U1_Master_Data.xlsx)
      python tools/build_u1_masters.py           (write the Excel, then create everything missing in AKE_DEMO)
Every step skips records that already exist, so it can be re-run after fixing an error.
GST rates and SAC/HSN codes below are indicative for training - AKE's tax team should confirm them.
"""
import argparse, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L
from renumber_bps import RENAME

RENAMED_FROM = {new: old for old, new in RENAME.items()}  # BPs created as U1C*/U1V* and renumbered on 2026-10-03

OUT = L.ROOT / "data" / "u1_masters"
DOC_DATE = "2026-10-03"  # posting date of the standard-cost revaluation of new Standard items

# ---------------------------------------------------------------------------------------------- units of measure
UOMS = {"NOS": "NOS", "PAIR": "Pairs", "PKT": "Packet", "SET": "Set",
        "SQM": "Square Meters", "SQFT": "Square Feet",
        "CM": "Centimeters", "INCH": "Inches", "MTR": "Meters", "FT": "Feet",
        "LTR": "LTR", "M3": "Cubic Meters (m3)",  # one UoM for cubic meter / m3
        "G": "Grams", "KG": "KGS", "MT": "Tonnes",
        "BAG": "Bag", "BOX": "Box"}
# group code -> (name, base UoM, [(alternate UoM, alternate qty, base qty)]):  alt qty x alt UoM = base qty x base UoM
# Standard groups Each / Area / Length / Volume / Weight (+ B1's built-in Manual); the three pack-size groups below
# them hold item-specific conversions (a bag of cement, a box of electrodes / discs) that cannot be general.
UOM_GROUPS = {
    "EACH":      ("Each", "NOS", [("PAIR", 1, 2), ("PKT", 1, 100), ("SET", 1, 1)]),
    "AREA":      ("Area", "SQM", [("SQFT", 10.7639, 1)]),
    "LENGTH":    ("Length", "MTR", [("CM", 100, 1), ("INCH", 1, 0.0254), ("FT", 1, 0.3048)]),
    "VOLUME":    ("Volume", "LTR", [("M3", 1, 1000)]),
    "WEIGHT":    ("Weight", "KG", [("G", 1000, 1), ("MT", 1, 1000)]),
    "CEMENT":    ("Cement - Bag / KG (1 Bag = 50 KG)", "KG", [("BAG", 1, 50)]),
    "ELECTRODE": ("Welding electrode - KG / Box (1 Box = 5 KG)", "KG", [("BOX", 1, 5)]),
    "DISC":      ("Abrasive discs - Nos / Box (1 Box = 25 Nos)", "NOS", [("BOX", 1, 25)]),
}
UOM_GROUP_RENAMED = {"STEEL": "WEIGHT", "NOS": "EACH", "LITER": "VOLUME"}  # 2026-10-03: old code -> new code

# ---------------------------------------------------------------------------------------------- warehouses
# U1WH02 / U1WH03 / U1WH06 / U1WH07 duplicated U1 WH1 / WH9 / WH7 / WH5 and were set inactive on 2026-10-03
WAREHOUSES = [  # (code, name, stock account)
    ("U1WH01", "Main Warehouse", "5002-01-01-06"),
    ("U1WH04", "Rejected Warehouse", "5002-01-01-06"),
    # 2026-10-03 Unit-1 warehouse list from AKE (codes exactly as given, with a space)
    ("U1 WH1", "Unit-1 Raw Material Warehouse", "5002-01-01-06"),
    ("U1 WH2", "Unit-1 Bin Storage Warehouse", "5002-01-01-06"),
    ("U1 WH3", "Unit-1 Subcontractor Warehouse", "5002-01-01-06"),
    ("U1 WH4", "Unit-1 Work In Progress Warehouse", "5002-01-01-06"),
    ("U1 WH5", "Unit-1 Finished Goods Warehouse", "5002-01-01-03"),
    ("U1 WH6", "Unit-1 Rework Warehouse", "5002-01-01-06"),
    ("U1 WH7", "Unit-1 Scrap Warehouse", "5002-01-01-06"),
    ("U1 WH8", "Unit-1 Cutting Warehouse", "5002-01-01-06"),
    ("U1 WH9", "Unit-1 Quality Warehouse", "5002-01-01-06"),
]

# ---------------------------------------------------------------------------------------------- item groups
# "Consumables" already exists in AKE_DEMO (group 105) and is reused; the others copy the accounts of the
# matching existing group (Raw material -> RM Plates, Safety Equipment -> PPE, Tools & Consumables -> Tools, FG -> FG).
ITEM_GROUPS = {"Raw material": "RM Plates", "Finished Goods": "FG", "Safety Equipment": "PPE",
               "Tools & Consumables": "Tools", "Consumables": "Consumables", "Sub Assembly": "Sub Assembly",
               "Packing Material": "Consumables", "Bought-out Components": "RM Plates", "Scrap": "RM Plates"}

HSN_TEXT = {"2505": "Natural sands", "2517": "Aggregate, crushed stone, M-sand", "2523": "Portland cement",
            "3824": "Construction chemicals", "3917": "PVC pipes and fittings", "6307": "Safety harness (textile)",
            "8413": "Pumps for liquids", "8537": "Distribution boards", "8544": "Insulated electric cables",
            "9405": "LED lamps and flood lights"}
HSN_TEXT.update({"2710": "Petroleum oils - diesel, lubricants", "3402": "Cleaning and degreasing preparations",
                 "3920": "Plastic film - stretch wrap", "3926": "Other plastic articles - cable ties, tarpaulin",
                 "4415": "Wooden pallets and packing cases", "6116": "Knitted gloves", "6806": "Rock wool insulation",
                 "7210": "Coated flat-rolled steel - roofing sheet", "7306": "Steel tubes and hollow sections",
                 "7308": "Steel structures", "7318": "Bolts, nuts, washers", "8311": "Welding and brazing rods",
                 "8482": "Ball bearings", "7208": "Hot-rolled flat steel - HR plate", "7204": "Ferrous scrap"})
SAC_TEXT = {"996511": "Road transport services of goods (GTA)",
            "998873": "Job work - fabricated metal products (verify SAC)"}

# ---------------------------------------------------------------------------------------------- items
# code, description, group, inv, pur, sal, UoM group, inventory/purchase/sales UoM, default whse, valuation,
# HSN/SAC, GST %, cost, purchase price, sales price (prices per pricing unit, see PRICING_UNIT), batch, serial.
# All items without transactions are on Each / NOS (user decision 2026-10-03); RM001 / SF001 have transactions.
# Valuation: bought items Moving Average, items made in production (sub-assemblies, finished goods) Standard.
MA, FIFO, STD = "bis_MovingAverage", "bis_FIFO", "bis_Standard"
RM, FG, SF, TL, CN = "Raw material", "Finished Goods", "Safety Equipment", "Tools & Consumables", "Consumables"
SA, PK, BO, SC = "Sub Assembly", "Packing Material", "Bought-out Components", "Scrap"
ITEMS = [
    ("RM001", "TMT Steel Bar Fe500D 12mm", RM, 1, 1, 1, "WEIGHT", "KG", "MT", "KG", "U1 WH1", MA, "7214", 18, 58, 60, 68, 0, 0),
    ("RM002", "TMT Steel Bar Fe500D 16mm", RM, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "7214", 18, 57, 59, 67, 0, 0),
    ("RM003", "Structural Steel ISMB / ISMC E250", RM, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "7216", 18, 60, 62, 72, 0, 0),
    ("RM004", "Cement OPC 53 Grade 50 KG Bag", RM, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "2523", 18, 360, 370, None, 0, 0),
    ("RM005", "River Sand", RM, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "2505", 5, 1800, 1850, None, 0, 0),
    ("RM006", "M-Sand (Manufactured Sand)", RM, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "2517", 5, 1100, 1150, None, 0, 0),
    ("RM007", "Aggregate 20mm", RM, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "2517", 5, 950, 1000, None, 0, 0),
    ("EL001", "Electrical Cable 3.5C x 25 sqmm Armoured", RM, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "8544", 18, 210, 220, 260, 0, 0),
    ("EL002", "Distribution Board 8-Way TPN", RM, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "8537", 18, 4200, 4400, 5200, 0, 0),
    ("EL003", "LED Flood Light 100W", RM, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "9405", 18, 2300, 2400, 2900, 0, 0),
    ("PL001", "PVC Pipe 110mm 6 kgf", RM, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "3917", 18, 290, 300, 350, 0, 0),
    ("PL002", "GI Pipe 50mm Medium", RM, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "7306", 18, 520, 540, 620, 0, 0),
    ("SF001", "Safety Helmet", SF, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "6506", 18, 180, 190, 250, 0, 0),
    ("SF002", "Safety Shoes", SF, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "6403", 5, 950, 990, None, 0, 0),
    ("SF003", "Safety Harness Full Body with Lanyard", SF, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "6307", 5, 2600, 2700, None, 0, 0),
    ("CN001", "Welding Rod E6013 3.15mm", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "8311", 18, 210, 220, None, 0, 0),
    ("CN002", "Cutting Disc 4 inch", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "6804", 18, 28, 30, None, 0, 0),
    ("CN003", "Grinding Disc 4 inch", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "6804", 18, 35, 38, None, 0, 0),
    ("TR001", "Water Pump 1 HP Monoblock", TL, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "8413", 18, 7800, 8200, None, 0, 0),
    ("TR002", "Power Tool Kit (Angle Grinder + Drill)", TL, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "8467", 18, 9500, 9900, None, 0, 0),
    ("BAT001", "Construction Chemical / Adhesive - Epoxy Grout", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "3824", 18, 420, 440, None, 1, 0),
    ("SER001", "Power Drill / Equipment - Rotary Hammer 26mm", TL, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "8467", 18, 14500, 15200, None, 0, 1),
    ("SRV001", "Transportation Service (per trip)", None, 0, 1, 1, "EACH", "NOS", "NOS", "NOS", None, None, "996511", 5, None, 6000, 6500, 0, 0),
    ("SRV002", "Subcontracting Service - Fabrication Job Work (per KG)", None, 0, 1, 0, "EACH", "NOS", "NOS", "NOS", None, None, "998873", 18, None, 18, None, 0, 0),
    ("FG001", "Fabricated Steel Roof Truss", FG, 1, 0, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH5", STD, "7308", 18, 85, None, 110, 0, 0),
    ("FG002", "Fabricated Built-up Steel Column", FG, 1, 0, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH5", STD, "7308", 18, 82, None, 105, 0, 0),
    ("FG003", "MS Base Plate Assembly 300x300x20", FG, 1, 0, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH5", STD, "7308", 18, 2400, None, 3100, 0, 0),
    # 2026-10-03 sample items for the Purchase -> Inventory -> Production -> Sales demo, one or more per UoM group
    ("RM008", "Colour Coated Roofing Sheet 0.47mm AZ150", RM, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "7210", 18, None, 48, 58, 0, 0),
    ("RM009", "Rockwool Insulation Blanket 50mm 64 kg/m3", RM, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "6806", 18, None, 310, None, 0, 0),
    ("RM010", "MS Square Hollow Section 40x40x2mm", RM, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "7306", 18, None, 145, None, 0, 0),
    ("RM011", "Ready Mix Concrete M25", RM, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "3824", 18, None, 5600, None, 0, 0),
    ("CN004", "HDPE Tarpaulin Sheet 200 GSM", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "3926", 18, None, 95, None, 0, 0),
    ("CN005", "Industrial Degreaser / Cleaning Chemical", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "3402", 18, None, 180, None, 0, 0),
    ("CN006", "Silver Brazing Alloy Rod 15%", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "8311", 18, None, 38, None, 0, 0),
    ("CN007", "Cotton Knitted Hand Gloves", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "6116", 5, None, 28, None, 0, 0),
    ("CN008", "Hydraulic Oil ISO VG 68", CN, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "2710", 18, None, 165, None, 0, 0),
    ("BO001", "Deep Groove Ball Bearing 6205-2RS", BO, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "8482", 18, None, 185, 240, 0, 0),
    ("BO002", "HDG Hex Bolt M16x60 with Nut & Washer", BO, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "7318", 18, None, 22, 30, 0, 0),
    ("BO003", "Anchor Bolt Set M20 (4 bolts + template)", BO, 1, 1, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH1", MA, "7318", 18, None, 1450, 1800, 0, 0),
    ("PM001", "Nylon Cable Tie 300mm (packet of 100)", PK, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "3926", 18, None, 1.6, None, 0, 0),
    ("PM002", "Wooden Pallet 1200x1000mm", PK, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "4415", 12, None, 650, None, 0, 0),
    ("PM003", "Stretch Wrap Film 500mm", PK, 1, 1, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", MA, "3920", 18, None, 210, None, 0, 0),
    ("SA001", "Welded Bearing Bracket (semi-finished)", SA, 1, 0, 0, "EACH", "NOS", "NOS", "NOS", "U1WH01", STD, "7308", 18, 750, None, None, 0, 0),
    ("FG004", "Conveyor Idler Support Frame", FG, 1, 0, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH5", STD, "7308", 18, 2600, None, 3400, 0, 0),
    # 2026-10-03 AKE BOM pattern: plate cut on CNC plasma, scrap returned as by-product, resources backflushed
    ("Z24631250005", "HR Plate, IS:2062 Gr. BR / S355JR, Size: 1250 x 5 mm", RM, 1, 1, 0, "WEIGHT", "KG", "KG", "KG", "U1 WH1", MA, "7208", 18, None, 62, None, 0, 0),
    ("SCR220001", "MS Scrap melting", SC, 1, 0, 1, "WEIGHT", "KG", "KG", "KG", "U1 WH7", MA, "7204", 18, None, None, 32, 0, 0),
    ("PL01", "Anchor Bolt Plate", FG, 1, 0, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH5", STD, "7308", 18, 43, None, 60, 0, 0),
    ("FG005", "Insulated Roof Panel Assembly", FG, 1, 0, 1, "EACH", "NOS", "NOS", "NOS", "U1 WH5", STD, "7308", 18, 1250, None, 1650, 0, 0),
]
ITEM_COLS = ["Code", "Description", "Group", "Inv", "Pur", "Sal", "UoMGroup", "InvUoM", "PurUoM", "SalUoM", "Whse",
             "Valuation", "HSN", "GST", "Cost", "PurPrice", "SalPrice", "Batch", "Serial"]
ITEMS = [dict(zip(ITEM_COLS, r)) for r in ITEMS]
# pricing unit (price list prices are per this unit) when it is not the inventory UoM
PRICING_UNIT = {}
for i in ITEMS:
    i["PriceUoM"] = PRICING_UNIT.get(i["Code"], i["InvUoM"])
# resources (time unit minutes): code, name, type, cost per minute (existing hourly rates / 60), warehouse
RESOURCES = [
    ("RESPCM2-U1", "CNC Plasma With Dual Torch", "rtMachine", 20, "U1 WH4"),
    ("RESPCO-U1", "Plasma Cutting Operator", "rtLabor", 6, "U1 WH4"),
    ("RESHRO-U1", "Helper", "rtLabor", 4, "U1 WH4"),
    ("RESGGM-U1", "Grinding Machine", "rtMachine", 5, "U1 WH4"),
]
# production BOMs of the made items: code -> (warehouse, [(component, qty per 1 inventory unit, warehouse
#                                               [, "I"tem / "R"esource, "M"anual / "B"ackflush])]) - rows in this order;
# a negative quantity is a by-product (scrap) received back into stock
BOMS = {
    "SA001": ("U1WH01", [("RM003", 6.5, "U1 WH1"), ("RM010", 1.2, "U1 WH1"), ("CN001", 0.3, "U1WH01")]),
    "FG004": ("U1 WH5", [("SA001", 2, "U1WH01"), ("BO001", 2, "U1 WH1"), ("BO002", 8, "U1 WH1"),
                         ("CN005", 0.2, "U1WH01"), ("PM001", 4, "U1WH01"), ("PM003", 0.25, "U1WH01")]),
    "FG005": ("U1 WH5", [("RM008", 1.05, "U1 WH1"), ("RM009", 1.05, "U1 WH1"), ("RM010", 0.8, "U1 WH1"),
                         ("BO002", 4, "U1 WH1")]),  # per 1 SQM of panel
    "PL01": ("U1 WH5", [("Z24631250005", 0.27, "U1 WH8", "I", "M"), ("SCR220001", -0.05, "U1 WH7", "I", "B"),
                        ("RESPCM2-U1", 0.5, "U1 WH4", "R", "B"), ("RESPCO-U1", 0.5, "U1 WH4", "R", "B"),
                        ("RESHRO-U1", 1.5, "U1 WH4", "R", "B"), ("RESGGM-U1", 1.0, "U1 WH4", "R", "B"),
                        ("RESHRO-U1", 1.0, "U1 WH4", "R", "B")]),
}

# ---------------------------------------------------------------------------------------------- business partners
# code, name, state, city, PAN, payment days, TDS code, what they buy / supply
CUSTOMERS = [
    ("C0007", "Hampi Infra Developers Pvt Ltd", "Karnataka", "Bengaluru", "AAHCH5521K", 45, None, "Industrial sheds - roof trusses, columns"),
    ("C0008", "Kaveri Industrial Parks Ltd", "Karnataka", "Mysuru", "AABCK7734M", 30, None, "Factory buildings - structural steel"),
    ("C0009", "Godavari Power Plant Constructions Pvt Ltd", "Telangana", "Hyderabad", "AAGCG4410P", 60, None, "Pipe racks, platforms, base plates"),
    ("C0010", "Palar Warehousing & Logistics LLP", "Tamil Nadu", "Chennai", "AAPFP2287D", 45, None, "PEB warehouses - trusses & columns"),
    ("C0011", "Deccan Highway Bridges Ltd", "Maharashtra", "Pune", "AADCD9063R", 60, None, "Bridge girders, TMT & site electricals"),
    ("C0012", "ABC Developers Pvt Ltd", "Karnataka", "Bengaluru", "AABCA7781K", 30, None, "Residential towers - TMT bars, safety items (O2C demo)"),
]
VENDORS = [
    ("V0010", "Tungabhadra Steel Distributors", "Karnataka", "Ballari", "AAKFT3318L", 30, None, "TMT bars, structural steel (194Q pending)"),
    ("V0011", "Chamundi Cement & Aggregates", "Karnataka", "Mysuru", "AAJFC6620B", 15, None, "Cement, river sand, M-sand, aggregate"),
    ("V0012", "Vidyut Electricals & Lighting", "Karnataka", "Bengaluru", "AAQFV1145H", 30, None, "Cables, distribution boards, flood lights"),
    ("V0013", "Jalavahini Pipes & Fittings", "Tamil Nadu", "Coimbatore", "AAEFJ8872N", 30, None, "PVC and GI pipes"),
    ("V0014", "Rakshak Safety Equipments", "Maharashtra", "Mumbai", "AAMFR4409G", 30, None, "Helmets, safety shoes, harness"),
    ("V0015", "Agni Welding & Abrasives", "Karnataka", "Bengaluru", "AABFA5536E", 15, None, "Welding rods, cutting & grinding discs"),
    ("V0016", "Shakti Tools & Construction Chemicals", "Karnataka", "Hubballi", "AAKFS2291C", 30, None, "Pumps, power tools, drills, epoxy grout"),
    ("V0017", "Sarathi Roadlines", "Karnataka", "Bengaluru", "AAGFS7740Q", 15, "C2", "Transport (GTA) - TDS 194C 2%"),
    ("V0018", "Ramesh Fabrication Job Works", "Karnataka", "Doddaballapur", "BQRPR6153A", 30, "C1", "Fabrication subcontracting - TDS 194C 1%"),
]
# BP groups by GST place of supply (company state Karnataka); B1 group names are unique across customers and vendors
HOME_STATE = "Karnataka"
CUSTOMER_GROUPS = {"Intrastate": "Intrastate", "Interstate": "Interstate", "Export": "Export"}
VENDOR_GROUPS = {"Intrastate": "Intrastate Vendor", "Interstate": "Interstate Vendor", "Export": "Import Vendor"}
# code -> segment (informational only - the BP group follows the state), contact (first, last, position), mobile, mail domain,
#         bill-to / pay-to (building, street, area, city, PIN), ship-to (site, building, street, area, city, PIN)
# Training data only: mobiles are a dummy 90000 1xxxx series, e-mails use the reserved .example domain.
DETAILS = {
    "C0007": ("EPC & Infra", ("Suresh", "Kumar", "Purchase Manager"), "+91 90000 10001", "hampiinfra",
               ("No. 45, 2nd Floor, Prestige Arcade", "Bannerghatta Road", "JP Nagar", "Bengaluru", "560076"),
               ("Site - Dabaspet Industrial Shed", "Plot 12", "KIADB Industrial Area", "Dabaspet", "Dabaspet", "562111")),
    "C0008": ("Industrial Developer", ("Lakshmi", "Narayan", "Projects Head"), "+91 90000 10002", "kaveriparks",
               ("Kaveri House, 3rd Floor", "Hunsur Road", "Hebbal Industrial Area", "Mysuru", "570016"),
               ("Site - Kaveri Park Phase 2", "Survey No. 88", "Nanjangud Industrial Area", "Nanjangud", "Nanjangud", "571301")),
    "C0009": ("Power & Process", ("Venkat", "Reddy", "Procurement Manager"), "+91 90000 10003", "godavaripower",
               ("8-2-293, Godavari Towers", "Road No. 14", "Banjara Hills", "Hyderabad", "500034"),
               ("Site - 2x150 MW Power Plant", "Sy. No. 210", "Pashamylaram Industrial Area", "Patancheru", "Sangareddy", "502307")),
    "C0010": ("Industrial Developer", ("Karthik", "Subramanian", "Purchase Manager"), "+91 90000 10004", "palarlogistics",
               ("No. 18, Palar Plaza", "Anna Salai", "Teynampet", "Chennai", "600018"),
               ("Site - Palar Logistics Park", "Plot B-7", "SIPCOT Industrial Park", "Oragadam", "Kancheepuram", "602105")),
    "C0011": ("EPC & Infra", ("Amit", "Deshpande", "Project Manager"), "+91 90000 10005", "deccanbridges",
               ("Deccan House, 5th Floor", "Senapati Bapat Road", "Shivajinagar", "Pune", "411016"),
               ("Site - Bhima River Bridge", "NH-65, Km 42", "Bhigwan Road", "Indapur", "Indapur", "413106")),
    "C0012": ("EPC & Infra", ("Naveen", "Shetty", "Purchase Manager"), "+91 90000 10006", "abcdevelopers",
               ("No. 21, ABC Towers, 4th Floor", "Outer Ring Road", "Marathahalli", "Bengaluru", "560037"),
               ("Site - ABC Residency Towers", "Sy. No. 54", "Sarjapur Road", "Dommasandra", "Bengaluru", "562125")),
    "V0010": ("Steel Suppliers", ("Mahesh", "Gowda", "Sales Manager"), "+91 90000 10101", "tungabhadrasteel",
               ("Plot 7, Tungabhadra Steel Yard", "Hospet Road", "Kurugodu Cross", "Ballari", "583101"),
               ("Stock Yard", "Plot 22", "KIADB Industrial Area", "Sanklapur", "Hosapete", "583201")),
    "V0011": ("Building Materials", ("Ravi", "Shankar", "Partner"), "+91 90000 10102", "chamundicement",
               ("No. 112, Chamundi Complex", "Bannur Road", "Alanahalli", "Mysuru", "570028"),
               ("Crusher Unit", "Sy. No. 45", "Belagola Road", "Srirangapatna Taluk", "Srirangapatna", "571438")),
    "V0012": ("Elec & Plumbing", ("Anil", "Rao", "Sales Executive"), "+91 90000 10103", "vidyutelectricals",
               ("No. 23, 1st Floor", "Sadar Patrappa Road", "Chickpet", "Bengaluru", "560002"),
               ("Godown", "No. 9, 4th Cross", "Peenya 2nd Stage", "Peenya", "Bengaluru", "560058")),
    "V0013": ("Elec & Plumbing", ("Senthil", "Kumar", "Sales Manager"), "+91 90000 10104", "jalavahinipipes",
               ("No. 56, Jalavahini Buildings", "Avinashi Road", "Peelamedu", "Coimbatore", "641004"),
               ("Factory", "SF No. 312", "Kurichi Industrial Estate", "Kurichi", "Coimbatore", "641021")),
    "V0014": ("Safety & Consumable", ("Priya", "Patil", "Key Account Manager"), "+91 90000 10105", "rakshaksafety",
               ("Unit 14, Rakshak Industrial Estate", "LBS Marg", "Ghatkopar West", "Mumbai", "400086"),
               ("Warehouse", "Gala 3, Bhiwandi Logistics Park", "Mumbai-Nashik Highway", "Bhiwandi", "Bhiwandi", "421302")),
    "V0015": ("Safety & Consumable", ("Manjunath", "H", "Sales Executive"), "+91 90000 10106", "agniwelding",
               ("No. 77, 1st Main", "Yeshwanthpur Industrial Suburb", "Yeshwanthpur", "Bengaluru", "560022"),
               ("Store", "Plot 41", "KIADB Industrial Area", "Bommasandra", "Bengaluru", "560099")),
    "V0016": ("Tools & Equipment", ("Basavaraj", "Patil", "Partner"), "+91 90000 10107", "shaktitools",
               ("No. 5, Shakti Arcade", "Station Road", "Old Hubballi", "Hubballi", "580020"),
               ("Warehouse", "Plot 18", "Gokul Road Industrial Area", "Gokul Road", "Hubballi", "580030")),
    "V0017": ("Transporters", ("Imran", "Khan", "Operations Manager"), "+91 90000 10108", "sarathiroadlines",
               ("No. 3, Transport Nagar", "Tumkur Road", "Yeshwanthpur", "Bengaluru", "560022"),
               ("Truck Terminal", "Plot 61", "Peenya 1st Stage", "Peenya", "Bengaluru", "560058")),
    "V0018": ("Subcontractors", ("Ramesh", "R", "Proprietor"), "+91 90000 10109", "rameshfabrication",
               ("Shed No. 11", "Apparel Park Road", "KIADB Industrial Area", "Doddaballapur", "561203"),
               ("Workshop", "Shed No. 12", "Apparel Park Road", "KIADB Industrial Area", "Doddaballapur", "561203")),
    # demo BPs loaded by sl_loader.py from data/06_business_partners.json (only completed here, never created)
    "C0001": ("EPC & Infra", ("Rahul", "Shinde", "Procurement Manager"), "+91 90000 20001", "sahyadriinfra",
              ("Sahyadri House, 7th Floor", "Bandra Kurla Complex", "Bandra East", "Mumbai", "400051"),
              ("Site - Navi Mumbai Logistics Hub", "Plot 18", "TTC Industrial Area", "Mahape", "Navi Mumbai", "400710")),
    "C0002": ("Power & Process", ("Ganesan", "R", "Purchase Manager"), "+91 90000 20002", "coromandelpower",
              ("Coromandel Towers, 4th Floor", "Mount Road", "Nandanam", "Chennai", "600035"),
              ("Site - Ennore Power Station", "Ennore Port Road", "Ennore", "Ennore", "Chennai", "600057")),
    "C0003": ("Power & Process", ("Prasanna", "Hegde", "Materials Manager"), "+91 90000 20003", "vijayanagarpetrochem",
              ("Vijayanagar Petrochem Complex", "Sandur Road", "Toranagallu", "Ballari", "583123"),
              ("Site - Refinery Expansion", "Plant Gate 3", "Sandur Road", "Toranagallu", "Ballari", "583123")),
    "C0004": ("Power & Process", ("Anoop", "Menon", "Purchase Manager"), "+91 90000 20004", "nilacement",
              ("Nila Cement Works", "Kanjikode Industrial Area", "Kanjikode", "Palakkad", "678621"),
              ("Site - Kiln Upgrade", "Plant Gate 1", "Kanjikode Industrial Area", "Kanjikode", "Palakkad", "678621")),
    "C0005": ("EPC & Infra", ("Ramana", "Murthy", "Project Manager"), "+91 90000 20005", "telanganametro",
              ("Plot 45, Metro Bhavan", "Begumpet Road", "Begumpet", "Hyderabad", "500016"),
              ("Site - Metro Phase 2 Depot", "Sy. No. 301", "Miyapur Depot Road", "Miyapur", "Hyderabad", "500049")),
    "C0006": ("Manufacturing", ("Vignesh", "K", "Purchase Manager"), "+91 90000 20006", "hosurauto",
              ("Plot 88, SIPCOT Phase I", "Bagalur Road", "SIPCOT Industrial Area", "Hosur", "635126"),
              ("Plant 2", "Plot 92", "SIPCOT Phase II", "Mookandapalli", "Hosur", "635126")),
    "V0001": ("Steel Suppliers", ("Ganesh", "Rao", "Partner"), "+91 90000 20101", "shreeganeshsteel",
              ("No. 14, Shree Ganesh Complex", "Old Madras Road", "KR Puram", "Bengaluru", "560036"),
              ("Stock Yard", "Plot 5", "Hoskote Industrial Area", "Hoskote", "Hoskote", "562114")),
    "V0002": ("Steel Suppliers", ("Srinivas", "Rao", "Sales Manager"), "+91 90000 20102", "deccanstructural",
              ("Plot 31, Deccan Steel House", "IDA Jeedimetla", "Jeedimetla", "Hyderabad", "500055"),
              ("Rolling Yard", "Sy. No. 120", "Medchal Industrial Area", "Medchal", "Medchal", "501401")),
    "V0003": ("Steel Suppliers", ("Arun", "Prakash", "Sales Head"), "+91 90000 20103", "kaverialloys",
              ("No. 9, Kaveri Alloys Building", "GST Road", "Guindy Industrial Estate", "Chennai", "600032"),
              ("Warehouse", "Plot C-14", "Ambattur Industrial Estate", "Ambattur", "Chennai", "600058")),
    "V0004": ("Safety & Consumable", ("Nagaraj", "N", "Proprietor"), "+91 90000 20104", "nandiwelding",
              ("No. 41, 3rd Cross", "Magadi Road", "Kamakshipalya", "Bengaluru", "560079"),
              ("Godown", "No. 18", "Peenya 3rd Phase", "Peenya", "Bengaluru", "560058")),
    "V0005": ("Safety & Consumable", ("Kiran", "Kumar", "Plant Manager"), "+91 90000 20105", "vayugases",
              ("Plot 22, Vayu Gas Plant", "NH-48", "Antharasanahalli Industrial Area", "Tumakuru", "572106"),
              ("Cylinder Filling Station", "Plot 23", "NH-48", "Antharasanahalli Industrial Area", "Tumakuru", "572106")),
    "V0006": ("Safety & Consumable", ("Sneha", "Joshi", "Sales Manager"), "+91 90000 20106", "surakshasafety",
              ("Office 204, Suraksha Plaza", "Mumbai-Pune Highway", "Pimpri", "Pune", "411018"),
              ("Warehouse", "Gat No. 112", "Chakan MIDC", "Chakan", "Pune", "410501")),
    "V0007": ("Subcontractors", ("Bharath", "B", "Proprietor"), "+91 90000 20107", "bharathicoating",
              ("Shed No. 4, Bharathi Works", "Tumkur Road", "Nelamangala Industrial Area", "Nelamangala", "562123"),
              ("Blasting Yard", "Sy. No. 77", "Tumkur Road", "Nelamangala Industrial Area", "Nelamangala", "562123")),
    "V0008": ("Transporters", ("Mohammed", "Rafi", "Operations Manager"), "+91 90000 20108", "mysorefreight",
              ("No. 8, Transport Layout", "Hunsur Road", "Hebbal", "Mysuru", "570017"),
              ("Truck Terminal", "Plot 9", "Bengaluru-Mysuru Road", "Bannimantap", "Mysuru", "570015")),
    "V0009": ("Consultants", ("Prakash", "S", "Partner"), "+91 90000 20109", "prakashassociates",
              ("No. 112, 2nd Floor, Prakash Chambers", "Residency Road", "Shanthala Nagar", "Bengaluru", "560025"),
              ("Office", "No. 112, 2nd Floor", "Residency Road", "Shanthala Nagar", "Bengaluru", "560025")),
}
GST_STATE = {"Karnataka": "29", "Telangana": "36", "Tamil Nadu": "33", "Maharashtra": "27"}


def gstin(state, pan):
    """15-char GSTIN with a valid check digit."""
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    body = GST_STATE[state] + pan + "1Z"
    total = sum(v // 36 + v % 36 for v in (chars.index(c) * (2 if i % 2 else 1) for i, c in enumerate(body)))
    return body + chars[(36 - total % 36) % 36]


def bps():
    """U1 BPs, then the demo BPs from data/06_business_partners.json (Legacy: completed, never created here)."""
    rows = [(kind, acct, False, *r) for kind, rs, acct in (("cCustomer", CUSTOMERS, "5002-02-04-01"),
                                                          ("cSupplier", VENDORS, "3002-02-01")) for r in rs]
    rows += [(b["CardType"], b["ControlAccount"], b["GSTIN"], b["CardCode"], b["CardName"], b["State"], b["City"],
              b["PAN"], b["PaymentTermsDays"], b["WTCode"], None)
             for b in sorted(L.load("06_business_partners"), key=lambda b: (b["CardType"], b["CardCode"]))]
    for kind, acct, legacy_gstin, code, name, state, city, pan, days, wt, note in rows:
        grp, (first, last, pos), mobile, dom, bill, ship = DETAILS[code]
        yield {"CardCode": code, "CardName": name, "CardType": kind, "State": state, "City": city, "PAN": pan,
               "GSTIN": legacy_gstin or gstin(state, pan), "Legacy": bool(legacy_gstin),
               "PaymentTermsDays": days, "WTCode": wt, "ControlAccount": acct, "Note": note,
               "Group": (CUSTOMER_GROUPS if kind == "cCustomer" else VENDOR_GROUPS)[
                   "Intrastate" if state == HOME_STATE else "Interstate"],  # all BPs are in India today
               "Segment": grp, "Contact": f"{first} {last}", "First": first, "Last": last,
               "Position": pos, "Mobile": mobile, "Email": f"accounts@{dom}.example",
               "ContactEmail": f"{first.lower()}@{dom}.example", "Bill": bill, "Ship": ship,
               "PriceList": "SAL" if kind == "cCustomer" else "PUR"}


# ---------------------------------------------------------------------------------------------- Excel
BP_HEAD = ["Code", "Name", "Billing / pay-to address", "Shipping address", "State", "GSTIN (dummy)", "PAN (dummy)",
           "Payment terms", "Contact person", "Position", "Mobile", "Email", "BP group",
           "Control account", "Price list", "TDS code", "Buys / supplies"]


def bp_row(b):
    (bb, bs, ba, bc, bz), (sn, sb, ss, sa, sc, sz) = b["Bill"], b["Ship"]
    lists = {p["Key"]: p["PriceListName"] for p in L.load("04_price_lists")}
    return (b["CardCode"], b["CardName"], f"{bb}, {bs}, {ba}, {bc} - {bz}", f"{sn}: {sb}, {ss}, {sa}, {sc} - {sz}",
            b["State"], b["GSTIN"], b["PAN"], f"Net {b['PaymentTermsDays']} Days", b["Contact"],
            b["Position"], b["Mobile"], b["Email"], b["Group"], b["ControlAccount"], lists[b["PriceList"]],
            b["WTCode"] or "-", b["Note"])


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
        "Resources": (["Code", "Name", "Type", "Cost per minute", "Warehouse"], RESOURCES),
        "BOMs": (["Parent", "Warehouse", "Seq", "Type", "Component", "Qty", "UoM", "Component warehouse", "Issue method"],
                 [(p, w, n, "Resource" if t == "R" else "Item", c, q,
                   "Mins" if t == "R" else next(UOMS[i["InvUoM"]] for i in ITEMS if i["Code"] == c), cw,
                   "Backflush" if m == "B" else "Manual")
                  for p, (w, ls) in BOMS.items() for n, (c, q, cw, t, m) in enumerate(map(bom_line, ls), 1)]),
        "Items": (["Item Code", "Description", "Item Group", "Inventory Item", "Purchase Item", "Sales Item", "UoM Group",
                   "UOM", "Purchase UOM", "Sales UOM", "Pricing Unit", "Default Warehouse", "Valuation Method", "HSN / SAC",
                   "Tax Category", "GST % (indicative)", "Cost", "Purchase Price", "Sales Price", "Batch Managed",
                   "Serial Managed"],
                  [(i["Code"], i["Description"], i["Group"] or "Items (services)", yn(i["Inv"]), yn(i["Pur"]), yn(i["Sal"]),
                    i["UoMGroup"], UOMS[i["InvUoM"]], UOMS[i["PurUoM"]], UOMS[i["SalUoM"]], UOMS[i["PriceUoM"]], i["Whse"] or "-",
                    val[i["Valuation"]], i["HSN"], "Regular (Service)" if not i["Inv"] else "Regular (Goods)", i["GST"],
                    i["Cost"], i["PurPrice"], i["SalPrice"], yn(i["Batch"]), yn(i["Serial"])) for i in ITEMS]),
        "Customers": (BP_HEAD, [bp_row(b) for b in bps() if b["CardType"] == "cCustomer"]),
        "Vendors": (BP_HEAD, [bp_row(b) for b in bps() if b["CardType"] == "cSupplier"]),
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


def bom_line(line):
    """(code, qty, warehouse[, I/R, M/B]) -> (code, qty, warehouse, type, issue method)"""
    return (*line, "I", "M")[:5] if len(line) == 3 else line


# ---------------------------------------------------------------------------------------------- SAP
def load_warehouses(sl):
    """Create missing warehouses; an existing code only gets its name corrected."""
    for code, name, stock in WAREHOUSES:
        cur = sl.get(f"Warehouses('{code}')?$select=WarehouseName")
        if cur:
            if cur["WarehouseName"] != name:
                sl.patch("Warehouses", code, {"WarehouseName": name}, f"{code} name {name}")
            continue
        sl.post("Warehouses", {"WarehouseCode": code, "WarehouseName": name, "Location": L.TDS_LOCATION,
                               "StockAccount": stock, "ExpenseAccount": "4001-16", "RevenuesAccount": "2001-01-01-01",
                               "PurchaseAccount": "4008-01", "PriceDifferencesAccount": "4001-17",
                               "VarianceAccount": "4001-23", "DecreasingAccount": "4001-21",
                               "IncreaseGLAccount": "4001-20", "DecreaseGLAccount": "4001-21",
                               "WIPMaterialAccount": "5002-01-02", "WIPMaterialVarianceAccount": "4001-23"}, f"{code} {name}")


def load_sap(sl):
    v = lambda p: (sl.get(p) or {}).get("value", [])
    cur = {u["Code"]: u for u in v("UnitOfMeasurements?$select=AbsEntry,Code,Name")}
    uom = {c: u["AbsEntry"] for c, u in cur.items()}
    for code, name in UOMS.items():
        if code not in uom:
            res = sl.post("UnitOfMeasurements", {"Code": code, "Name": name}, f"UoM {code}")
            if res:
                uom[code] = res["AbsEntry"]
        elif cur[code]["Name"] != name:
            sl.patch("UnitOfMeasurements", uom[code], {"Name": name}, f"UoM {code} name {name}")
    groups_now = {g["Code"]: g for g in v("UnitOfMeasurementGroups")}
    for old, new in UOM_GROUP_RENAMED.items():  # rename in place: items keep their group, no duplicate group
        if old in groups_now and new not in groups_now:
            sl.patch("UnitOfMeasurementGroups", groups_now[old]["AbsEntry"], {"Code": new}, f"UoM group {old} -> {new}")
            groups_now[new] = groups_now.pop(old)
    for code, (name, base, alt) in UOM_GROUPS.items():  # existing groups: fix the name, add missing alternate UoMs
        g = groups_now.get(code)
        if not g:
            continue
        have = {d["AlternateUoM"] for d in g["UoMGroupDefinitionCollection"]}
        new_uoms = [u for u, *_ in alt if uom[u] not in have]
        add = [{"AlternateUoM": uom[u], "AlternateQuantity": a, "BaseQuantity": q} for u, a, q in alt if u in new_uoms]
        if g["Name"] != name or add:
            sl.patch("UnitOfMeasurementGroups", g["AbsEntry"],
                     {"Name": name, **({"UoMGroupDefinitionCollection": add} if add else {})},
                     f"UoM group {code}" + (f" + {', '.join(new_uoms)}" if add else ""))
    ugp = {g["Code"]: g["AbsEntry"] for g in v("UnitOfMeasurementGroups?$select=AbsEntry,Code")}
    for code, (name, base, alt) in UOM_GROUPS.items():
        if code not in ugp:
            res = sl.post("UnitOfMeasurementGroups", {
                "Code": code, "Name": name, "BaseUoM": uom[base],
                "UoMGroupDefinitionCollection": [{"AlternateUoM": uom[u], "AlternateQuantity": a, "BaseQuantity": q}
                                                 for u, a, q in alt]}, f"UoM group {code}")
            if res:
                ugp[code] = res["AbsEntry"]

    load_warehouses(sl)

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
    mat = {RM: "mt_RawMaterial", FG: "mt_FinishedGoods", SA: "mt_GoodsInProcess"}
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
                "PricingUnit": uom[i["PriceUoM"]],
                "GSTRelevnt": "tYES", "GSTTaxCategory": "gtc_Regular",
                "ItemPrices": [{"PriceList": pl, "Price": p} for pl, p in ((pur, i["PurPrice"]), (sal, i["SalPrice"])) if p]}
        make = i["Code"] in BOMS or i["Group"] == FG
        if i["Inv"]:
            body.update({"ItemClass": "itcMaterial", "ChapterID": hsn.get(i["HSN"]), "GLMethod": "glm_ItemClass",
                         "CostAccountingMethod": i["Valuation"], "DefaultWarehouse": i["Whse"],
                         "ManageStockByWarehouse": "tYES", "MaterialType": mat.get(i["Group"], "mt_RawMaterial"),
                         "ProcurementMethod": "bom_Make" if make else "bom_Buy",
                         "PlanningSystem": "bop_MRP" if make else "bop_None",  # make items planned by MRP
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
        sl.post("MaterialRevaluation", {"DocDate": DOC_DATE, "RevalType": "P", "Comments": "U1 standard cost",
                                        "MaterialRevaluationLines": [{"ItemCode": i["Code"], "Price": i["Cost"], "WarehouseCode": w}
                                                                     for i in new_std for w in whs]},
                "Standard cost " + ", ".join(i["Code"] for i in new_std))

    for code, name, rtype, cost, whs_res in RESOURCES:
        if not sl.find("Resources", "VisCode", code):
            sl.post("Resources", {"VisCode": code, "Name": name, "Type": rtype, "IssueMethod": "rimBackflush",
                                  "Cost1": cost, "DefaultWarehouse": whs_res, "ResourceWarehouses": [{"Warehouse": whs_res}]},
                    f"Resource {code} {name}")
    for code, (whs_bom, lines) in BOMS.items():
        if not sl.exists("ProductTrees", code):
            sl.post("ProductTrees", {"TreeCode": code, "TreeType": "iProductionTree", "Quantity": 1, "Warehouse": whs_bom,
                                     "ProductTreeLines": [{"ItemCode": c, "Quantity": q, "Warehouse": w,
                                                           "ItemType": "pit_Resource" if t == "R" else "pit_Item",
                                                           "IssueMethod": "im_Backflush" if m == "B" else "im_Manual"}
                                                          for c, q, w, t, m in map(bom_line, lines)]},
                    f"BOM {code} ({len(lines)} lines)")

    for gtype, names in (("bbpgt_CustomerGroup", CUSTOMER_GROUPS), ("bbpgt_VendorGroup", VENDOR_GROUPS)):
        for name in names.values():
            if not sl.find("BusinessPartnerGroups", "Name", name):
                sl.post("BusinessPartnerGroups", {"Name": name, "Type": gtype}, f"BP group {name}")
    bpgrp = {g["Name"]: g["Code"] for g in v("BusinessPartnerGroups")}
    plist = {k: L.price_list_no(sl, k) for k in ("SAL", "PUR")}
    terms = {t["PaymentTermsGroupName"]: t["GroupNumber"] for t in v("PaymentTermsTypes?$select=GroupNumber,PaymentTermsGroupName")}
    for b in bps():
        st = L.state_code(sl, b["State"])
        (bb, bs, ba, bc, bz), (sn, sb, ss, sa, sc, sz) = b["Bill"], b["Ship"]
        addr = lambda t, n, n2, bld, street, block, city, pin: {
            "AddressName": n, "AddressType": t, "AddressName2": n2, "BuildingFloorRoom": bld, "Street": street,
            "Block": block, "City": city, "ZipCode": pin, "Country": "IN", "State": st, "GSTIN": b["GSTIN"],
            "GstType": "gstRegularTDSISD"}
        details = {"GroupCode": bpgrp[b["Group"]], "PriceListNum": plist[b["PriceList"]],
                   "Cellular": b["Mobile"], "EmailAddress": b["Email"], "ContactPerson": b["Contact"],
                   "DebitorAccount": b["ControlAccount"], "PayTermsGrpCode": terms.get(f"Net {b['PaymentTermsDays']} Days"),
                   "BPAddresses": [addr("bo_BillTo", "Bill To", "", bb, bs, ba, bc, bz),
                                   addr("bo_ShipTo", "Ship To", sn, sb, ss, sa, sc, sz)]}
        if b["Note"]:
            details["Notes"] = b["Note"]
        contact = {"Name": b["Contact"], "FirstName": b["First"], "LastName": b["Last"], "Position": b["Position"],
                   "MobilePhone": b["Mobile"], "E_Mail": b["ContactEmail"]}
        old = RENAMED_FROM.get(b["CardCode"])
        if old and sl.exists("BusinessPartners", old):
            sl.log(f"WARN {old} still exists - rename it to {b['CardCode']} in the SAP client first")
            continue
        if sl.exists("BusinessPartners", b["CardCode"]):
            # complete BPs created before the details existed; the contact is added only once
            cur = sl.get(f"BusinessPartners('{b['CardCode']}')?$select=ContactEmployees,BPAddresses")
            if not any(c["Name"] == b["Contact"] for c in cur["ContactEmployees"]):
                details["ContactEmployees"] = [contact]
            rows = {(a["AddressName"], a["AddressType"]): a["RowNum"] for a in cur["BPAddresses"]}
            for a in details["BPAddresses"]:  # without RowNum the PATCH tries to add the address again
                if (a["AddressName"], a["AddressType"]) in rows:
                    a.update({"RowNum": rows[(a["AddressName"], a["AddressType"])], "BPCode": b["CardCode"]})
            sl.patch("BusinessPartners", b["CardCode"], details, f"{b['CardCode']} details")
            continue
        if b["Legacy"]:
            sl.log(f"WARN {b['CardCode']} missing - create it with sl_loader.py --step bps, then re-run")
            continue
        body = {"CardCode": b["CardCode"], "CardName": b["CardName"], "CardType": b["CardType"], "Currency": "INR",
                **details, "ContactEmployees": [contact], "BPFiscalTaxIDCollection": [{"Address": "", "TaxId0": b["PAN"]}]}
        if b["WTCode"]:
            body.update({"TypeReport": "atOthers" if b["PAN"][3] in "PH" else "atCompany",
                         "SubjectToWithholdingTax": "boYES", "BPWithholdingTaxCollection": [{"WTCode": b["WTCode"]}]})
        sl.post("BusinessPartners", body, f"{b['CardCode']} {b['CardName']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", action="store_true", help="only write the Excel master data sheet")
    ap.add_argument("--warehouses", action="store_true", help="only create / rename the warehouses")
    a = ap.parse_args()
    write_excel()
    if a.excel:
        return
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    load_warehouses(sl) if a.warehouses else load_sap(sl)
    print(f"Done. Failures: {sl.failures}")


if __name__ == "__main__":
    main()
