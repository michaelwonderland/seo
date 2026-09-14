#!/usr/bin/env python3
import json, csv, re
from pathlib import Path
OUT = Path("/home/user/seo/data/personio")

BRAND = re.compile(r"personio", re.I)

def rows(f):
    j = json.loads(f.read_text())
    out = []
    for t in j.get("tasks") or []:
        for r in (t.get("result") or []):
            for it in (r.get("items") or []):
                kd = it.get("keyword_data") or {}
                ki = kd.get("keyword_info") or {}
                kp = kd.get("keyword_properties") or {}
                si = kd.get("search_intent_info") or {}
                sp = (it.get("ranked_serp_element") or {}).get("serp_item") or {}
                out.append({
                    "keyword": kd.get("keyword"),
                    "search_volume": ki.get("search_volume"),
                    "etv": round(sp.get("etv") or 0, 1),
                    "position": sp.get("rank_absolute"),
                    "url": sp.get("url"),
                    "kd": kp.get("keyword_difficulty"),
                    "cpc": ki.get("cpc"),
                    "intent": si.get("main_intent"),
                    "foreign_intent": ",".join(si.get("foreign_intent") or []),
                    "branded": bool(BRAND.search(kd.get("keyword") or "")),
                })
    return out

for dom in ["personio_de", "personio_com"]:
    rs = rows(OUT / f"raw_{dom}.json")
    nb = [r for r in rs if not r["branded"]]
    with (OUT / f"{dom}_keywords.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rs[0].keys())); w.writeheader(); w.writerows(rs)
    from collections import Counter
    c = Counter(r["intent"] for r in nb)
    print(f"\n=== {dom} === total={len(rs)} nonbrand={len(nb)}")
    print("  intent mix (non-brand):", dict(c))
    print(f"  brand ETV={sum(r['etv'] for r in rs if r['branded']):,.0f}  nonbrand ETV={sum(r['etv'] for r in nb):,.0f}")
    print("  TOP 25 NON-BRAND BY ETV:")
    for r in sorted(nb, key=lambda x: -x["etv"])[:25]:
        print(f"   {r['etv']:>8.0f} | pos {str(r['position']):>3} | vol {str(r['search_volume']):>7} | {r['intent']:<14} | {r['keyword'][:55]}")
