"""Parse AKE's SAP B1 BOM export ('Bom master list.csv', UTF-16, one row per component) into data/ake_boms/boms.json.

Unquoted export: commas in item names and amounts shift the columns, so each row is matched as a whole:
  #,Parent,ParentName...,BOMType,ParentQty,ParentWhs,PriceList,LineNo,Child,ChildName...,ChildQty,ChildWhs,
  IssueMethod(M/B),ComponentType(4 item / 290 resource / -18 text),Price,Currency,PriceList,
Run:  python tools/parse_bom_list.py ["Bom master list.csv"]
"""
import collections, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "Bom master list.csv")
OUT = ROOT / "data" / "ake_boms" / "boms.json"
NUM = r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?"
ROW = re.compile(rf"^\d+,([^,]+),(.*?),([PASTN]),({NUM}),([^,]*),(-?\d*),(\d*),([^,]*),(.*?),({NUM}),([^,]*),([MB]?),"
                 rf"(-?\d+),({NUM}),([A-Z]*),(-?\d*),$")
num = lambda s: float(s.replace(",", ""))


def main():
    lines = SRC.read_text(encoding="utf-16").splitlines()[1:]
    boms, bad = collections.OrderedDict(), []
    for n, ln in enumerate(lines, 2):
        m = ROW.match(ln)
        if not m:
            bad.append((n, ln[:160]))
            continue
        g = m.groups()
        b = boms.setdefault(g[0], {"TreeCode": g[0], "Name": g[1].strip('"'), "Type": g[2], "Qty": num(g[3]),
                                   "Warehouse": g[4], "Lines": []})
        b["Lines"].append({"LineNo": int(g[6]) if g[6] else len(b["Lines"]) + 1, "Code": g[7],
                           "Name": g[8].strip('"'), "Qty": num(g[9]), "Warehouse": g[10], "IssueMethod": g[11],
                           "Type": int(g[12]), "Price": num(g[13])})
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(list(boms.values()), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(boms)} BOMs, {sum(len(b['Lines']) for b in boms.values())} lines -> {OUT.relative_to(ROOT)}; "
          f"{len(bad)} unparsed")
    for b in bad[:15]:
        print("  BAD", b)


if __name__ == "__main__":
    main()
