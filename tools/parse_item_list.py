"""Parse AKE's SAP B1 item master export ('item master list final.csv', UTF-16) into data/ake_items/items.json.

The export is not quoted: commas in descriptions and in amounts (20,000.00) shift the columns, so fields are found by
anchors instead of positions:
  start   #,ItemCode,Description[,ForeignName],ItmsGrpCod,CustomsGroup,TaxDef,BarCode,TaxLiable,Purchase,Sales,Inventory
  valuation       ...,Valuation(A/S/F/B),UserSign,Free(Y/N),Picture,YearTransfer,BalancesTransferred,...
  active/inactive ...,ManBtch,SNOnExit,DataSource,validFor,from,to,frozenFor,from,to,ForceSN,remarks,remarks,LogInst,4(ObjType),...
  item type       ObjType + 13 fields (TaxType, ManInvByWhs, WTLiable, ItemType I/L/T/F)
  planning        ...,Planning(M/N),Procurement(B/M),OrderInterval,OrderMultiple,MinOrderQty,LeadTime,...
  names (right)   ...,Item Group Name,UoM Group Name,Inventory UoM Name,Purchase UoM Name,Sales UoM Name,''
Run:  python tools/parse_item_list.py ["item master list final.csv"]
"""
import collections, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "item master list final.csv")
OUT = ROOT / "data" / "ake_items" / "items.json"

START = re.compile(r"^\d+,([^,]*),(.*?),(\d+),(-?\d*),[^,]*,[^,]*,([YN]),([YN]),([YN]),([YN]),")
VALUATION = re.compile(r",([ASFB]),(\d+),([YN]),[^,]*,([YN]),([YN]),")
ACTIVE = re.compile(r",([YN]),([YN]),([A-Z]),([YN]),([^,]*),([^,]*),([YN]),([^,]*),([^,]*),([YN]),"
                    r"([^,]*),([^,]*),([^,]*),4,[^,]*,([YN]),(\d+),"
                    r"[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,([YN]),([YN]),([YN]),([ILTF]),")
PLANNING = re.compile(r",([MN]),([BM]),(\d*),([\d.]+),([\d.]+),(\d*),")


def main():
    lines = SRC.read_text(encoding="utf-16").splitlines()[1:]
    items, bad = [], collections.Counter()
    for n, ln in enumerate(lines, 2):
        s = START.match(ln)
        if not s:
            bad["start"] += 1
            continue
        f = ln.split(",")
        desc = s.group(2)
        # description may carry a trailing ',ForeignName' - foreign names are rare, keep the text before the last comma
        # only when the remainder is empty (no foreign name)
        desc = desc[:-1] if desc.endswith(",") else desc
        rest = ln[s.end():]
        v = VALUATION.search(rest)
        a = ACTIVE.search(rest)
        p = PLANNING.search(rest[a.end():] if a else rest)
        if not a:
            bad["active"] += 1
        it = {"ItemCode": s.group(1), "ItemName": re.sub(r"\s+", " ", desc).strip(), "GroupCode": s.group(3),
              "Purchase": s.group(6) == "Y", "Sales": s.group(7) == "Y", "Inventory": s.group(8) == "Y",
              "Valuation": v.group(1) if v else "", "ManageBatch": a.group(1) == "Y" if a else False,
              "Active": (a.group(4) == "Y" and a.group(7) == "N") if a else True,
              "ItemType": a.group(19) if a else "I",
              "Planning": p.group(1) if p else "", "Procurement": p.group(2) if p else "",
              "ItemGroup": f[-6].strip(), "UoMGroup": f[-5].strip(), "InventoryUoM": f[-4].strip(),
              "PurchaseUoM": f[-3].strip() or f[-4].strip(), "SalesUoM": f[-2].strip() or f[-4].strip()}
        items.append(it)
    OUT.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(items)} items -> {OUT.relative_to(ROOT)}; unparsed {dict(bad)}")


if __name__ == "__main__":
    main()
