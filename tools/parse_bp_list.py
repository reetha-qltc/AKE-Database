"""Parse AKE's SAP B1 business-partner export ('Customer list.csv', UTF-16, one row per address) into
data/ake_customers/bps.json.

The export is not quoted, so commas inside names, streets and amounts shift the columns. Fields are therefore found
by anchors instead of positions:
  header  #,CardCode,CardName...,CardType(C/S),GroupCode(100/101/102),...
  mobile/e-mail   counted back from the ',P,N,N,N' run (Parent Summary Type + 64 property flags)
  active/frozen   after the encrypted credit-card constant '/aJkE...=='
  address tail    ...,AddressName,CardCode,Street...,Zip,City,County,Country,State,UserSign,LogInst,2,...,B|S,...,GSTIN
Run:  python tools/parse_bp_list.py ["Customer list.csv"]
"""
import collections, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "Customer list.csv")
OUT = ROOT / "data" / "ake_customers" / "bps.json"
GSTIN = re.compile(r"\b(\d{2})([A-Z]{5}\d{4}[A-Z])[0-9A-Z]Z[0-9A-Z]\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CC = "/aJkEu9+xYoUrzxQe1zMCw=="


def clean(s):
    s = EMAIL.sub("", s.replace("�", ""))
    return re.sub(r"\s+", " ", s.replace(",", ", ")).strip(" ,").replace(" ,", ",")


def parse_line(ln):
    f = ln.split(",")
    code = f[1].strip().upper()
    # CardType + GroupCode follow the (comma-containing) name
    i = next(i for i in range(3, 12) if f[i] in ("C", "S") and f[i + 1] in ("100", "101", "102"))
    rec = {"Code": code, "Name": clean(",".join(f[2:i])), "Type": f[i], "Group": f[i + 1]}
    p = ln.find(",P,N,N,N,")
    pre = ln[:p].split(",")
    mob = pre[-17].strip()
    rec["Mobile"] = mob if re.fullmatch(r"[\d +/-]{8,}", mob) else ""
    em = EMAIL.findall(ln[:p])
    rec["Email"] = em[0] if em else ""
    c = ln.find(CC)
    flags = ln[c:].split(",")[1:8] if c >= 0 else []
    # CCValidity, UserSign, LCRecon, validFor, validFrom, validTo, frozenFor
    rec["Active"] = not (len(flags) > 6 and (flags[3] == "N" or flags[6] == "Y"))
    # address tail: last ',<code>,' occurrence (address BP Code column)
    m = None
    for m in re.finditer(r",(%s),(?=.*,2,)" % re.escape(f[1].strip()), ln, re.I):
        pass
    addr = None
    if m and m.start() > p:
        # address name follows the last ',N,N,N,N,' run (... Data Version, Legal Text, VAT verification date/code)
        k = re.search(r".*,N,N,N,N,[^,]*,\d*,[^,]*,[^,]*,[^,]*,(.*)$", ln[:m.start()])
        aname = k.group(1) if k and CC not in k.group(1) else ""
        tail = ln[m.end():]
        a = re.search(r"(?:^|,)(\d{6}|[^,]*),([^,]*),([^,]*),([A-Z]{2}|),([A-Z]{2}|[^,]*),[^,]*,[^,]*,2,[^,]*,[^,]*,[^,]*,([^,]*),([BS]),", tail)
        if a:
            street = clean(tail[:a.start()])
            rest = tail[a.end():]
            g = GSTIN.search(rest)
            addr = {"AddressName": clean(aname)[:50] or ("Bill To" if a.group(7) == "B" else "Ship To"),
                    "Type": a.group(7), "Street": street, "Zip": a.group(1).strip(), "City": clean(a.group(2)),
                    "Country": a.group(4) or "IN", "State": a.group(5).strip(), "Building": clean(a.group(6)),
                    "GSTIN": g.group(0) if g else ""}
            if addr["Country"] != "IN":  # foreign party: no state, no GSTIN (AKE used a dummy 29AAAAA1111K1ZZ)
                addr.update(State="", GSTIN="")
    rec["Address"] = addr
    return rec


def main():
    lines = SRC.read_text(encoding="utf-16").splitlines()[1:]
    bps, bad = collections.OrderedDict(), []
    for n, ln in enumerate(lines, 2):
        try:
            r = parse_line(ln)
        except Exception as e:
            bad.append((n, repr(e), ln[:120]))
            continue
        bp = bps.setdefault(r["Code"], {k: v for k, v in r.items() if k != "Address"} | {"Addresses": []})
        if r["Address"] and r["Address"] not in bp["Addresses"]:
            bp["Addresses"].append(r["Address"])
    for bp in bps.values():
        gst = next((a["GSTIN"] for a in bp["Addresses"] if a["Type"] == "B" and a["GSTIN"]), "") or \
              next((a["GSTIN"] for a in bp["Addresses"] if a["GSTIN"]), "")
        bp["GSTIN"], bp["PAN"] = gst, gst[2:12]
    OUT.write_text(json.dumps(list(bps.values()), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(bps)} BPs -> {OUT.relative_to(ROOT)}; {len(bad)} unparsed lines")
    for b in bad[:20]:
        print("  BAD", b)


if __name__ == "__main__":
    main()
