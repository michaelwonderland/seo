#!/usr/bin/env python3
import json,re
from pathlib import Path
OUT=Path("/home/user/seo/data/personio")

# Practitioner definition of TRANSACTIONAL for B2B SaaS: category/product-purchase terms
BUY = re.compile(r"\b(software|system|systeme|tool|tools|platform|plattform|hris|hrms|ats|applicant tracking|"
                 r"payroll|lohnabrechnung|zeiterfassung|bewerbermanagement|personalverwaltung|personalmanagement|"
                 r"personalsoftware|best|top|vergleich|compare|alternative|pricing|preis|kosten|cost|demo|trial)\b", re.I)
# noise that looks commercial but is not a buying query for an HR SaaS
NOISE = re.compile(r"\b(job|jobs|course|courses|salary|gehalt|career|karriere|meaning|definition|certification|"
                   r"training|resume|cv|interview|exam|tutorial|xero|sage|quickbooks|free download|download)\b", re.I)

def uniq_by_vol(rows, n):
    seen=set(); out=[]
    for r in sorted(rows,key=lambda x:-x["vol"]):
        key=" ".join(sorted(re.sub(r"[^a-zäöüß0-9 ]","",r["kw"].lower()).split()))
        if key in seen: continue
        seen.add(key); out.append(r)
        if len(out)>=n: break
    return out

# ---- TRANSACTIONAL sets from category suggestions ----
trans={}
for mkt in ["DE","GB"]:
    items=json.loads((OUT/f"sugg_{mkt}.json").read_text())
    rows=[]
    for it in items:
        ki=it.get("keyword_info") or {}; si=it.get("search_intent_info") or {}
        kw=it["keyword"]
        if not BUY.search(kw) or NOISE.search(kw): continue
        rows.append(dict(kw=kw,vol=ki.get("search_volume") or 0,cpc=ki.get("cpc") or 0,
                         intent=si.get("main_intent")))
    trans[mkt]=uniq_by_vol(rows,50)
    print(f"TRANSACTIONAL {mkt}: {len(trans[mkt])} kws, total vol {sum(r['vol'] for r in trans[mkt]):,}, "
          f"avg cpc ${sum(r['cpc'] for r in trans[mkt])/len(trans[mkt]):.2f}")

# ---- INFORMATIONAL sets from Personio's own top informational rankings ----
BRAND=re.compile(r"personio",re.I)
info={}
for mkt,f in [("DE","raw_personio_de.json"),("GB","raw_personio_com_gb.json")]:
    j=json.loads((OUT/f).read_text()); rows=[]
    for t in j["tasks"]:
        for r in t["result"]:
            for it in r["items"]:
                kd=it["keyword_data"]; ki=kd.get("keyword_info") or {}; si=kd.get("search_intent_info") or {}
                sp=(it.get("ranked_serp_element") or {}).get("serp_item") or {}
                kw=kd["keyword"]
                if BRAND.search(kw) or si.get("main_intent")!="informational": continue
                if BUY.search(kw): continue
                rows.append(dict(kw=kw,vol=ki.get("search_volume") or 0,cpc=ki.get("cpc") or 0,
                                 etv=sp.get("etv") or 0,intent="informational"))
    rows.sort(key=lambda x:-x["etv"])
    info[mkt]=uniq_by_vol(rows[:200],50)
    print(f"INFORMATIONAL {mkt}: {len(info[mkt])} kws, total vol {sum(r['vol'] for r in info[mkt]):,}")

json.dump({"transactional":trans,"informational":info}, open(OUT/"keyword_sets.json","w"), indent=1)
for b in ["transactional","informational"]:
    for mkt in ["DE","GB"]:
        s = trans[mkt] if b=="transactional" else info[mkt]
        print(f"\n--- {b.upper()} {mkt} (top 15) ---")
        for r in s[:15]: print(f"   {r['vol']:>6} | cpc {r['cpc']:>6.2f} | {r['kw']}")
