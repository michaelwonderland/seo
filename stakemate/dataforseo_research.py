import os,json,base64,requests
tok=base64.b64encode(f"{os.environ['DATAFORSEO_LOGIN']}:{os.environ['DATAFORSEO_PASSWORD']}".encode()).decode()
H={"Authorization":f"Basic {tok}","Content-Type":"application/json"}
LOC,LANG=2826,"en"
def post(path,payload):
    r=requests.post("https://api.dataforseo.com/v3/"+path,headers=H,json=payload,timeout=180); r.raise_for_status(); return r.json()
out=json.load(open("raw.json"))
out["suggestions"]=[]
for s in ["betting app","bet with friends","social betting","betting sites","free bets","bet builder","football betting","accumulator","betting with mates","group bet"]:
    out["suggestions"].append(post("dataforseo_labs/google/keyword_suggestions/live",[{"keyword":s,"location_code":LOC,"language_code":LANG,"limit":300,"order_by":["keyword_info.search_volume,desc"],"filters":[["keyword_info.search_volume",">",30]]}]))
out["competitors"]=[]
for d in ["betfred.com","bet442.co.uk","talksport.bet","betgoodwin.co.uk","midnite.com"]:
    out["competitors"].append(post("dataforseo_labs/google/ranked_keywords/live",[{"target":d,"location_code":LOC,"language_code":LANG,"limit":300,"order_by":["keyword_data.keyword_info.search_volume,desc"],"filters":[["keyword_data.keyword_info.search_volume",">",100],"and",["ranked_serp_element.serp_item.rank_absolute","<=",20]]}]))
json.dump(out,open("raw.json","w"))
cost=sum(t.get("cost",0) for k in out.values() for v in (k if isinstance(k,list) else [k]) for t in v.get("tasks",[]))
print("total cost $",round(cost,3))
