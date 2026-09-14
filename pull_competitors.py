#!/usr/bin/env python3
import os,json,base64,sys,requests
from pathlib import Path
OUT=Path("/home/user/seo/data/personio")
l,p=os.environ["DATAFORSEO_LOGIN"],os.environ["DATAFORSEO_PASSWORD"]
H={"Authorization":"Basic "+base64.b64encode(f"{l}:{p}".encode()).decode(),"Content-Type":"application/json"}
# Top-3 transactional competitors that are actual HR-software vendors, by SERP visibility
TARGETS=[("rexx-systems.com",2276,"de","DE"),("datev.de",2276,"de","DE"),("workday.com",2276,"de","DE"),
         ("sage.com",2826,"en","GB"),("oracle.com",2826,"en","GB"),("peoplehr.com",2826,"en","GB")]
cost=0
for dom,loc,lang,mkt in TARGETS:
    pl=[{"target":dom,"location_code":loc,"language_code":lang,"limit":1000,
         "order_by":["ranked_serp_element.serp_item.etv,desc"],
         "filters":[["ranked_serp_element.serp_item.type","=","organic"],"and",
                    ["keyword_data.keyword_info.search_volume",">",0]]}]
    j=requests.post("https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live",
                    headers=H,json=pl,timeout=300).json()
    if j["status_code"]!=20000: sys.exit(f"{dom}: {j['status_message']}")
    cost+=j["cost"]
    (OUT/f"raw_{mkt}_{dom.replace('.','_')}.json").write_text(json.dumps(j))
    res=j["tasks"][0]["result"][0]
    print(f"{mkt} {dom}: items={len(res.get('items') or [])} total_kw={res.get('total_count'):,}")
print("cost",round(cost,3))
