import datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule, DataBarRule
from openpyxl.chart import DoughnutChart, BarChart, Reference
from openpyxl.worksheet.datavalidation import DataValidation

OUT = r"C:\Projects\AKE-Database\AKE_Project_Tracking_System_Tracker_V1.xlsx"
MAIN = "AKE Tracking System V1"
Q = f"'{MAIN}'"
TODAY = dt.datetime(2026, 10, 1)
TRAIN = dt.datetime(2026, 10, 5)

def F(**k): return Font(name="Calibri", **k)
def fill(c): return PatternFill("solid", fgColor=c)

wb = Workbook()
dash = wb.active; dash.title = "Dashboard"
ws = wb.create_sheet(MAIN)
coa = wb.create_sheet("COA Findings")
how = wb.create_sheet("How To Use")

# ---------------- Main tracker ----------------
stages = [  # (status col, header, fill, extra Risk column?)
    ("B", "Empathise", "DDEBF7", False),
    ("H", "Define", "E2EFDA", False),
    ("N", "Ideate", "FFF2CC", True),
    ("U", "Prototype", "FCE4D6", False),
    ("AA", "Testing", "E4DFEC", False),
]
from openpyxl.utils import column_index_from_string as ci, get_column_letter as gl
ws["A1"] = "Section / Topic"; ws["A1"].font = F(b=True); ws["A1"].fill = fill("D9D9D9")
for col, name, colr, risk in stages:
    c0 = ci(col)
    heads = [f'="{name} Version (V"&$AH$2&" - Open/Closed)"', "Details"]
    heads += (["Risk / Assumption"] if risk else []) + ["Responsibility", "Target Date", "Attachments"]
    for i, h in enumerate(heads):
        cell = ws.cell(row=1, column=c0 + i, value=h)
        cell.font = F(b=True); cell.fill = fill(colr)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.column_dimensions[gl(c0)].width = 30
    ws.column_dimensions[gl(c0 + 1)].width = 60
    ws.column_dimensions[gl(c0 + (3 if risk else 2))].width = 18
    ws.column_dimensions[gl(c0 + (4 if risk else 3))].width = 13
    if risk: ws.column_dimensions[gl(c0 + 2)].width = 40
ws.column_dimensions["A"].width = 44
ws.freeze_panes = "B2"

QL = "Qltc Consultant"
QC = "Qltc Consultant / Claude"
DEF_DRAFT = "Open"

# topic rows: (topic, emp_status, emp_details, emp_resp, def_status, def_details, def_resp,
#              ide_status, ide_details, ide_risk)
sections = [
 ("A. Customer & Training Scope", [
  ("A1. Customer Profile & Business Model", "Closed",
   "AKE Infrastructure Pvt. Ltd. (akeinfra.com) - Qltc customer for 5+ years, on SAP B1 (SQL) for 5 years. "
   "Design document describes them as a fabrication company; environment section says Infrastructure / Construction / "
   "Engineering Projects. Working model agreed: steel-structure fabricator (plates, structurals, TMT, special grades) that also "
   "executes project work - confirmed by AKE's own item groups (RM Plates, RM Structurals, Machining, Rolling) and job-work "
   "expense heads (Blasting & Primer, Galvanizing, Fabrication & Erection) in their Chart of Accounts.",
   QC, "Open", "TBD", "Open", "TBD", ""),
  ("A2. Training Participants & Roles", "Closed",
   "Rashmi and Namrata - Directors; Ashok - Planning, SCM; Sunil - Finance; Veena - Accounts. "
   "Current users are new to SAP B1 - the earlier super users trained by Qltc have left AKE.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("A3. Training Schedule & Module Scope", "Closed",
   "3 days: Mon 5 Oct - Wed 7 Oct 2026. Scope: OTC (Order to Cash), PTP (Procure to Pay), "
   "PTS = Production to Stock (BOM -> Production Order -> Issue for Production -> Receipt from Production -> Stock) - "
   "confirmed by Qltc 1 Oct 2026, NOT plan-to-stock. Also Finance, Inventory, Resources.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("A4. SAP Environment", "Open",
   "Confirmed: SAP Business One 10, SAP HANA, India localization, INR, TRAINING database (not production). "
   "NOT YET confirmed: exact B1 10 Feature Pack / patch level of the target server, server name and who creates the company DB.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("A5. Selling Price Confidentiality", "Closed",
   "Management does not want trainees to know item selling prices. Hard constraint for every training screen, report and demo document.",
   QL, DEF_DRAFT,
   "DRAFT: Trainees must be able to run OTC end-to-end without ever seeing a real selling price. Success = no real price visible "
   "in price lists, item master, sales documents, gross profit window or reports under any trainee login.",
   QC, "Open",
   "DRAFT options: (1) dummy prices only in the training DB; (2) authorizations - Price Lists = No Authorization, Gross Profit = No Authorization, "
   "Item Master price tab hidden; (3) both. Recommended: both.",
   "Risk: authorizations alone can leak via reports/Excel export - dummy prices remove the risk at source."),
 ]),
 ("B. AKE Pain Points", [
  ("B1. Inventory Not Matching Physical Stock", "Open",
   "Stated by Qltc: system inventory does not match physical inventory. NOT YET explored: which item groups/warehouses are worst, "
   "whether production issues are backflushed or manual, whether GRPOs are posted on receipt, last physical count date. "
   "Early evidence from COA: separate Stock Difference Gain/Loss and Revaluation accounts exist (4001-18 to 4001-21) but 10 inventory "
   "group accounts are blank (5002-01-01-14, -19, -21, -22, -24 to -29) and WIP exists twice (5002-01-01-15 and 5002-01-02).",
   QC, "Open", "TBD", "Open", "TBD", ""),
  ("B2. Finance Reports Not Coming Properly", "Closed",
   "Root causes found in AKE's real Chart of Accounts (598 accounts) - see 'COA Findings' sheet: 34 liability-coded (3002-xx) lender/loan "
   "accounts sit in the ASSET drawer under 5002-05-06 Others; the same loans are duplicated in Liabilities (e.g. Kotak LAP 19510148, "
   "Kotak LAP 19404642, Deutsche Bank 0037, JSW One Finance); 36 accounts have no name; 10 orphan accounts; 2 malformed codes; "
   "GST payable split across 3002-03 / 3002-09 / 3003-09; TDS Payable spread over 14 accounts.",
   QC, DEF_DRAFT,
   "DRAFT: Sunil and Veena need a Balance Sheet and P&L they can trust. Today loans show as negative assets, duplicated loan accounts split balances, "
   "and GST/TDS liabilities are scattered - so no report can be correct whatever the user does.",
   QC, "Open", "TBD", ""),
  ("B3. BOM Needs Correction", "Open",
   "Stated by Qltc: BOMs need to be corrected. NOT YET explored: which BOMs, what is wrong (quantities, missing components, wrong BOM type, "
   "no resources/routing), and whether AKE's real BOMs can be shared. Training DB will use dummy fabrication BOMs unless samples are provided.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("B4. Users Not Aware of SAP B1", "Closed",
   "Earlier super-user training was given but those users left; current users are new. Training must be hands-on, role-based and "
   "follow AKE's real processes, with step-by-step exercises per participant.",
   QL, "Open", "TBD", "Open", "TBD", ""),
 ]),
 ("C. Database Configuration & Data", [
  ("C1. Chart of Accounts - AKE Real", "Closed",
   "Decision (Qltc, 1 Oct 2026): use AKE's real Chart of Accounts, not the standard India template, and use it to show AKE the finance report "
   "problems. Export received as 5 files (Asset 199, Liability 122, Equity 12, Revenue 37, Expenditure 228 accounts) and pushed to GitHub.",
   QL, DEF_DRAFT,
   "DRAFT: Load AKE's COA so trainees recognise their own accounts, but the training DB must also demonstrate the corrected structure. "
   "Open decision: load AS-IS (to show the problem) and correct live in the Finance session, or load a corrected copy plus a before/after report.",
   QC, "Open", "TBD", ""),
  ("C2. Tax - GST and TDS (No e-Invoice)", "Closed",
   "Decision (Qltc, 1 Oct 2026): GST + TDS required; e-Invoice out of scope. Note: TDS is not written in the design document - recorded here "
   "as Qltc's instruction. AKE already uses TDS @0.75%, 1%, 1.5%, 2%, 7.5%, 10%, on Rent, Professional, Purchases (194Q) and Interest.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("C3. Master Data - Realistic Dummy Items & BPs", "Closed",
   "Decision (Qltc, 1 Oct 2026): realistic dummy data, not AKE's live masters. Items follow AKE's own item groups (RM Plates, RM Structurals, "
   "RM Special Grades, TMT Rod, Consumables, Tools, PPE, Sub Assembly, FG). Indian vendors and customers with dummy GSTIN/PAN.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("C4. Opening Balances & Posting Periods", "Open",
   "NOT YET confirmed: financial year (assume FY 2026-27, Apr-Mar), posting period granularity, and whether opening balances (stock, BP, GL) "
   "should be loaded as dummy values.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("C5. Users, Licences & Authorizations", "Open",
   "Known: 5 participants (+ trainer). NOT YET confirmed: number and type of licences on the training server, user codes, "
   "whether Directors get full or restricted access.",
   QL, "Open", "TBD", "Open", "TBD", ""),
 ]),
 ("D. Method & Delivery", [
  ("D1. Design Thinking + Spiral Model", "Closed",
   "Qltc method (Qltc_Design_Thinking_Spiral_Model_Training.pptx): Empathize+Define -> Q1 Objectives; Ideate -> Q1/Q2 Alternatives; "
   "Prototype -> Q2/Q3 Risk & Build; Test -> Q4 Review & plan next loop. Followed regardless of deadline pressure.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("D2. Deadline", "Closed",
   "Database ready for Qltc testing by 1 Oct 2026 afternoon; demo/training from Mon 5 Oct 2026.",
   QL, "Open", "TBD", "Open", "TBD", ""),
  ("D3. Delivery Mechanism - Access to SAP", "Open",
   "Claude cannot reach the SAP server. NOT YET decided: Qltc runs the deliverables (setup checklist, DTW templates, HANA SQL checks), "
   "or Qltc provides Service Layer access to a test server so data can be posted directly.",
   QC, "Open", "TBD", "Open", "TBD", ""),
  ("D4. Source Control", "Closed",
   "All project files kept in GitHub repo reetha-qltc/AKE-Database (public - confirmed by Qltc, including AKE COA files).",
   QC, "Open", "TBD", "Open", "TBD", ""),
 ]),
]

# ---- Answers from Qltc, 1 Oct 2026 (second round) - override the base rows ----
D = "Qltc, 1 Oct 2026"
UPD = {
 "A4": dict(B="Closed",
   C="SAP Business One 10.0 for SAP HANA, version 10.00.310, FP 2511 (64-bit), India localization, INR - confirmed from "
     "'About SAP Business One' screenshot (Screenshot (1).png). Client host SSO-WINDOWS1. "
     "OPEN POINT: the About box shows the licence is issued to 'Bangalore Biotech Labs Private Limited', not AKE or Qltc - "
     "Qltc to confirm this is the right server and that the licence permits an AKE training company.",
   F="Screenshot (1).png",
   H="Closed", I="Target build: B1 10.0 FP 2511 (10.00.310) on HANA. All DTW templates, Service Layer payloads and SQL checks built for this version.",
   J=QC, K=TODAY),
 "B1": dict(B="Closed",
   C=f"Answers ({D}): most item groups AND warehouses mismatch; Issue for Production is done MANUALLY; GRPO is posted when goods arrive "
     "(purchase items); Receipt from Production is posted for produced items. Supporting COA evidence: 10 blank inventory group accounts, "
     "WIP held in two accounts (5002-01-01-15 and 5002-01-02).",
   H="Open",
   I="DRAFT: Ashok needs system stock to equal physical stock in every warehouse. With manual Issue for Production, components are issued "
     "late, partially or in wrong quantities (and with wrong BOM quantities - see B3), so stock drifts while GRPO/Receipt keep adding to it. "
     "Training must show: correct issue against a production order, warehouse-wise stock check, Inventory Counting and Posting to correct differences.",
   J=QC, K=TODAY),
 "B3": dict(B="Closed",
   C=f"Answers ({D}): BOM quantities do not match reality - wrong quantity entries on BOM lines. Training DB will use dummy fabrication BOMs "
     "with realistic quantities (weight-based steel: kg per unit), plus one deliberately wrong BOM to demonstrate the effect.",
   H="Open",
   I="DRAFT: Wrong BOM quantities make every production order issue the wrong components, so stock and product cost are wrong even when "
     "users follow the process. Training must show how a wrong BOM quantity flows into Issue for Production, stock and cost - and how to correct it.",
   J=QC, K=TODAY),
 "C1": dict(H="Closed",
   I=f"Decision ({D}): load AKE's Chart of Accounts EXACTLY as given (as-is, all 598 accounts), so trainees see their own structure and the "
     "COA Findings can be demonstrated live in the Finance session. Corrections are shown, not pre-applied.",
   J=QL, K=TODAY),
 "C4": dict(B="Closed",
   C=f"Decision ({D}): use DUMMY opening balances (stock, BP, GL). Financial year assumed FY 2026-27 (Apr 2026 - Mar 2027), monthly posting periods.",
   H="Closed", I="Opening balances: dummy stock per item/warehouse, dummy BP balances, dummy GL balances against 1003 Opening Balance Offset Account.",
   J=QC, K=TODAY),
 "C5": dict(B="Closed",
   C=f"Decision ({D}): 6 user licences - Rashmi, Namrata, Ashok, Sunil, Veena + trainer (manager). Licence type not yet stated (assume Professional).",
   H="Closed", I="6 users, role-based authorizations; selling prices hidden for all trainee users (A5).",
   J=QC, K=TODAY),
 "D3": dict(B="Closed",
   C=f"Decision ({D}): Qltc will provide Service Layer access - data will be posted directly by Claude. Credentials to be kept in a local, "
     "git-ignored file - never committed to the public repo. Pending: Service Layer URL, company DB name, user.",
   H="Open", I="TBD"),
}

# ---- Spiral 1 Ideate / Prototype progress (1 Oct 2026, after "continue with creating database") ----
PKG = "tools/build_data.py -> data/*.json; tools/sl_loader.py; docs/01_Company_Setup_Checklist.md"
def ip(ideate, proto, risk=None):
    d = dict(N="Closed", O=ideate, Q=QC, R=TODAY, U="Open", V=proto, W=QC, X=TODAY, Y=PKG)
    if risk: d["P"] = risk
    return d
PROG = {
 "A5": ip("Chosen: both layers - only dummy sales prices exist in the DB ('Sales Price (Dummy - Restricted)' price list, FG items only) "
          "+ No Authorization on Price Lists, Gross Profit and Sales Analysis for all users except TRAINER.",
          "Built: price lists + dummy FG prices in data package; authorization settings in checklist Step 7. Awaiting load and SUNIL-login test.",
          "Authorizations are set manually - Service Layer cannot set general authorizations."),
 "B1": ip("Chosen: 6 clear warehouses (RM-STR, CONS, SHOP, FG, SCRAP, SITE), manual Issue for Production kept (AKE's real practice), "
          "Block negative inventory = Yes, dummy opening stock per warehouse, Inventory Counting exercise in training.",
          "Built: warehouses, items with manual issue method, opening stock (30 lines). Awaiting load."),
 "B3": ip("Chosen: 5 production BOMs with realistic steel weights (e.g. ISMB300 6m column = 265.2 kg) incl. resources; "
          "the 'wrong BOM' (2652 kg decimal slip) is a live trainer exercise, not loaded.",
          "Built: 09_boms.json (2 sub-assemblies, 3 FG). Awaiting load."),
 "C1": ip("Chosen: load 598 accounts as given. Parents rebuilt from codes + file order (export lost indentation); 42 placed by position; "
          "36 blank names get placeholder '(No name in AKE COA) <code>' because B1 requires a name.",
          "Built: 01_chart_of_accounts.json + 01_coa_placement_review.json. Dry-run OK (598 posts). Awaiting load.",
          "Placement of 42 accounts is reconstructed - verify against OACT (FatherNum, Levels) from AKE's SQL DB if exact tree matters."),
 "C2": ip("Chosen: 4 GST codes (CGST+SGST / IGST at 18% and 12%) and 6 TDS codes (194Q, 194C1, 194C2, 194J, 194I, 194A) on AKE's existing accounts.",
          "Built: 07_gst_codes.json, 07_tds_codes.json; setup in checklist Steps 5-6 (manual). HSN per item in data package.",
          "India tax setup is manual - not loaded via Service Layer."),
 "C3": ip("Chosen: 37 dummy items across AKE's 9 item groups; 9 fictional vendors + 6 fictional customers in KA/TN/MH/TS/KL with checksum-valid dummy GSTIN.",
          "Built: 05_items.json, 06_business_partners.json. Dry-run OK. Awaiting load."),
 "C4": ip("Chosen: opening date 01-Apr-2026 against 1003 Opening Balance Offset Account - stock via Goods Receipt, BP and GL via Journal Entries.",
          "Built: 11_opening_balances.json (30 stock lines, 6 BP, 10 GL). Awaiting load."),
 "C5": ip("Chosen: 6 users (TRAINER superuser), role matrix in checklist Step 7; licences assigned manually.",
          "Built: 10_users.json; passwords from git-ignored .env. Awaiting load."),
 "D3": dict(H="Closed", I="Loader posts all masters and opening balances through Service Layer; Qltc creates the empty company and does the manual "
            "setup steps (G/L determination, GST, TDS, licences, authorizations).", J=QC, K=TODAY,
            **ip("Chosen: idempotent Python loader (skips existing records, logs every call), dry-run mode, credentials only in .env.",
                 "Built and dry-run tested (all 13 steps). Not yet run against the server - expect a short fix-and-rerun loop on first contact.")),
}
for k, v in PROG.items():
    UPD.setdefault(k, {}).update(v)

r = 2
for title, topics in sections:
    c = ws.cell(row=r, column=1, value=title); c.font = F(b=True); c.fill = fill("BFBFBF")
    r += 1
    for row in topics:
        if len(row) == 9:  # no Define owner yet
            row = row[:6] + (None,) + row[6:]
        (t, es, ed, er, ds, dd, dr, is_, idt, irisk) = row
        vals = {
            "A": t, "B": es, "C": ed, "D": er, "E": TODAY,
            "H": ds, "I": dd, "J": dr if dd != "TBD" else None, "K": TODAY if dd != "TBD" else None,
            "N": is_, "O": idt, "P": irisk or None, "Q": QC if idt != "TBD" else None, "R": TODAY if idt != "TBD" else None,
            "U": "Open", "V": "TBD", "AA": "Open", "AB": "TBD",
        }
        if t.startswith("B2") or t.startswith("C1"):
            vals["F"] = "COA Findings sheet; Chart of Accounts *.csv"
        if t.startswith("D1"):
            vals["F"] = "Qltc_Design_Thinking_Spiral_Model_Training.pptx"
        vals.update(UPD.get(t.split(".")[0], {}))
        for k, v in vals.items():
            if v is None: continue
            cell = ws[f"{k}{r}"]; cell.value = v; cell.font = F()
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if isinstance(v, dt.datetime): cell.number_format = "dd-mmm-yyyy"
        r += 1
LAST = r - 1

# iteration info
info = [("Version", 1),
        ("Objective", "Build and validate a complete SAP B1 10 (HANA, India, INR) training database for AKE Infrastructure Pvt. Ltd. "
                      "covering OTC, PTP, Production to Stock, Finance, Inventory and Resources - using AKE's real COA, GST + TDS, "
                      "dummy items/BPs, and never exposing real selling prices."),
        ("Owner", "Qltc Consultant"),
        ("Start Date", TODAY), ("Target Date", TODAY),
        ("Overall % Complete", None),
        ("Training Start", TRAIN)]
ws["AG1"] = "Iteration Info"; ws["AG1"].font = F(b=True)
for i, (k, v) in enumerate(info, start=2):
    ws[f"AG{i}"] = k; ws[f"AG{i}"].font = F()
    if v is not None:
        ws[f"AH{i}"] = v; ws[f"AH{i}"].font = F()
        ws[f"AH{i}"].alignment = Alignment(wrap_text=True, vertical="top")
        if isinstance(v, dt.datetime): ws[f"AH{i}"].number_format = "dd-mmm-yyyy"
ws.column_dimensions["AG"].width = 20; ws.column_dimensions["AH"].width = 50
sc = ["B", "H", "N", "U", "AA"]
closed = "+".join(f'COUNTIF({s}2:{s}{LAST},"Closed")' for s in sc)
total = "+".join(f'COUNTIF({s}2:{s}{LAST},"Closed")+COUNTIF({s}2:{s}{LAST},"Open")' for s in sc)
ws["AH7"] = f"=IF(({total})=0,0,({closed})/({total}))"
ws["AH7"].number_format = "0%"

dv = DataValidation(type="list", formula1='"Open,Closed"', allow_blank=True)
ws.add_data_validation(dv)
for s in sc:
    dv.add(f"{s}2:{s}200")
    ws.conditional_formatting.add(f"{s}2:{s}200", CellIsRule(operator="equal", formula=['"Closed"'],
        fill=fill("C6EFCE"), font=Font(color="006100")))
    ws.conditional_formatting.add(f"{s}2:{s}200", CellIsRule(operator="equal", formula=['"Open"'],
        fill=fill("FFC7CE"), font=Font(color="9C0006")))

# ---------------- Dashboard ----------------
dash.merge_cells("A1:I1"); dash["A1"] = "AKE Project Tracking System"
dash["A1"].font = F(sz=20, b=True, color="FFFFFF"); dash["A1"].fill = fill("1F3864")
dash.merge_cells("A2:I2"); dash["A2"] = "Design Thinking + Spiral Model  |  AKE SAP B1 Training Database  |  Tracker Dashboard (V1)"
dash["A2"].font = F(sz=12, color="D9E2F3"); dash["A2"].fill = fill("1F3864")
for c in "BCDEFGHI":
    dash[f"{c}1"].fill = fill("1F3864"); dash[f"{c}2"].fill = fill("1F3864")
kpis = [("A", "B", "VERSION", "2E75B6", "DDEBF7", f"={Q}!AH2", "0"),
        ("C", "D", "OVERALL % COMPLETE", "BF8F00", "FFF2CC", f"={Q}!AH7", "0%"),
        ("E", "F", "BOTTLENECK STAGE", "C55A11", "FCE4D6", "=INDEX($A$11:$A$15,MATCH(MIN($E$11:$E$15),$E$11:$E$15,0))", None),
        ("G", "H", "TOPICS TRACKED", "7030A0", "E4DFEC",
         f'=COUNTIF({Q}!$B$2:$B$200,"Closed")+COUNTIF({Q}!$B$2:$B$200,"Open")', "0")]
for a, b, lab, dark, light, fml, nf in kpis:
    dash.merge_cells(f"{a}4:{b}4"); dash[f"{a}4"] = lab
    dash[f"{a}4"].font = F(sz=10, b=True, color="FFFFFF"); dash[f"{a}4"].fill = fill(dark)
    dash[f"{b}4"].fill = fill(dark)
    dash.merge_cells(f"{a}5:{b}7"); dash[f"{a}5"] = fml
    dash[f"{a}5"].font = F(sz=22, b=True, color=dark)
    for rr in range(5, 8):
        for cc in (a, b): dash[f"{cc}{rr}"].fill = fill(light)
    dash[f"{a}5"].alignment = Alignment(horizontal="center", vertical="center")
    dash[f"{a}4"].alignment = Alignment(horizontal="center")
    if nf: dash[f"{a}5"].number_format = nf
dash["A9"] = "PROGRESS BY PHASE"; dash["A9"].font = F(sz=13, b=True, color="1F3864")
for i, h in enumerate(["Stage", "Closed", "Open", "Total", "% Complete"]):
    c = dash.cell(row=10, column=1 + i, value=h); c.font = F(b=True, color="FFFFFF"); c.fill = fill("404040")
stage_colors = ["2E75B6", "548235", "BF8F00", "C55A11", "7030A0"]
for i, ((col, name, _, _), sc_) in enumerate(zip(stages, stage_colors)):
    rr = 11 + i
    band = fill("F2F2F2") if i % 2 else None
    dash[f"A{rr}"] = name; dash[f"A{rr}"].font = F(b=True, color=sc_)
    dash[f"B{rr}"] = f'=COUNTIF({Q}!{col}2:{col}200,"Closed")'
    dash[f"C{rr}"] = f'=COUNTIF({Q}!{col}2:{col}200,"Open")'
    dash[f"D{rr}"] = f"=B{rr}+C{rr}"
    dash[f"E{rr}"] = f"=IF(D{rr}=0,0,B{rr}/D{rr})"; dash[f"E{rr}"].number_format = "0%"
    for c in "BCDE": dash[f"{c}{rr}"].font = F()
    if band:
        for c in "ABCDE": dash[f"{c}{rr}"].fill = band
dash.conditional_formatting.add("E11:E15", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="5B9BD5"))
dash["A22"] = "Closed (all phases)"; dash["B22"] = "=SUM(B11:B15)"
dash["A23"] = "Open (all phases)"; dash["B23"] = "=SUM(C11:C15)"
for c in ("A22", "B22", "A23", "B23"): dash[c].font = F(sz=9, color="808080")
dash.column_dimensions["A"].width = 18; dash.column_dimensions["B"].width = 13
dash.column_dimensions["E"].width = 14; dash.column_dimensions["F"].width = 6

d = DoughnutChart(); d.title = "Closed vs Open (all phases)"
d.add_data(Reference(dash, min_col=2, min_row=22, max_row=23), titles_from_data=False)
d.set_categories(Reference(dash, min_col=1, min_row=22, max_row=23))
d.height, d.width = 7.5, 9
dash.add_chart(d, "A25")
b = BarChart(); b.type = "col"; b.grouping = "stacked"; b.overlap = 100; b.title = "Topics by Phase"
b.add_data(Reference(dash, min_col=2, max_col=3, min_row=10, max_row=15), titles_from_data=True)
b.set_categories(Reference(dash, min_col=1, min_row=11, max_row=15))
b.height, b.width = 7.5, 12
dash.add_chart(b, "F25")

notes = ["HOW TO READ THIS DASHBOARD",
         "•  Version and Overall % Complete pull live from the Iteration Info block on the main sheet - no manual updates needed.",
         "•  Bottleneck Stage highlights whichever phase has the lowest % Complete right now, so you always know where attention is needed.",
         "•  The phase table and both charts recalculate automatically as topics move from Open to Closed on the main sheet."]
for i, n in enumerate(notes):
    rr = 42 + i
    dash.merge_cells(f"A{rr}:I{rr}"); dash[f"A{rr}"] = n
    dash[f"A{rr}"].font = F(sz=12, b=True, color="1F3864") if i == 0 else F(sz=10, color="404040")
    dash[f"A{rr}"].alignment = Alignment(wrap_text=True)

# ---------------- COA Findings ----------------
coa_rows = [
 ("F01", "Wrong drawer", "High", "5002-05-06 Others (Asset drawer)",
  "34 accounts with liability codes 3002-xx (private lenders, NBFCs, Kotak/Deutsche Bank loans, JSW One Finance) are created in the ASSET drawer.",
  "Loans appear as negative current assets; Balance Sheet understates both assets and liabilities.", "Sunil, Veena", "Move to Liabilities > 3002-07 Other Finances / 3002-01 Secured Loans; then lock 5002-05-06."),
 ("F02", "Duplicate loan accounts", "High", "3002-01-12 & 3002-01-15; 3002-01-10 & 3002-01-16; 3002-01-14 & 3002-01-18; 3002-01-13 & 3002-01-13-01", 
  "Same Kotak LAP, Deutsche Bank and JSW One Finance loans exist in more than one account (one of each pair in the Asset drawer or under Non-Current). A further 'Deutsche bank Loan A/c' (3002-02-06-08) sits under Trade Creditors - which loan it belongs to is unclear.",
  "Loan balances split across accounts - outstanding loan per lender cannot be read from any one report.", "Sunil, Veena", "One GL per loan; JE to merge balances; deactivate duplicates."),
 ("F03", "Duplicate bank account", "High", "5002-02-02-04 & 3002-01-11",
  "Kotak current account exists as a bank (asset) and again under 3002-01 Secured Loans codes.",
  "Bank reconciliation and cash position wrong.", "Veena", "Keep 5002-02-02-04; merge and deactivate 3002-01-11."),
 ("F04", "Blank account names", "Medium", "36 accounts (19 Asset, 7 Liability, 2 Revenue, 8 Expenditure)",
  "Accounts with codes but no name, e.g. 5002-01-01-14, -19, -21..-29 (inventory groups), 3002-03-02/05/07/08, 2003-07, 4004-07-14/31.",
  "Users cannot pick the right account; postings to unnamed accounts are invisible in reports.", "Sunil, Veena", "Name or deactivate; remove from training COA."),
 ("F05", "Orphan accounts (parent missing)", "Medium", "1001-01-01-01..03; 3003-09-03..08; 5002-04-07-01",
  "Share capital per shareholder has no 1001-01-01 parent; GST output/RCM payables coded 3003-09-xx sit under 3002-09 GST Payable; Advance Clearing coded 5002-04-07-01 sits under 5002-04-04.",
  "Account codes do not match their position in the tree - grouping in Trial Balance and Balance Sheet is unreliable.", "Sunil", "Re-code to match parent (e.g. 3002-09-03..08)."),
 ("F06", "Malformed codes", "Low", "3002007-35 Kumar Arts; 4004-4-08 Medical Insurance",
  "Codes break the segment pattern (missing hyphen / single-digit segment). Kumar Arts also exists correctly as 3002-07-35.",
  "Sorting and code-based reports misplace these accounts.", "Veena", "Merge Kumar Arts; re-code 4004-04-08."),
 ("F07", "GST payable scattered", "High", "3002-03-22/24/25/27; 3002-09-01/02; 3003-09-03..08",
  "IGST/CGST/SGST payable exist in Statutory Payables AND in GST Payable, with a separate 'GST PAYABLE' 3002-03-27.",
  "GST liability report never matches GSTR-3B; tax determination may post to different accounts.", "Sunil, Veena", "One output account per tax type under 3002-09; map in Tax Code determination."),
 ("F08", "TDS payable spread over 14 accounts", "High", "3002-03-03, -04, -10..-16, -18, -20, -21, -23, -26",
  "TDS split by rate AND by nature with overlaps: 'TDS on Rent' (3002-03-13) and 'TDS Payable on Rent' (3002-03-15); 1% / 2% / 0.75% / 1.5% rate accounts alongside section-wise ones.",
  "TDS payable per section (for challan/return) cannot be reported. Directly relevant to the TDS setup in the training DB.", "Sunil, Veena", "One account per TDS section (194C, 194J, 194I, 194Q, 194A, 192) mapped to Withholding Tax codes."),
 ("F09", "Duplicate WIP accounts", "Medium", "5002-01-01-15 & 5002-01-02",
  "Work-in-progress exists as an item-group account and as a separate WIP account.",
  "Production WIP split - production cost reports and inventory valuation disagree. Links to B1 inventory mismatch.", "Ashok, Sunil", "Use one WIP account in G/L account determination (Production)."),
 ("F10", "Duplicate expense heads", "Medium", "Rates & Taxes x4; Audit Fees x3; Professional Tax, Electrical Inspection, KIADB in both 4002 and 4004; LWF-MGT x2",
  "Same expense exists under Manufacturing (4002) and Administrative (4004) expenses, or twice in the same group.",
  "Same cost posted to different heads - P&L by function is inconsistent between periods.", "Sunil", "Keep one per function; deactivate the rest."),
 ("F11", "Misclassified accounts", "Medium", "5002-05-04-03 Suspense A/C; 5002-05-04-01 Income Tax Refund (under Investments); 3003-02 Conversion Expenses (under Provisions); 4004-07-22 Sale of FA Asset (under Expenses)",
  "Accounts sit under groups that do not describe them.", "Balance Sheet groups (Investments, Provisions) are overstated/misleading.", "Sunil", "Re-parent to the correct group."),
 ("F12", "Bank / loan numbers in account names", "Low", "26 accounts",
  "Full bank and loan account numbers are embedded in GL names.", "Exposes sensitive numbers on every report and printout.", "Sunil", "Store numbers in House Bank / remarks; keep names generic."),
 ("F13", "Spelling and naming errors", "Low", "e.g. 'Non Current Lability', 'Deautch bank', 'Fuels and Olis', 'Maintanence', 'Clearning', 'Distrubution', 'Benifit'",
  "Inconsistent spelling and case across the COA.", "Hard to search accounts; unprofessional reports.", "Veena", "Correct names during training-DB load."),
 ("F14", "Product sales posted to an unnamed account", "High", "2001-01-01 SALES-PRODUCT SALES; 2001-01-01-01 (no name)",
  "2001-01-01 is a title account; its only postable child 2001-01-01-01 has no name. Product sales revenue can only be posted to the unnamed account.",
  "The main revenue line of the P&L appears without a name; sales analysis by GL is unreadable.", "Sunil, Veena", "Name 2001-01-01-01 'Sales - Product Sales (Domestic)' and use it in G/L determination."),
]
heads = ["ID", "Issue Type", "Severity", "Accounts Affected", "Finding", "Impact on Reports", "Session / Audience", "Proposed Correction"]
widths = [6, 22, 10, 40, 60, 45, 16, 45]
coa["A1"] = "AKE Chart of Accounts - Findings (Spiral 1, Empathise/Define evidence for topic B2)"
coa["A1"].font = F(sz=13, b=True, color="1F3864")
coa["A2"] = "Source: AKE's real Chart of Accounts export (5 CSV files, 598 accounts), analysed 1 Oct 2026."
coa["A2"].font = F(sz=9, color="808080")
for i, (h, w) in enumerate(zip(heads, widths)):
    c = coa.cell(row=4, column=1 + i, value=h); c.font = F(b=True, color="FFFFFF"); c.fill = fill("404040")
    coa.column_dimensions[gl(1 + i)].width = w
sev = {"High": "FFC7CE", "Medium": "FFEB9C", "Low": "DDEBF7"}
for rr, row in enumerate(coa_rows, start=5):
    for i, v in enumerate(row):
        c = coa.cell(row=rr, column=1 + i, value=v); c.font = F()
        c.alignment = Alignment(wrap_text=True, vertical="top")
    coa.cell(row=rr, column=3).fill = fill(sev[row[2]])
coa.freeze_panes = "A5"
cr = 5 + len(coa_rows) + 1
coa[f"A{cr}"] = "Summary"; coa[f"A{cr}"].font = F(b=True)
for j, s in enumerate(["High", "Medium", "Low"]):
    coa[f"B{cr+1+j}"] = s; coa[f"C{cr+1+j}"] = f'=COUNTIF($C$5:$C${4+len(coa_rows)},B{cr+1+j})'
    coa[f"B{cr+1+j}"].font = F(); coa[f"C{cr+1+j}"].font = F()

# ---------------- How To Use ----------------
how.column_dimensions["A"].width = 110
lines = [("How to use this tracker (V1)", True), (None, False),
 ("This tracker follows the Qltc Project Tracking System format: each topic moves through Empathise -> Define -> Ideate -> Prototype -> Testing, each stage Open or Closed.", False),
 ("Spiral mapping (Qltc method deck): Empathise + Define = Q1 Determine Objectives; Ideate = Q1/Q2 Alternatives; Prototype = Q2/Q3 Resolve Risk & Build; Testing = Q4 Review & Plan Next Loop.", False),
 ("Topics are grouped into 4 sections: A) Customer & Training Scope, B) AKE Pain Points, C) Database Configuration & Data, D) Method & Delivery.", False),
 ("Empathise topics marked Closed carry answers already confirmed by Qltc on 1 Oct 2026. Open Empathise topics are genuine gaps that need answers before Spiral 1 can close.", False),
 ("Define cells starting with 'DRAFT:' are proposed problem statements written by Claude - Qltc reviews and changes the status to Closed when agreed.", False),
 ("The 'COA Findings' sheet is the evidence behind topic B2 (Finance reports) and will be used in Sunil and Veena's Finance session.", False),
 ("Status cells have a drop-down (Open / Closed); the Dashboard recalculates automatically.", False)]
for i, (t, bold) in enumerate(lines, start=1):
    if t:
        how[f"A{i}"] = t; how[f"A{i}"].font = F(sz=12 if bold else 11, b=bold)
        how[f"A{i}"].alignment = Alignment(wrap_text=True)

wb.save(OUT)
print("saved", OUT, "last topic row", LAST)
