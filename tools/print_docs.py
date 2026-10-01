"""Print formats (PDF) for every transaction posted in AKE_DEMO - read live from SAP B1 via Service Layer.

Run:  python tools/print_docs.py                 (all documents recorded in logs/txn_state.json)
      python tools/print_docs.py S4 P3          (documents of selected flows)
Output: prints/<Document type>/<number>.pdf

Formats: Sales Quotation, Sales Order, Delivery Challan, Tax Invoice, Receipt Voucher, Purchase Order,
Goods Receipt Note, Purchase Invoice, Purchase Credit Note, Goods Receipt, Goods Issue, Issue for Production,
Receipt from Production, Stock Transfer Note, Production Order (Job Card).
GST documents show HSN/SAC, CGST/SGST or IGST per line, an HSN summary, TDS (purchase) and the amount in words.
"""
import json, pathlib, re, sys
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

OUT = L.ROOT / "prints"
STATE = L.LOGS / "txn_state.json"

pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))      # Arial carries the Rupee sign
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
INK, LINE, SHADE = colors.HexColor("#1F2937"), colors.HexColor("#9CA3AF"), colors.HexColor("#E5EDF5")
S = {n: ParagraphStyle(n, fontName=f, fontSize=z, leading=z + 2.5, textColor=INK, alignment=a)
     for n, f, z, a in [("n", "Arial", 8, 0), ("b", "Arial-Bold", 8, 0), ("r", "Arial", 8, 2), ("rb", "Arial-Bold", 8, 2),
                        ("c", "Arial", 8, 1), ("h", "Arial-Bold", 14, 1), ("co", "Arial-Bold", 13, 0), ("s", "Arial", 7, 0)]}
P = lambda t, s="n": Paragraph(str(t if t is not None else ""), S[s])

# entity -> (title, party label, sales?)
MARKETING = {
    "Quotations": ("Sales Quotation", "Customer", True), "Orders": ("Sales Order", "Customer", True),
    "DeliveryNotes": ("Delivery Challan", "Consignee", True), "Invoices": ("Tax Invoice", "Bill To", True),
    "PurchaseOrders": ("Purchase Order", "Supplier", False), "PurchaseDeliveryNotes": ("Goods Receipt Note", "Supplier", False),
    "PurchaseInvoices": ("Purchase Invoice", "Supplier", False), "PurchaseCreditNotes": ("Purchase Credit Note", "Supplier", False),
}
BASE_ENTITY = {23: "Quotations", 17: "Orders", 15: "DeliveryNotes", 13: "Invoices", 22: "PurchaseOrders",
               20: "PurchaseDeliveryNotes", 18: "PurchaseInvoices", 202: "ProductionOrders"}
STATE_NAME = {code: (name, gst) for code, (name, gst) in L.STATES.items()}


# ------------------------------------------------------------------------------------------------ helpers
def inr(x):
    """Indian digit grouping: 12,34,567.89"""
    neg, x = x < 0, abs(round(x or 0, 2))
    whole, frac = f"{x:.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    head = ",".join(re.findall(r"\d{1,2}", head[::-1]))[::-1] if head else ""
    return ("-" if neg else "") + (f"{head},{tail}" if head else tail) + "." + frac


ONES = "Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen Sixteen " \
       "Seventeen Eighteen Nineteen".split()
TENS = "_ _ Twenty Thirty Forty Fifty Sixty Seventy Eighty Ninety".split()


def words(n):
    def two(n):
        return ONES[n] if n < 20 else TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    def three(n):
        return (ONES[n // 100] + " Hundred" + (" " + two(n % 100) if n % 100 else "")) if n >= 100 else two(n)
    parts = []
    for div, name in [(10 ** 7, "Crore"), (10 ** 5, "Lakh"), (1000, "Thousand")]:
        if n >= div:
            parts.append(f"{words(n // div) if n // div >= 1000 else three(n // div)} {name}")
            n %= div
    if n or not parts:
        parts.append(three(n))
    return " ".join(parts)


def amount_words(x):
    rupees, paise = int(round(x * 100)) // 100, int(round(x * 100)) % 100
    return f"Rupees {words(rupees)}" + (f" and {two_words(paise)} Paise" if paise else "") + " Only"


two_words = lambda p: words(p)
fdate = lambda d: datetime.fromisoformat(d[:10]).strftime("%d-%m-%Y") if d else ""


class Ctx:
    """Service Layer session + caches for series prefixes, items, HSN/SAC, partners, accounts."""

    def __init__(self):
        self.sl = L.SL(L.read_env(), False, lambda m: None)
        self.sl.login()
        self.c = {}
        admin = self.sl.s.post(f"{self.sl.base}/CompanyService_GetAdminInfo", timeout=60).json()
        loc = self.sl.get(f"WarehouseLocations({L.TDS_LOCATION})")
        st = STATE_NAME.get(loc["State"], (loc["State"], ""))
        self.company = {"name": admin["CompanyName"], "gstin": loc["GSTIN"], "pan": loc["PANNumber"],
                        "state": f"{st[0]} ({st[1]})",
                        "address": ", ".join(x for x in [loc["BuildingFloorRoom"], loc["Street"], loc["Block"],
                                                         f"{loc['City']} - {loc['ZipCode']}", st[0], "India"] if x)}

    def once(self, key, fn):
        if key not in self.c:
            self.c[key] = fn()
        return self.c[key]

    def prefix(self, series):
        return self.once(("ser", series), lambda: (self.sl.s.post(f"{self.sl.base}/SeriesService_GetSeries",
            json={"SeriesParams": {"Series": series}}, timeout=60).json().get("Prefix") or ""))

    def number(self, doc, num_field="DocNum"):
        pre = self.prefix(doc.get("Series"))
        return f"{pre}{doc[num_field]}" if pre else f"Primary-{doc[num_field]}"  # posted before the FY series existed

    def item(self, code):
        return self.once(("item", code), lambda: self.sl.get(f"Items('{code}')?$select=ItemName,InventoryUOM,ChapterID") or {})

    def hsn(self, entry):
        if not entry:
            return ""
        # B1 stores the HSN as '72.08.' - print the plain digits (7208)
        return self.once(("hsn", entry), lambda: re.sub(r"\D", "", (self.sl.get(f"IndiaHsn({entry})") or {}).get("ChapterID", "")))

    def sac(self, entry):
        if not entry:
            return ""
        return self.once(("sac", entry), lambda: (self.sl.get(f"IndiaSacCode({entry})") or {}).get("ServiceCode", ""))

    def bp(self, card):
        def load():
            b = self.sl.get(f"BusinessPartners('{card}')?$select=CardName,BPAddresses,FederalTaxID")
            addr = next((a for a in b["BPAddresses"] if a["AddressType"] == "bo_BillTo"), b["BPAddresses"][0] if b["BPAddresses"] else {})
            st = STATE_NAME.get(addr.get("State"), (addr.get("State") or "", ""))
            gstin = addr.get("GSTIN") or ""
            return {"name": b["CardName"], "city": addr.get("City") or "", "state": st[0], "code": st[1],
                    "gstin": gstin, "pan": gstin[2:12] if len(gstin) == 15 else ""}
        return self.once(("bp", card), load)

    def account(self, code):
        return self.once(("acct", code), lambda: (self.sl.get(f"ChartOfAccounts('{code}')?$select=Name") or {}).get("Name", code))

    def base_ref(self, lines):
        refs = []
        for bt, be in sorted({(l.get("BaseType"), l.get("BaseEntry")) for l in lines if l.get("BaseType") in BASE_ENTITY}):
            ent = BASE_ENTITY[bt]
            num = "DocumentNumber" if ent == "ProductionOrders" else "DocNum"
            d = self.once(("base", ent, be), lambda: self.sl.get(f"{ent}({be})?$select=Series,{num},DocDate" if ent != "ProductionOrders"
                                                                  else f"{ent}({be})?$select=Series,{num},PostingDate"))
            refs.append(self.number(d, num))
        return ", ".join(refs)


# ------------------------------------------------------------------------------------------------ building blocks
def grid(rows, widths, head_rows=1, right_from=None, bold_last=False, zebra=False):
    t = Table(rows, colWidths=widths, repeatRows=head_rows)
    st = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("BACKGROUND", (0, 0), (-1, head_rows - 1), SHADE), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if bold_last:
        st.append(("BACKGROUND", (0, -1), (-1, -1), SHADE))
    t.setStyle(TableStyle(st))
    return t


def letterhead(ctx, title, story):
    co = ctx.company
    story += [grid([[P(co["name"], "co")],
                    [P(co["address"])],
                    [P(f"<b>GSTIN:</b> {co['gstin']} &nbsp;&nbsp; <b>PAN:</b> {co['pan']} &nbsp;&nbsp; <b>State:</b> {co['state']}")]],
                   [535], head_rows=0),
              Spacer(1, 3 * mm), P(title.upper(), "h"), Spacer(1, 3 * mm)]


def info_block(left, right):
    """Two-column key/value block: party on the left, document data on the right."""
    l_rows = [[P(left[0][0], "b")]] + [[P(t)] for t in left[1:]]
    r_rows = [[P(k, "b"), P(v)] for k, v in right]
    return Table([[Table(l_rows, colWidths=[265]), Table(r_rows, colWidths=[90, 170])]], colWidths=[268, 267],
                 style=TableStyle([("BOX", (0, 0), (0, 0), 0.4, LINE), ("BOX", (1, 0), (1, 0), 0.4, LINE),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                                   ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))


def signatures(ctx, story, left="Prepared by", mid="Checked by", note=None):
    story += [Spacer(1, 4 * mm)]
    if note:
        story += [P(note, "s"), Spacer(1, 2 * mm)]
    story += [Table([[P(left), P(mid, "c"), P(f"For {ctx.company['name']}<br/><br/><br/>Authorised Signatory", "r")]],
                    colWidths=[178, 178, 179], style=TableStyle([("BOX", (0, 0), (-1, -1), 0.4, LINE),
                                                                 ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                                                                 ("TOPPADDING", (0, 0), (-1, -1), 18)])),
              Spacer(1, 2 * mm), P("This is a computer generated document from SAP Business One (AKE_DEMO).", "s")]


def split_tax(line):
    t = line.get("TaxTotal") or 0
    if (line.get("TaxCode") or "").startswith("IGST"):
        return 0, 0, t
    c = round(t / 2, 2)
    return c, round(t - c, 2), 0


# ------------------------------------------------------------------------------------------------ formats
def marketing(ctx, entity, d):
    title, party_label, sales = MARKETING[entity]
    if entity == "PurchaseInvoices" and d.get("WTAmount"):
        title = "Purchase Invoice (with TDS)"
    bp = ctx.bp(d["CardCode"])
    lines = d["DocumentLines"]
    service = d.get("DocType") == "dDocument_Service"
    igst = any((l.get("TaxCode") or "").startswith("IGST") for l in lines)
    story = []
    letterhead(ctx, title, story)
    right = [("Document No.", ctx.number(d)), ("Date", fdate(d["DocDate"])),
             ("Place of Supply", f"{bp['state']} ({bp['code']})" if sales else ctx.company["state"]),
             ("Reference", d.get("NumAtCard") or "")]
    base = ctx.base_ref(lines)
    if base:
        right.append(("Against", base))
    if entity == "PurchaseCreditNotes" and d.get("OriginalRefNo"):
        right.append(("Original Invoice", f"{d['OriginalRefNo']} dt. {fdate(d.get('OriginalRefDate'))}"))
    if d.get("DocDueDate") and entity in ("Invoices", "PurchaseInvoices", "Orders", "PurchaseOrders"):
        right.append(("Due / Delivery", fdate(d["DocDueDate"])))
    left = [(f"{party_label}: {d['CardCode']}",), f"<b>{bp['name']}</b>", f"{bp['city']}, {bp['state']}",
            f"GSTIN: {bp['gstin']} &nbsp; State Code: {bp['code']}", f"PAN: {bp['pan']}"]
    story += [info_block(left, right), Spacer(1, 3 * mm)]

    tax_cols = ["IGST"] if igst else ["CGST", "SGST"]
    head = ["#", "Item / Description", "SAC" if service else "HSN", "Qty", "UoM", "Rate", "Taxable", "GST %"] + tax_cols
    widths = [16, 150, 40, 36, 30, 52, 62, 30] + ([119] if igst else [59, 60])  # = 535 pt
    rows = [[P(h, "b") for h in head]]
    tot = {"taxable": 0, "CGST": 0, "SGST": 0, "IGST": 0}
    hsn_sum = {}
    for i, l in enumerate(lines, 1):
        c, s, g = split_tax(l)
        rate = l.get("TaxPercentagePerRow") or 0
        if service:
            code, desc, qty, uom, price = ctx.sac(l.get("SACEntry")), l.get("ItemDescription"), "", "", ""
        else:
            it = ctx.item(l["ItemCode"])
            code = ctx.hsn(l.get("HSNEntry") or it.get("ChapterID"))
            desc = f"<b>{l['ItemCode']}</b><br/>{l.get('ItemDescription') or it.get('ItemName', '')}"
            qty, uom, price = f"{l['Quantity']:g}", l.get("MeasureUnit") or it.get("InventoryUOM", ""), inr(l.get("Price") or l.get("UnitPrice"))
        tx = l.get("LineTotal") or 0
        vals = [inr(g)] if igst else [inr(c), inr(s)]
        rows.append([P(i, "c"), P(desc), P(code, "c"), P(qty, "r"), P(uom, "c"), P(price, "r"), P(inr(tx), "r"),
                     P(f"{rate:g}%", "c")] + [P(v, "r") for v in vals])
        tot["taxable"] += tx; tot["CGST"] += c; tot["SGST"] += s; tot["IGST"] += g
        h = hsn_sum.setdefault((code, rate), [0, 0, 0, 0])
        h[0] += tx; h[1] += c; h[2] += s; h[3] += g
    story.append(grid(rows, widths))

    # totals
    gross = tot["taxable"] + tot["CGST"] + tot["SGST"] + tot["IGST"]
    trows = [["Taxable Value", inr(tot["taxable"])]]
    trows += [["IGST", inr(tot["IGST"])]] if igst else [["CGST", inr(tot["CGST"])], ["SGST", inr(tot["SGST"])]]
    if d.get("WTAmount"):
        wt = d.get("WithholdingTaxDataCollection") or [{}]
        trows += [["Invoice Value", inr(gross)], [f"Less: TDS {wt[0].get('WTCode', '')}", f"-{inr(d['WTAmount'])}"]]
    if d.get("RoundingDiffAmount"):
        trows.append(["Rounding", inr(d["RoundingDiffAmount"])])
    trows.append(["Net Payable" if d.get("WTAmount") else "Grand Total", f"₹ {inr(d['DocTotal'])}"])
    total_tbl = grid([[P(a, "b"), P(b, "rb")] for a, b in trows], [100, 90], head_rows=0, bold_last=True)
    words_tbl = Table([[P("<b>Amount in words:</b><br/>" + amount_words(d["DocTotal"]))]], colWidths=[335],
                      style=TableStyle([("BOX", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [Spacer(1, 2 * mm), Table([[words_tbl, total_tbl]], colWidths=[343, 192],
                                       style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))]

    # HSN / SAC summary for tax documents
    if entity in ("Invoices", "PurchaseInvoices", "PurchaseCreditNotes"):
        hh = ["SAC" if service else "HSN", "GST %", "Taxable"] + tax_cols + ["Total Tax"]
        hr = [[P(x, "b") for x in hh]]
        for (code, rate), (tx, c, s, g) in sorted(hsn_sum.items()):
            hr.append([P(code, "c"), P(f"{rate:g}%", "c"), P(inr(tx), "r")] +
                      ([P(inr(g), "r")] if igst else [P(inr(c), "r"), P(inr(s), "r")]) + [P(inr(c + s + g), "r")])
        story += [Spacer(1, 3 * mm), P("HSN / SAC Summary", "b"), Spacer(1, 1 * mm),
                  grid(hr, [70, 45, 110] + ([110] if igst else [80, 80]) + ([200] if igst else [150]))]

    note = d.get("Comments") or ""
    if entity == "Invoices":
        note = ("Declaration: We declare that this invoice shows the actual price of the goods described and that all "
                "particulars are true and correct. " + note)
    if entity == "DeliveryNotes":
        note = "Goods dispatched for supply against the referenced sales order. Tax invoice follows. " + note
    signatures(ctx, story, "Receiver's Signature" if sales and entity in ("DeliveryNotes", "Invoices") else "Prepared by",
               "Checked by", note)
    return title, ctx.number(d), story


def receipt(ctx, entity, d):
    bp = ctx.bp(d["CardCode"])
    story = []
    letterhead(ctx, "Receipt Voucher", story)
    right = [("Receipt No.", ctx.number(d)), ("Date", fdate(d["DocDate"])),
             ("Mode", "Bank Transfer (NEFT/RTGS)" if d.get("TransferSum") else "Cash/Cheque"),
             ("Transfer Ref.", d.get("TransferReference") or ""),
             ("Bank", f"{d.get('TransferAccount', '')} {ctx.account(d['TransferAccount']) if d.get('TransferAccount') else ''}")]
    left = [(f"Received from: {d['CardCode']}",), f"<b>{bp['name']}</b>", f"{bp['city']}, {bp['state']}", f"GSTIN: {bp['gstin']}"]
    story += [info_block(left, right), Spacer(1, 3 * mm)]
    rows = [[P(h, "b") for h in ["#", "Against Invoice", "Invoice Date", "Invoice Amount", "Amount Received"]]]
    for i, pi in enumerate(d.get("PaymentInvoices") or [], 1):
        inv = ctx.sl.get(f"Invoices({pi['DocEntry']})?$select=Series,DocNum,DocDate,DocTotal")
        rows.append([P(i, "c"), P(ctx.number(inv)), P(fdate(inv["DocDate"]), "c"), P(inr(inv["DocTotal"]), "r"), P(inr(pi["SumApplied"]), "r")])
    amt = d.get("TransferSum") or d.get("CashSum") or 0
    rows.append([P(""), P("Total", "b"), P(""), P(""), P(f"₹ {inr(amt)}", "rb")])
    story += [grid(rows, [20, 175, 90, 125, 125], bold_last=True), Spacer(1, 3 * mm),
              P(f"<b>Amount in words:</b> {amount_words(amt)}")]
    signatures(ctx, story, "Received by", "Checked by", d.get("Remarks"))
    return "Receipt Voucher", ctx.number(d), story


def inventory(ctx, entity, d):
    lines = d.get("DocumentLines") or d.get("StockTransferLines") or []
    prod = any(l.get("BaseType") == 202 for l in lines)
    title = {"InventoryGenEntries": "Receipt from Production" if prod else "Goods Receipt",
             "InventoryGenExits": "Issue for Production" if prod else "Goods Issue",
             "StockTransfers": "Stock Transfer Note"}[entity]
    story = []
    letterhead(ctx, title, story)
    right = [("Document No.", ctx.number(d)), ("Date", fdate(d["DocDate"]))]
    if entity == "StockTransfers":
        right += [("From Warehouse", d.get("FromWarehouse")), ("To Warehouse", d.get("ToWarehouse"))]
    base = ctx.base_ref(lines)
    if base:
        right.append(("Production Order", base))
    if d.get("Reference2"):
        right.append(("Reference", d["Reference2"]))
    left = [("Purpose",), d.get("Comments") or title, f"Location: {ctx.company['address']}"]
    story += [info_block(left, right), Spacer(1, 3 * mm)]
    transfer = entity == "StockTransfers"
    head = ["#", "Item Code", "Description", "UoM", "Qty"] + (["From", "To"] if transfer else ["Warehouse", "Rate", "Value"])
    widths = [18, 95, 190, 35, 52] + ([72, 73] if transfer else [55, 40, 50])
    if not transfer:
        widths = [18, 92, 170, 35, 50, 55, 55, 60]
    rows = [[P(h, "b") for h in head]]
    total_qty = total_val = 0
    for i, l in enumerate(lines, 1):
        it = ctx.item(l["ItemCode"])
        qty = l["Quantity"]
        cells = [P(i, "c"), P(l["ItemCode"]), P(l.get("ItemDescription") or it.get("ItemName", "")),
                 P(it.get("InventoryUOM", ""), "c"), P(f"{qty:g}", "r")]
        if transfer:
            cells += [P(l.get("FromWarehouseCode"), "c"), P(l.get("WarehouseCode"), "c")]
        else:
            price = l.get("Price") or l.get("UnitPrice") or 0
            val = l.get("LineTotal") or price * qty
            cells += [P(l.get("WarehouseCode"), "c"), P(inr(price) if price else "", "r"), P(inr(val) if val else "", "r")]
            total_val += val
        total_qty += qty
        rows.append(cells)
    if not transfer and total_val:
        rows.append([P("")] * 7 + [P(f"₹ {inr(total_val)}", "rb")])
    story.append(grid(rows, widths, bold_last=not transfer and bool(total_val)))
    signatures(ctx, story, "Issued / Received by", "Store In-charge")
    return title, ctx.number(d), story


def production_order(ctx, entity, d):
    story = []
    letterhead(ctx, "Production Order / Job Card", story)
    it = ctx.item(d["ItemNo"])
    status = {"boposPlanned": "Planned", "boposReleased": "Released", "boposClosed": "Closed", "boposCancelled": "Cancelled"}
    right = [("Order No.", ctx.number(d, "DocumentNumber")), ("Order Date", fdate(d.get("PostingDate"))),
             ("Due Date", fdate(d.get("DueDate"))), ("Status", status.get(d.get("ProductionOrderStatus"), d.get("ProductionOrderStatus"))),
             ("Type", "Standard")]
    left = [("Product",), f"<b>{d['ItemNo']}</b>", it.get("ItemName", ""),
            f"Planned: {d['PlannedQuantity']:g} {it.get('InventoryUOM', '')} &nbsp; Completed: {d.get('CompletedQuantity', 0):g}",
            f"Receipt warehouse: {d.get('Warehouse', '')}"]
    story += [info_block(left, right), Spacer(1, 3 * mm), P("Components and Resources", "b"), Spacer(1, 1 * mm)]
    rows = [[P(h, "b") for h in ["#", "Code", "Description", "Type", "Base Qty", "Planned", "Issued", "Whse"]]]
    for i, l in enumerate(d["ProductionOrderLines"], 1):
        res = l.get("ItemType") == "pit_Resource"
        name = l.get("ItemName") or ("" if res else ctx.item(l["ItemNo"]).get("ItemName", ""))
        rows.append([P(i, "c"), P(l["ItemNo"]), P(name), P("Resource (hrs)" if res else "Material", "c"),
                     P(f"{l.get('BaseQuantity', 0):g}", "r"), P(f"{l.get('PlannedQuantity', 0):g}", "r"),
                     P(f"{l.get('IssuedQuantity', 0):g}", "r"), P(l.get("Warehouse") or "", "c")])
    story.append(grid(rows, [18, 92, 160, 62, 48, 50, 50, 55]))
    signatures(ctx, story, "Production Supervisor", "Quality Check", d.get("Remarks"))
    return "Production Order", ctx.number(d, "DocumentNumber"), story


def render(ctx, entity, entry):
    d = ctx.sl.get(f"{entity}({entry})")
    if entity in MARKETING:
        title, number, story = marketing(ctx, entity, d)
    elif entity == "IncomingPayments":
        title, number, story = receipt(ctx, entity, d)
    elif entity == "ProductionOrders":
        title, number, story = production_order(ctx, entity, d)
    else:
        title, number, story = inventory(ctx, entity, d)
    folder = OUT / title.split(" (")[0]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (re.sub(r"[^\w-]+", "-", number).strip("-") + ".pdf")
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=30, rightMargin=30, topMargin=28, bottomMargin=28,
                            title=f"{title} {number}", author=ctx.company["name"])
    doc.build(story, onLaterPages=page_no, onFirstPage=page_no)
    return title, number, path


def page_no(canvas, doc):
    canvas.setFont("Arial", 7)
    canvas.drawRightString(A4[0] - 30, 16, f"Page {doc.page}")


def main():
    state = json.loads(STATE.read_text())
    want = sys.argv[1:]
    seen = set()
    ctx = Ctx()
    for key, rec in state.items():
        if "Entity" not in rec or (want and key.split("-")[0] not in want):
            continue
        k = (rec["Entity"], rec["DocEntry"])
        if k in seen:
            continue
        seen.add(k)
        title, number, path = render(ctx, *k)
        print(f"OK   {key:16s} {title:28s} {number:18s} {path.relative_to(L.ROOT)}")


if __name__ == "__main__":
    main()
