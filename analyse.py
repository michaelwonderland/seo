#!/usr/bin/env python3
import json,re
from pathlib import Path
OUT=Path("/home/user/seo/data/personio")
BRAND=re.compile(r"personio",re.I)

def prof(f, brandre=BRAND):
    j=json.loads((OUT/f).read_text()); rows=[]
    for t in j["tasks"]:
        for r in t["result"]:
            for it in r["items"]:
                kd=it["keyword_data"]; ki=kd.get("keyword_info") or {}; si=kd.get("search_intent_info") or {}
                sp=(it.get("ranked_serp_element") or {}).get("serp_item") or {}
                rows.append(dict(kw=kd["keyword"],vol=ki.get("search_volume") or 0,cpc=ki.get("cpc") or 0,
                    etv=sp.get("etv") or 0,pos=sp.get("rank_absolute"),
                    intent=si.get("main_intent"),brand=bool(brandre.search(kd["keyword"]))))
    return rows

BUY=re.compile(r"\b(software|system|systeme|tool|tools|platform|plattform|hris|hrms|ats|applicant tracking|"
               r"payroll|lohnabrechnung|zeiterfassung|bewerbermanagement|personalverwaltung|personalmanagement|"
               r"personalsoftware|best|top|vergleich|compare|alternative|pricing|preis|kosten|demo|trial)\b",re.I)

DOMS={"DE":[("personio.de","raw_personio_de.json",BRAND),
            ("rexx-systems.com","raw_DE_rexx-systems_com.json",re.compile(r"rexx",re.I)),
            ("datev.de","raw_DE_datev_de.json",re.compile(r"datev",re.I)),
            ("workday.com","raw_DE_workday_com.json",re.compile(r"workday",re.I))],
      "GB":[("personio.com","raw_personio_com_gb.json",BRAND),
            ("sage.com","raw_GB_sage_com.json",re.compile(r"\bsage\b",re.I)),
            ("oracle.com","raw_GB_oracle_com.json",re.compile(r"oracle",re.I)),
            ("peoplehr.com","raw_GB_peoplehr_com.json",re.compile(r"people\s*hr|peoplehr",re.I))]}

for mkt,doms in DOMS.items():
    print(f"\n{'='*104}\nPORTFOLIO COMPARISON — {mkt}  (top 1000 keywords by ETV per domain)\n{'='*104}")
    print(f"{'domain':<20}{'nonbrandETV':>12}{'brandETV':>10}{'%brand':>8}{'buyKW':>7}{'buyETV':>9}{'%buyETV':>9}{'avgCPCbuy':>11}{'top3':>6}{'top10':>7}")
    for name,f,br in doms:
        rs=prof(f,br); nb=[r for r in rs if not r["brand"]]
        buy=[r for r in nb if BUY.search(r["kw"])]
        tot=sum(r["etv"] for r in rs); nbe=sum(r["etv"] for r in nb); be=tot-nbe
        bye=sum(r["etv"] for r in buy)
        acpc=(sum(r["cpc"] for r in buy)/len(buy)) if buy else 0
        t3=sum(1 for r in nb if (r["pos"] or 99)<=3); t10=sum(1 for r in nb if (r["pos"] or 99)<=10)
        print(f"{name:<20}{nbe:>12,.0f}{be:>10,.0f}{(be/tot*100 if tot else 0):>7.0f}%{len(buy):>7}{bye:>9,.0f}"
              f"{(bye/nbe*100 if nbe else 0):>8.1f}%{acpc:>11.2f}{t3:>6}{t10:>7}")

# ---- head to head on the transactional keyword set ----
PICK={"DE":["www.personio.de","www.rexx-systems.com","www.datev.de","www.workday.com"],
      "GB":["www.personio.com","www.sage.com","www.oracle.com","www.peoplehr.com"]}
sets=json.loads((OUT/"keyword_sets.json").read_text())
for mkt in ["DE","GB"]:
    j=json.loads((OUT/f"full_transactional_{mkt}.json").read_text())
    items={i["domain"]:i for i in j["tasks"][0]["result"][0]["items"]}
    picks=PICK[mkt]
    print(f"\n{'='*104}\nHEAD-TO-HEAD — TRANSACTIONAL SET, {mkt} ({len(sets['transactional'][mkt])} money keywords)\n{'='*104}")
    print(f"{'domain':<26}{'kws ranked':>11}{'avg pos':>9}{'median':>8}{'visibility':>12}")
    for d in picks:
        i=items.get(d)
        if not i: print(f"{d:<26}{'0':>11}{'—':>9}{'—':>8}{'0.00':>12}"); continue
        print(f"{d:<26}{i['keywords_count']:>11}{i['avg_position']:>9.1f}{i['median_position']:>8.0f}{i['visibility']:>12.2f}")
    # per keyword grid
    kws=[r for r in sets["transactional"][mkt]][:20]
    print(f"\n{'keyword':<36}{'vol':>7}{'cpc':>8}" + "".join(f"{d.replace('www.','')[:11]:>13}" for d in picks))
    for r in kws:
        cells=[]
        for d in picks:
            i=items.get(d); pos=(i or {}).get("keywords_positions",{}).get(r["kw"])
            cells.append(f"{min(pos) if pos else '—':>13}")
        print(f"{r['kw'][:35]:<36}{r['vol']:>7}{r['cpc']:>8.2f}"+"".join(str(c) for c in cells))
