"""Direct GRPOs (no purchase order) for 10 more AKE vendors in AKE_DEMO.

Items fit the vendor (abrasives for Apex Abrasives, gases for Asba, bolts for Aswathi Hardware, steel for Beekay /
Bhotika / Choudhary, paint for Berger, blasting grit for Blastline, filters for Donaldson ...), priced at AKE's average
cost and received into U1 WH1 on 06-10-2026.  GST from the vendor's bill-to state (KA -> CG+SG@18, else IGST@18).
Batch items get batch GRN-<vendor>-261006.  GRPOs stay open (no A/P invoice).

Run:  python tools/demo_direct_grpo.py              (all)
      python tools/demo_direct_grpo.py V014 V027    (selected vendors)
Posted documents are recorded in logs/txn_state.json (keys AKE-<vendor>-DGRN), so a re-run continues where it stopped.
"""
import sys

import demo_ake_cycles as C
import demo_transactions as T

WH, DATE = "U1 WH1", "2026-10-06"
VENDORS = {  # card: (vendor delivery challan, [(item, qty)])
    "V011": ("APEX/DC/26-27/118", [("CON120033", 100), ("CON120082", 50), ("CON120064", 100)]),  # cut-off / grinding wheels, flap discs
    "V014": ("ASBA/DC/4471", [("CON120079", 111), ("CON120618", 55.5)]),                       # oxygen, argon mix (m3)
    "V015": ("AHS/DC/0937", [("CON120102", 500), ("CON120106", 300)]),                         # HT hex bolts M10 / M12
    "V020": ("BCDD/DC/215", [("OFS170009", 5), ("OFS170103", 5)]),                             # HP cartridge, Dell mouse
    "V025": ("BEEKAY/DC/26-27/0661", [("RMS219904", 1000), ("RMS219906", 800)]),               # MS angle, channel (KGS)
    "V027": ("BERGER/DC/8812046", [("CON120673", 40), ("CON120271", 60)]),                     # epoxy primer, thinner (LTR)
    "V029": ("BIPL/DC/2026/774", [("Z24631250005", 3000)]),                                     # HR plate 1250 x 5 (KGS)
    "V030": ("BLAST/DC/0429", [("CON120319", 500), ("SPO250229", 2)]),                          # steel grit, blasting hose
    "V035": ("CSS/DC/1186", [("RMS219907", 500), ("RMS219905", 1000)]),                         # MS flat, MS beam (KGS)
    "V039": ("DIFS/DC/90331", [("SPO250390", 2), ("SPO250110", 4)]),                            # compressor air / oil filters
}


def grpo(run, card):
    ref, lines = VENDORS[card]
    name, tax = run.tax(card)
    print(f"--- {card} {name} ({tax})")
    body = []
    for code, qty in lines:
        it = run.item(code)
        if it["PurchaseItem"] != "tYES":
            raise SystemExit(f"{card}: {code} is not a purchase item")
        ln = {"ItemCode": code, "Quantity": qty, "UnitPrice": round(run.cost[code], 2), "WarehouseCode": WH, "TaxCode": tax}
        if it["ManageBatchNumbers"] == "tYES":
            ln["BatchNumbers"] = [{"BatchNumber": f"GRN-{card}-261006", "Quantity": qty}]
        body.append(ln)
    doc = run.doc(f"AKE-{card}-DGRN", "PurchaseDeliveryNotes", {
        "CardCode": card, "DocDate": DATE, "DocDueDate": DATE, "TaxDate": DATE, "NumAtCard": ref,
        "Comments": f"AKE demo direct GRPO {card} - {ref} (no purchase order)", "DocumentLines": body},
        "Direct GRPO " + ", ".join(f"{c} x {q}" for c, q in lines))
    print(f"     GRPO #{doc['DocNum']}: {C.total(run, 'PurchaseDeliveryNotes', doc)}")


if __name__ == "__main__":
    run = C.Run()
    r = run.sl.s.post(f"{run.sl.base}/SBOBobService_SetCurrencyRate", timeout=60,  # system currency USD
                      json={"Currency": "USD", "Rate": str(T.USD_RATE), "RateDate": DATE.replace("-", "")})
    if r.status_code not in (200, 204):
        raise SystemExit(f"FAIL USD rate {DATE}: {r.text[:300]}")
    for v in sys.argv[1:] or VENDORS:
        grpo(run, v)
    print("Done.")
