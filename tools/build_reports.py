"""Query Manager report pack for AKE_DEMO: categories OTC, PTP, PTS, FICO with HANA SQL reports.

Run:  python tools/build_reports.py --test     (run every report against AKE_DEMO via Service Layer, save nothing)
      python tools/build_reports.py --no-test  (save without testing; test each report in the SAP client)
      python tools/build_reports.py            (test, then create/update the categories and saved queries)
In SAP: Tools -> Queries -> Query Manager -> OTC / PTP / PTS / FICO. Date-range reports prompt for From / To date
([%0] / [%1]); the GL ledger also asks for the account ([%2]).
"""
import argparse, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sl_loader as L

# OTC = Order to Cash, PTP = Procure to Pay, PTS = Plan to Stock (production & inventory), FICO = Finance & Controlling
CATEGORIES = {"OTC": "OTC", "PTP": "PTP", "PTS": "PTS", "FICO": "FICO"}
TEST_PARAMS = {"[%0]": "'2026-04-01'", "[%1]": "'2027-03-31'", "[%2]": "'3002-02-01'"}

NO = lambda t, n="N": f'IFNULL({n}."BeginStr", \'\') || TO_NVARCHAR({t}."DocNum")'      # series prefix + number
DATES = lambda t, col="DocDate": f'{t}."{col}" >= [%0] AND {t}."{col}" <= [%1]'
CGST = lambda l: f'CASE WHEN {l}."TaxCode" LIKE \'CG+SG%\' THEN {l}."VatSum" / 2 ELSE 0 END'
IGST = lambda l: f'CASE WHEN {l}."TaxCode" LIKE \'IGST%\' THEN {l}."VatSum" ELSE 0 END'

REPORTS = [
    # ---------------------------------------------------------------------------------------------- OTC
    ("OTC", "OTC01 Sales Quotation Register", f'''
SELECT {NO("T0")} AS "Quotation No", T0."DocDate" AS "Date", T0."CardCode" AS "Customer", T0."CardName" AS "Customer Name",
       T0."DocTotal" - T0."VatSum" AS "Taxable", T0."VatSum" AS "GST", T0."DocTotal" AS "Total",
       CASE T0."DocStatus" WHEN 'O' THEN 'Open' ELSE 'Closed (converted)' END AS "Status"
FROM "OQUT" T0 LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum"'''),
    ("OTC", "OTC02 Open Sales Orders - Pending Delivery", f'''
SELECT {NO("T0")} AS "SO No", T0."DocDate" AS "SO Date", T1."ShipDate" AS "Delivery Date", T0."CardName" AS "Customer",
       T1."ItemCode" AS "Item", T1."Dscription" AS "Description", T1."Quantity" AS "Ordered", T1."Quantity" - T1."OpenQty" AS "Delivered",
       T1."OpenQty" AS "Pending Qty", T1."Price" AS "Rate", T1."OpenQty" * T1."Price" AS "Pending Value", T1."WhsCode" AS "Whse"
FROM "ORDR" T0 INNER JOIN "RDR1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T1."LineStatus" = 'O' AND T0."CANCELED" = 'N' ORDER BY T1."ShipDate", T0."DocNum"'''),
    ("OTC", "OTC03 Pending Deliveries to Invoice", f'''
SELECT {NO("T0")} AS "Delivery No", T0."DocDate" AS "Date", T0."CardName" AS "Customer", T1."ItemCode" AS "Item",
       T1."Dscription" AS "Description", T1."OpenQty" AS "Qty to Invoice", T1."Price" AS "Rate",
       T1."OpenQty" * T1."Price" AS "Value to Invoice", T1."TaxCode" AS "Tax Code"
FROM "ODLN" T0 INNER JOIN "DLN1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T1."LineStatus" = 'O' AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum"'''),
    ("OTC", "OTC04 Sales Register (GST)", f'''
SELECT {NO("T0")} AS "Invoice No", T0."DocDate" AS "Date", T0."CardCode" AS "Customer", T0."CardName" AS "Customer Name",
       C."GSTRegnNo" AS "Customer GSTIN", T1."ItemCode" AS "Item", T1."Dscription" AS "Description", H."ChapterID" AS "HSN",
       T1."Quantity" AS "Qty", T1."Price" AS "Rate", T1."LineTotal" AS "Taxable", T1."TaxCode" AS "Tax Code",
       {CGST("T1")} AS "CGST", {CGST("T1")} AS "SGST", {IGST("T1")} AS "IGST", T1."LineTotal" + T1."VatSum" AS "Line Total"
FROM "OINV" T0 INNER JOIN "INV1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
LEFT JOIN "OCHP" H ON H."AbsEntry" = T1."HsnEntry"
LEFT JOIN "CRD1" C ON C."CardCode" = T0."CardCode" AND C."AdresType" = 'B' AND C."Address" = T0."PayToCode"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum", T1."LineNum"'''),
    ("OTC", "OTC05 Customer Outstanding & Ageing", f'''
SELECT T0."CardCode" AS "Customer", T0."CardName" AS "Customer Name", {NO("T0")} AS "Invoice No", T0."DocDate" AS "Invoice Date",
       T0."DocDueDate" AS "Due Date", T0."DocTotal" AS "Invoice Amount", T0."PaidToDate" AS "Received",
       T0."DocTotal" - T0."PaidToDate" AS "Outstanding", DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) AS "Days Overdue",
       CASE WHEN DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) <= 0 THEN 'Not due'
            WHEN DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) <= 30 THEN '1-30'
            WHEN DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) <= 60 THEN '31-60'
            WHEN DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) <= 90 THEN '61-90' ELSE '90+' END AS "Ageing Bucket"
FROM "OINV" T0 LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T0."DocStatus" = 'O' AND T0."CANCELED" = 'N' ORDER BY T0."CardCode", T0."DocDueDate"'''),
    ("OTC", "OTC06 Incoming Payments Register", f'''
SELECT {NO("T0")} AS "Receipt No", T0."DocDate" AS "Date", T0."CardCode" AS "Customer", T0."CardName" AS "Customer Name",
       T0."TrsfrAcct" AS "Bank Account", T0."TrsfrRef" AS "Transfer Ref", T0."CashSum" AS "Cash", T0."TrsfrSum" AS "Bank Transfer",
       T0."DocTotal" AS "Total Received", T0."Comments" AS "Remarks"
FROM "ORCT" T0 LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."Canceled" = 'N' ORDER BY T0."DocDate", T0."DocNum"'''),
    ("OTC", "OTC07 Item-wise Sales Summary", f'''
SELECT T1."ItemCode" AS "Item", MAX(T1."Dscription") AS "Description", SUM(T1."Quantity") AS "Qty Sold",
       SUM(T1."LineTotal") AS "Sales Value", SUM(T1."VatSum") AS "GST", SUM(T1."GrssProfit") AS "Gross Profit",
       CASE WHEN SUM(T1."LineTotal") = 0 THEN 0 ELSE ROUND(SUM(T1."GrssProfit") * 100 / SUM(T1."LineTotal"), 2) END AS "GP %"
FROM "OINV" T0 INNER JOIN "INV1" T1 ON T1."DocEntry" = T0."DocEntry"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' GROUP BY T1."ItemCode" ORDER BY SUM(T1."LineTotal") DESC'''),
    ("OTC", "OTC08 Open Sales Quotations", f'''
SELECT {NO("T0")} AS "Quotation No", T0."DocDate" AS "Date", T0."DocDueDate" AS "Valid Until",
       DAYS_BETWEEN(CURRENT_DATE, T0."DocDueDate") AS "Days to Expiry", T0."CardCode" AS "Customer",
       T0."CardName" AS "Customer Name", T1."ItemCode" AS "Item", T1."Dscription" AS "Description", T1."Quantity" AS "Qty",
       T1."unitMsr" AS "UoM", T1."OpenQty" AS "Open Qty", T1."Price" AS "Rate", T1."OpenQty" * T1."Price" AS "Open Value"
FROM "OQUT" T0 INNER JOIN "QUT1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T1."LineStatus" = 'O' AND T0."CANCELED" = 'N' ORDER BY T0."DocDueDate", T0."DocNum"'''),
    ("OTC", "OTC09 Sales Order Register", f'''
SELECT {NO("T0")} AS "SO No", T0."DocDate" AS "SO Date", T0."DocDueDate" AS "Delivery Date", T0."NumAtCard" AS "Customer PO",
       T0."CardCode" AS "Customer", T0."CardName" AS "Customer Name", T0."DocTotal" - T0."VatSum" AS "Taxable",
       T0."VatSum" AS "GST", T0."DocTotal" AS "Total",
       CASE T0."DocStatus" WHEN 'O' THEN 'Open' ELSE 'Closed' END AS "Status"
FROM "ORDR" T0 LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum"'''),
    ("OTC", "OTC10 Sales Order vs Delivery", f'''
SELECT {NO("T0")} AS "SO No", T0."DocDate" AS "SO Date", T0."CardName" AS "Customer", T1."ItemCode" AS "Item",
       T1."Quantity" AS "SO Qty", T1."unitMsr" AS "UoM", IFNULL(D."BeginStr", '') || TO_NVARCHAR(G."DocNum") AS "Delivery No",
       G."DocDate" AS "Delivery Date", GL."Quantity" AS "Delivered Qty", T1."OpenQty" AS "Open Qty Now",
       CASE T0."DocStatus" WHEN 'O' THEN 'Open' ELSE 'Closed' END AS "SO Status"
FROM "ORDR" T0 INNER JOIN "RDR1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
LEFT JOIN "DLN1" GL ON GL."BaseType" = 17 AND GL."BaseEntry" = T1."DocEntry" AND GL."BaseLine" = T1."LineNum"
LEFT JOIN "ODLN" G ON G."DocEntry" = GL."DocEntry" AND G."CANCELED" = 'N' LEFT JOIN "NNM1" D ON D."Series" = G."Series"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocNum", T1."LineNum", G."DocNum"'''),
    ("OTC", "OTC11 Open Sales Orders - Summary", f'''
SELECT {NO("T0")} AS "SO No", T0."DocDate" AS "SO Date", T0."DocDueDate" AS "Delivery Date", T0."CardCode" AS "Customer",
       T0."CardName" AS "Customer Name", T0."DocTotal" AS "SO Value (incl. GST)", SUM(T1."LineTotal") AS "Taxable Value",
       SUM((T1."Quantity" - T1."OpenQty") * T1."Price") AS "Delivered Value", SUM(T1."OpenQty" * T1."Price") AS "Pending Value",
       DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) AS "Days Overdue"
FROM "ORDR" T0 INNER JOIN "RDR1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T0."DocStatus" = 'O' AND T0."CANCELED" = 'N'
GROUP BY N."BeginStr", T0."DocNum", T0."DocDate", T0."DocDueDate", T0."CardCode", T0."CardName", T0."DocTotal"
ORDER BY T0."DocDueDate", T0."DocNum"'''),
    ("OTC", "OTC12 A/R Credit Memo Register", f'''
SELECT {NO("T0")} AS "Credit Memo No", T0."DocDate" AS "Date", T0."CardCode" AS "Customer", T0."CardName" AS "Customer Name",
       T1."BaseRef" AS "Base Invoice / Return", T1."ItemCode" AS "Item", T1."Dscription" AS "Description",
       T1."Quantity" AS "Qty", T1."unitMsr" AS "UoM", T1."WhsCode" AS "Return Whse", T1."LineTotal" AS "Taxable",
       T1."TaxCode" AS "Tax Code", {CGST("T1")} AS "CGST", {CGST("T1")} AS "SGST", {IGST("T1")} AS "IGST",
       T1."LineTotal" + T1."VatSum" AS "Line Total", T0."Comments" AS "Reason"
FROM "ORIN" T0 INNER JOIN "RIN1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum", T1."LineNum"'''),
    # ---------------------------------------------------------------------------------------------- PTP
    ("PTP", "PTP01 Open Purchase Orders - Pending GRPO", f'''
SELECT {NO("T0")} AS "PO No", T0."DocDate" AS "PO Date", T1."ShipDate" AS "Expected", T0."CardName" AS "Vendor",
       T1."ItemCode" AS "Item", T1."Dscription" AS "Description", T1."Quantity" AS "Ordered", T1."Quantity" - T1."OpenQty" AS "Received",
       T1."OpenQty" AS "Pending Qty", T1."Price" AS "Rate", T1."OpenQty" * T1."Price" AS "Pending Value", T1."WhsCode" AS "Whse"
FROM "OPOR" T0 INNER JOIN "POR1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T1."LineStatus" = 'O' AND T0."CANCELED" = 'N' ORDER BY T1."ShipDate", T0."DocNum"'''),
    ("PTP", "PTP02 GRPO Pending Invoice (GRNI)", f'''
SELECT {NO("T0")} AS "GRPO No", T0."DocDate" AS "Date", T0."CardName" AS "Vendor", T1."ItemCode" AS "Item",
       T1."Dscription" AS "Description", T1."OpenQty" AS "Qty not Invoiced", T1."Price" AS "Rate",
       T1."OpenQty" * T1."Price" AS "GRNI Value", DAYS_BETWEEN(T0."DocDate", CURRENT_DATE) AS "Days Pending"
FROM "OPDN" T0 INNER JOIN "PDN1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T1."LineStatus" = 'O' AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum"'''),
    ("PTP", "PTP03 Purchase Register (GST)", f'''
SELECT {NO("T0")} AS "Invoice No", T0."DocDate" AS "Date", T0."NumAtCard" AS "Vendor Ref", T0."CardCode" AS "Vendor",
       T0."CardName" AS "Vendor Name", C."GSTRegnNo" AS "Vendor GSTIN",
       CASE WHEN T0."DocType" = 'S' THEN T1."Dscription" ELSE T1."ItemCode" END AS "Item / Service",
       IFNULL(H."ChapterID", S."ServCode") AS "HSN/SAC", T1."Quantity" AS "Qty", T1."LineTotal" AS "Taxable", T1."TaxCode" AS "Tax Code",
       {CGST("T1")} AS "CGST", {CGST("T1")} AS "SGST", {IGST("T1")} AS "IGST", T1."LineTotal" + T1."VatSum" AS "Line Total"
FROM "OPCH" T0 INNER JOIN "PCH1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
LEFT JOIN "OCHP" H ON H."AbsEntry" = T1."HsnEntry" LEFT JOIN "OSAC" S ON S."AbsEntry" = T1."SacEntry"
LEFT JOIN "CRD1" C ON C."CardCode" = T0."CardCode" AND C."AdresType" = 'B' AND C."Address" = T0."PayToCode"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum", T1."LineNum"'''),
    ("PTP", "PTP04 TDS Deducted Register", f'''
SELECT {NO("T0")} AS "Invoice No", T0."DocDate" AS "Date", T0."CardCode" AS "Vendor", T0."CardName" AS "Vendor Name",
       W."WTCode" AS "TDS Code", X."WTName" AS "Description", W."Rate" AS "Rate %", W."TaxbleAmnt" AS "Taxable",
       W."WTAmnt" AS "TDS Amount", X."Account" AS "TDS Payable Account"
FROM "OPCH" T0 INNER JOIN "PCH5" W ON W."AbsEntry" = T0."DocEntry" LEFT JOIN "OWHT" X ON X."WTCode" = W."WTCode"
LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum"'''),
    ("PTP", "PTP05 Vendor Outstanding & Ageing", f'''
SELECT T0."CardCode" AS "Vendor", T0."CardName" AS "Vendor Name", {NO("T0")} AS "Invoice No", T0."NumAtCard" AS "Vendor Ref",
       T0."DocDate" AS "Invoice Date", T0."DocDueDate" AS "Due Date", T0."DocTotal" AS "Invoice Amount (net of TDS)",
       T0."PaidToDate" AS "Paid", T0."DocTotal" - T0."PaidToDate" AS "Outstanding",
       DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) AS "Days Overdue",
       CASE WHEN DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) <= 0 THEN 'Not due'
            WHEN DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) <= 30 THEN '1-30'
            WHEN DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) <= 60 THEN '31-60'
            WHEN DAYS_BETWEEN(T0."DocDueDate", CURRENT_DATE) <= 90 THEN '61-90' ELSE '90+' END AS "Ageing Bucket"
FROM "OPCH" T0 LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T0."DocStatus" = 'O' AND T0."CANCELED" = 'N' ORDER BY T0."CardCode", T0."DocDueDate"'''),
    ("PTP", "PTP06 Outgoing Payments Register", f'''
SELECT {NO("T0")} AS "Payment No", T0."DocDate" AS "Date", T0."CardCode" AS "Vendor", T0."CardName" AS "Vendor Name",
       T0."TrsfrAcct" AS "Bank Account", T0."TrsfrRef" AS "Transfer Ref", T0."CashSum" AS "Cash", T0."TrsfrSum" AS "Bank Transfer",
       T0."DocTotal" AS "Total Paid", T0."Comments" AS "Remarks"
FROM "OVPM" T0 LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."Canceled" = 'N' ORDER BY T0."DocDate", T0."DocNum"'''),
    ("PTP", "PTP07 Vendor-wise Purchase Summary", f'''
SELECT T0."CardCode" AS "Vendor", MAX(T0."CardName") AS "Vendor Name", COUNT(DISTINCT T0."DocEntry") AS "Invoices",
       SUM(T0."DocTotal" - T0."VatSum" + T0."WTSum") AS "Taxable", SUM(T0."VatSum") AS "GST", SUM(T0."WTSum") AS "TDS",
       SUM(T0."DocTotal") AS "Net Payable"
FROM "OPCH" T0 WHERE {DATES("T0")} AND T0."CANCELED" = 'N' GROUP BY T0."CardCode" ORDER BY SUM(T0."DocTotal") DESC'''),
    ("PTP", "PTP08 Purchase Quotation Comparison", f'''
SELECT T1."ItemCode" AS "Item", T1."Dscription" AS "Description", T0."DocNum" AS "PQ No", T0."DocDate" AS "PQ Date",
       T0."CardCode" AS "Vendor", T0."CardName" AS "Vendor Name", T1."Quantity" AS "Qty", T1."unitMsr" AS "UoM",
       T1."Price" AS "Rate", T1."LineTotal" AS "Net", T1."VatSum" AS "GST", T1."LineTotal" + T1."VatSum" AS "Total",
       T1."ShipDate" AS "Delivery Date", T0."DocDueDate" AS "Valid Until", T1."BaseRef" AS "Purchase Request",
       T0."DocStatus" AS "Status"
FROM "OPQT" T0 INNER JOIN "PQT1" T1 ON T1."DocEntry" = T0."DocEntry"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T1."ItemCode", T1."Price", T1."ShipDate"'''),
    ("PTP", "PTP09 PO Receipt Status by GRPO", f'''
SELECT T0."DocNum" AS "PO No", T0."DocDate" AS "PO Date", T0."CardName" AS "Vendor", T1."ItemCode" AS "Item",
       T1."Quantity" AS "PO Qty", T1."unitMsr" AS "UoM", G."DocNum" AS "GRPO No", G."DocDate" AS "GRPO Date",
       GL."Quantity" AS "GRPO Qty", T1."OpenQty" AS "Open Qty Now", T0."DocStatus" AS "PO Status"
FROM "OPOR" T0 INNER JOIN "POR1" T1 ON T1."DocEntry" = T0."DocEntry"
LEFT JOIN "PDN1" GL ON GL."BaseType" = 22 AND GL."BaseEntry" = T1."DocEntry" AND GL."BaseLine" = T1."LineNum"
LEFT JOIN "OPDN" G ON G."DocEntry" = GL."DocEntry"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocNum", T1."LineNum", G."DocNum"'''),
    ("PTP", "PTP10 Open Purchase Requests", f'''
SELECT {NO("T0")} AS "PR No", T0."DocDate" AS "PR Date", T0."ReqName" AS "Requester", T1."PQTReqDate" AS "Required By",
       T1."ItemCode" AS "Item", T1."Dscription" AS "Description", T1."Quantity" AS "Requested", T1."unitMsr" AS "UoM",
       T1."OpenQty" AS "Open Qty", T1."LineVendor" AS "Preferred Vendor", T1."WhsCode" AS "Whse",
       DAYS_BETWEEN(T0."DocDate", CURRENT_DATE) AS "Days Open", T0."Comments" AS "Remarks"
FROM "OPRQ" T0 INNER JOIN "PRQ1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T1."LineStatus" = 'O' AND T0."CANCELED" = 'N' ORDER BY T1."PQTReqDate", T0."DocNum"'''),
    ("PTP", "PTP11 GRPO Register", f'''
SELECT {NO("T0")} AS "GRPO No", T0."DocDate" AS "GRPO Date", T0."NumAtCard" AS "Vendor DC / Ref", T0."CardCode" AS "Vendor",
       T0."CardName" AS "Vendor Name", T1."BaseRef" AS "PO No", T1."ItemCode" AS "Item", T1."Dscription" AS "Description",
       T1."Quantity" AS "Qty Received", T1."unitMsr" AS "UoM", T1."WhsCode" AS "Whse", T1."Price" AS "Rate",
       T1."LineTotal" AS "Taxable", T1."VatSum" AS "GST", T1."LineTotal" + T1."VatSum" AS "Line Total",
       CASE T1."LineStatus" WHEN 'O' THEN T1."OpenQty" ELSE 0 END AS "Qty not Invoiced",
       CASE T1."LineStatus" WHEN 'O' THEN 'Pending invoice' ELSE 'Invoiced / closed' END AS "Status"
FROM "OPDN" T0 INNER JOIN "PDN1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum", T1."LineNum"'''),
    ("PTP", "PTP12 A/P Credit Memo Register", f'''
SELECT {NO("T0")} AS "Credit Memo No", T0."DocDate" AS "Date", T0."NumAtCard" AS "Vendor Ref", T0."CardCode" AS "Vendor",
       T0."CardName" AS "Vendor Name", T1."BaseRef" AS "Base Invoice / Return",
       CASE WHEN T0."DocType" = 'S' THEN T1."Dscription" ELSE T1."ItemCode" END AS "Item / Service",
       T1."Quantity" AS "Qty", T1."LineTotal" AS "Taxable", T1."TaxCode" AS "Tax Code", {CGST("T1")} AS "CGST",
       {CGST("T1")} AS "SGST", {IGST("T1")} AS "IGST", T1."LineTotal" + T1."VatSum" AS "Line Total", T0."Comments" AS "Reason"
FROM "ORPC" T0 INNER JOIN "RPC1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum", T1."LineNum"'''),
    ("PTP", "PTP13 Goods Return Register", f'''
SELECT {NO("T0")} AS "Return No", T0."DocDate" AS "Date", T0."CardCode" AS "Vendor", T0."CardName" AS "Vendor Name",
       T1."BaseRef" AS "Base GRPO", T1."ItemCode" AS "Item", T1."Dscription" AS "Description", T1."Quantity" AS "Qty Returned",
       T1."unitMsr" AS "UoM", T1."WhsCode" AS "From Whse", T1."Price" AS "Rate", T1."LineTotal" AS "Value",
       T1."VatSum" AS "GST", CASE T1."LineStatus" WHEN 'O' THEN 'Credit memo pending' ELSE 'Credited / closed' END AS "Status",
       T0."Comments" AS "Reason"
FROM "ORPD" T0 INNER JOIN "RPD1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' ORDER BY T0."DocDate", T0."DocNum", T1."LineNum"'''),
    # ---------------------------------------------------------------------------------------------- PTS
    ("PTS", "PTS01 Production Order Status", f'''
SELECT {NO("T0")} AS "Order No", T0."PostDate" AS "Order Date", T0."DueDate" AS "Due Date", T0."ItemCode" AS "Product",
       I."ItemName" AS "Description", T0."PlannedQty" AS "Planned", T0."CmpltQty" AS "Completed", T0."RjctQty" AS "Rejected",
       T0."PlannedQty" - T0."CmpltQty" AS "Balance",
       CASE T0."Status" WHEN 'P' THEN 'Planned' WHEN 'R' THEN 'Released' WHEN 'L' THEN 'Closed' WHEN 'C' THEN 'Cancelled' END AS "Status",
       T0."Warehouse" AS "Whse"
FROM "OWOR" T0 INNER JOIN "OITM" I ON I."ItemCode" = T0."ItemCode" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0", "PostDate")} ORDER BY T0."PostDate", T0."DocNum"'''),
    ("PTS", "PTS02 Production Material Issue vs Plan", f'''
SELECT {NO("T0")} AS "Order No", T0."ItemCode" AS "Product", T1."ItemCode" AS "Component",
       CASE WHEN T1."ItemType" = 290 THEN 'Resource' ELSE 'Material' END AS "Type", T1."BaseQty" AS "Base Qty",
       T1."PlannedQty" AS "Planned", T1."IssuedQty" AS "Issued", T1."IssuedQty" - T1."PlannedQty" AS "Variance Qty",
       T1."wareHouse" AS "Whse"
FROM "OWOR" T0 INNER JOIN "WOR1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0", "PostDate")} ORDER BY T0."DocNum", T1."LineNum"'''),
    ("PTS", "PTS03 Receipt from Production Register", f'''
SELECT {NO("T0")} AS "Receipt No", T0."DocDate" AS "Date", T1."BaseRef" AS "Production Order", T1."ItemCode" AS "Product",
       T1."Dscription" AS "Description", T1."Quantity" AS "Qty", T1."WhsCode" AS "Whse", T1."StockPrice" AS "Unit Cost",
       T1."Quantity" * T1."StockPrice" AS "Value"
FROM "OIGN" T0 INNER JOIN "IGN1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE T1."BaseType" = 202 AND {DATES("T0")} ORDER BY T0."DocDate", T0."DocNum"'''),
    ("PTS", "PTS04 Bill of Materials List", '''
SELECT T0."Code" AS "Product", P."ItemName" AS "Product Name", T0."Qauntity" AS "BOM Qty", T1."Code" AS "Component",
       CASE WHEN T1."Type" = 290 THEN 'Resource' ELSE 'Material' END AS "Type", T1."Quantity" AS "Qty per BOM",
       T1."Warehouse" AS "Issue Whse", CASE T1."IssueMthd" WHEN 'M' THEN 'Manual' WHEN 'B' THEN 'Backflush' END AS "Issue Method"
FROM "OITT" T0 INNER JOIN "ITT1" T1 ON T1."Father" = T0."Code" INNER JOIN "OITM" P ON P."ItemCode" = T0."Code"
ORDER BY T0."Code", T1."ChildNum"'''),
    ("PTS", "PTS05 Stock Status by Warehouse", '''
SELECT T0."ItemCode" AS "Item", I."ItemName" AS "Description", G."ItmsGrpNam" AS "Item Group", T0."WhsCode" AS "Whse",
       I."InvntryUom" AS "UoM", T0."OnHand" AS "In Stock", T0."IsCommited" AS "Committed", T0."OnOrder" AS "On Order",
       T0."OnHand" - T0."IsCommited" + T0."OnOrder" AS "Available", T0."AvgPrice" AS "Avg Cost", T0."OnHand" * T0."AvgPrice" AS "Stock Value"
FROM "OITW" T0 INNER JOIN "OITM" I ON I."ItemCode" = T0."ItemCode" INNER JOIN "OITB" G ON G."ItmsGrpCod" = I."ItmsGrpCod"
WHERE T0."OnHand" <> 0 OR T0."IsCommited" <> 0 OR T0."OnOrder" <> 0 ORDER BY G."ItmsGrpNam", T0."ItemCode", T0."WhsCode"'''),
    ("PTS", "PTS06 Inventory Movement Register", f'''
SELECT T0."DocDate" AS "Date",
       CASE T0."TransType" WHEN 20 THEN 'GRPO' WHEN 18 THEN 'A/P Invoice' WHEN 15 THEN 'Delivery' WHEN 13 THEN 'A/R Invoice'
            WHEN 59 THEN 'Goods Receipt' WHEN 60 THEN 'Goods Issue' WHEN 67 THEN 'Transfer' WHEN 202 THEN 'Production'
            ELSE TO_NVARCHAR(T0."TransType") END AS "Transaction", T0."BASE_REF" AS "Doc No", T0."ItemCode" AS "Item",
       T0."Dscription" AS "Description", T0."Warehouse" AS "Whse", T0."InQty" AS "In", T0."OutQty" AS "Out",
       T0."CardName" AS "Partner", T0."Comments" AS "Remarks"
FROM "OINM" T0 WHERE {DATES("T0")} ORDER BY T0."DocDate", T0."TransNum"'''),
    ("PTS", "PTS07 Inventory Transfer Register", f'''
SELECT {NO("T0")} AS "Transfer No", T0."DocDate" AS "Date", T1."ItemCode" AS "Item", T1."Dscription" AS "Description",
       T1."FromWhsCod" AS "From Whse", T1."WhsCode" AS "To Whse", T1."Quantity" AS "Qty", T0."Comments" AS "Remarks"
FROM "OWTR" T0 INNER JOIN "WTR1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
WHERE {DATES("T0")} ORDER BY T0."DocDate", T0."DocNum"'''),
    # ---------------------------------------------------------------------------------------------- FIN
    ("FICO", "FIN01 Trial Balance", f'''
SELECT T1."Account" AS "Account", A."AcctName" AS "Account Name",
       CASE A."GroupMask" WHEN 1 THEN 'Assets' WHEN 2 THEN 'Liabilities' WHEN 3 THEN 'Equity' WHEN 4 THEN 'Revenue'
            WHEN 5 THEN 'Cost of Sales' WHEN 6 THEN 'Expenses' ELSE 'Other' END AS "Drawer",
       SUM(T1."Debit") AS "Debit", SUM(T1."Credit") AS "Credit", SUM(T1."Debit") - SUM(T1."Credit") AS "Closing (Dr +/Cr -)"
FROM "JDT1" T1 INNER JOIN "OACT" A ON A."AcctCode" = T1."Account"
WHERE {DATES("T1", "RefDate")} GROUP BY T1."Account", A."AcctName", A."GroupMask" ORDER BY A."GroupMask", T1."Account"'''),
    ("FICO", "FIN02 General Ledger - Account", '''
SELECT T1."RefDate" AS "Date", T0."Number" AS "JE No", T1."TransType" AS "Origin", T0."BaseRef" AS "Origin No",
       T1."ShortName" AS "BP / Account", T1."LineMemo" AS "Narration", T1."Debit" AS "Debit", T1."Credit" AS "Credit",
       SUM(T1."Debit" - T1."Credit") OVER (ORDER BY T1."RefDate", T1."TransId", T1."Line_ID") AS "Running Balance"
FROM "JDT1" T1 INNER JOIN "OJDT" T0 ON T0."TransId" = T1."TransId"
WHERE T1."RefDate" >= [%0] AND T1."RefDate" <= [%1] AND T1."Account" = [%2] ORDER BY T1."RefDate", T1."TransId", T1."Line_ID"'''),
    ("FICO", "FIN03 Journal Entry Register", f'''
SELECT T0."Number" AS "JE No", T0."RefDate" AS "Date", T0."TransType" AS "Origin", T0."BaseRef" AS "Origin No",
       T0."Memo" AS "Memo", T1."Account" AS "Account", A."AcctName" AS "Account Name", T1."ShortName" AS "BP",
       T1."Debit" AS "Debit", T1."Credit" AS "Credit"
FROM "OJDT" T0 INNER JOIN "JDT1" T1 ON T1."TransId" = T0."TransId" INNER JOIN "OACT" A ON A."AcctCode" = T1."Account"
WHERE {DATES("T0", "RefDate")} ORDER BY T0."RefDate", T0."Number", T1."Line_ID"'''),
    ("FICO", "FIN04 GST Summary - Output vs Input (3B)", f'''
SELECT 'Output (Sales)' AS "Side", T1."TaxCode" AS "Tax Code", SUM(T1."LineTotal") AS "Taxable",
       SUM({CGST("T1")}) AS "CGST", SUM({CGST("T1")}) AS "SGST", SUM({IGST("T1")}) AS "IGST", SUM(T1."VatSum") AS "Total GST"
FROM "OINV" T0 INNER JOIN "INV1" T1 ON T1."DocEntry" = T0."DocEntry"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' GROUP BY T1."TaxCode"
UNION ALL
SELECT 'Input (Purchases)', T1."TaxCode", SUM(T1."LineTotal"), SUM({CGST("T1")}), SUM({CGST("T1")}), SUM({IGST("T1")}), SUM(T1."VatSum")
FROM "OPCH" T0 INNER JOIN "PCH1" T1 ON T1."DocEntry" = T0."DocEntry"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' GROUP BY T1."TaxCode"
UNION ALL
SELECT 'Input reversed (A/P credit notes)', T1."TaxCode", -SUM(T1."LineTotal"), -SUM({CGST("T1")}), -SUM({CGST("T1")}),
       -SUM({IGST("T1")}), -SUM(T1."VatSum")
FROM "ORPC" T0 INNER JOIN "RPC1" T1 ON T1."DocEntry" = T0."DocEntry"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' GROUP BY T1."TaxCode"
ORDER BY 1, 2'''),
    ("FICO", "FIN05 GSTR-1 B2B Invoice List", f'''
SELECT C."GSTRegnNo" AS "Customer GSTIN", T0."CardName" AS "Customer", {NO("T0")} AS "Invoice No", T0."DocDate" AS "Invoice Date",
       T0."DocTotal" AS "Invoice Value", LEFT(C."GSTRegnNo", 2) AS "Place of Supply", T1."VatPrcnt" AS "Rate %",
       SUM(T1."LineTotal") AS "Taxable", SUM({IGST("T1")}) AS "IGST", SUM({CGST("T1")}) AS "CGST", SUM({CGST("T1")}) AS "SGST"
FROM "OINV" T0 INNER JOIN "INV1" T1 ON T1."DocEntry" = T0."DocEntry" LEFT JOIN "NNM1" N ON N."Series" = T0."Series"
LEFT JOIN "CRD1" C ON C."CardCode" = T0."CardCode" AND C."AdresType" = 'B' AND C."Address" = T0."PayToCode"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N'
GROUP BY C."GSTRegnNo", T0."CardName", N."BeginStr", T0."DocNum", T0."DocDate", T0."DocTotal", T1."VatPrcnt"
ORDER BY T0."DocDate", T0."DocNum"'''),
    ("FICO", "FIN06 TDS Payable by Section", f'''
SELECT X."WTCode" AS "TDS Code", X."WTName" AS "Description", W."Rate" AS "Rate %", COUNT(*) AS "Deductions",
       SUM(W."TaxbleAmnt") AS "Taxable", SUM(W."WTAmnt") AS "TDS Deducted", X."Account" AS "Payable Account"
FROM "OPCH" T0 INNER JOIN "PCH5" W ON W."AbsEntry" = T0."DocEntry" INNER JOIN "OWHT" X ON X."WTCode" = W."WTCode"
WHERE {DATES("T0")} AND T0."CANCELED" = 'N' GROUP BY X."WTCode", X."WTName", W."Rate", X."Account" ORDER BY X."WTCode"'''),
    ("FICO", "FIN07 Profit & Loss Summary", f'''
SELECT CASE WHEN A."GroupMask" = 4 THEN '1 Revenue' WHEN A."GroupMask" = 5 THEN '2 Cost of Sales' ELSE '3 Expenses' END AS "Section",
       T1."Account" AS "Account", A."AcctName" AS "Account Name", SUM(T1."Credit") - SUM(T1."Debit") AS "Amount (Income +/Cost -)"
FROM "JDT1" T1 INNER JOIN "OACT" A ON A."AcctCode" = T1."Account"
WHERE {DATES("T1", "RefDate")} AND A."GroupMask" IN (4, 5, 6, 7, 8)
GROUP BY A."GroupMask", T1."Account", A."AcctName" ORDER BY 1, T1."Account"'''),
]


def run_sql(sl, code, sql):
    """Execute a report once through Service Layer SQLQueries (temporary query, removed afterwards)."""
    for k, v in TEST_PARAMS.items():
        sql = sql.replace(k, v)
    sl.s.delete(f"{sl.base}/SQLQueries('{code}')", timeout=60)
    r = sl.s.post(f"{sl.base}/SQLQueries", json={"SqlCode": code, "SqlName": code, "SqlText": sql}, timeout=60)
    if r.status_code not in (200, 201):
        return None, r.json()["error"]["message"]
    r = sl.s.get(f"{sl.base}/SQLQueries('{code}')/List", timeout=120, headers={"Prefer": "odata.maxpagesize=1000"})
    sl.s.delete(f"{sl.base}/SQLQueries('{code}')", timeout=60)
    if r.status_code != 200:
        return None, r.json()["error"]["message"]
    return r.json()["value"], None


def create_categories(sl):
    """Create the missing Query Manager categories; return {name: code}."""
    cats = {c["Name"]: c["Code"] for c in sl.get("QueryCategories")["value"]}
    for name in CATEGORIES.values():
        if name not in cats:
            res = sl.post("QueryCategories", {"Name": name, "Permissions": "YYYYYYYYYYYYYYY"}, name)
            if res:
                cats[name] = res["Code"]
    return cats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="only run the SQL, do not save queries")
    ap.add_argument("--no-test", action="store_true",
                    help="save without the Service Layer test (SQLQueries rejects ||, CASE, arithmetic and some tables)")
    ap.add_argument("--categories", action="store_true", help="only create the Query Manager categories")
    a = ap.parse_args()
    sl = L.SL(L.read_env(), False, print)
    sl.login()
    if a.categories:
        cats = create_categories(sl)
        print("Categories:", {n: cats.get(n) for n in CATEGORIES.values()}, f"Failures: {sl.failures}")
        return
    bad = 0
    for cat, title, sql in ([] if a.no_test else REPORTS):
        rows, err = run_sql(sl, "zz_" + title.split()[0].lower(), sql.strip())
        if err:
            bad += 1
            print(f"FAIL {title}: {err}")
        else:
            print(f"OK   {title:48s} {len(rows):4d} rows" + (f"  e.g. {list(rows[0].items())[:3]}" if rows else ""))
    if a.test or bad:
        print(f"Tested {len(REPORTS)} reports, {bad} failed." + ("" if a.test else " Nothing saved."))
        return
    cats = create_categories(sl)
    have = {(q["QueryCategory"], q["QueryDescription"]): q["InternalKey"]
            for q in sl.get(f"UserQueries?$select=InternalKey,QueryCategory,QueryDescription&$filter=QueryCategory gt 0")["value"]}
    for cat, title, sql in REPORTS:
        code = cats[CATEGORIES[cat]]
        body = {"QueryCategory": code, "QueryDescription": title, "Query": sql.strip()}
        if (code, title) in have:
            sl.patch("UserQueries", {"InternalKey": have[(code, title)], "QueryCategory": code}, {"Query": sql.strip()}, title)
        else:
            sl.post("UserQueries", body, title)
    print(f"Done. Failures: {sl.failures}")


if __name__ == "__main__":
    main()
