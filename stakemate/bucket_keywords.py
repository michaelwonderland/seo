import json,csv,re
out=json.load(open("raw.json"))
kws={}
def add(kd,src):
    k=kd.get("keyword"); ki=kd.get("keyword_info") or {}; si=kd.get("search_intent_info") or {}; kp=kd.get("keyword_properties") or {}
    if not k: return
    e=kws.setdefault(k,{"keyword":k,"volume":ki.get("search_volume") or 0,"cpc":ki.get("cpc"),"competition":ki.get("competition_level"),"intent":si.get("main_intent"),"kd":kp.get("keyword_difficulty"),"src":set()})
    e["src"].add(src)
for it in out["ideas"]["tasks"][0]["result"][0].get("items") or []: add(it,"ideas")
for r in out["suggestions"]:
    for it in (r["tasks"][0]["result"] or [{}])[0].get("items") or []: add(it,"sugg")
for r in out["competitors"]:
    for it in (r["tasks"][0]["result"] or [{}])[0].get("items") or []: add(it["keyword_data"],"comp:"+r["tasks"][0]["result"][0]["target"])
print("unique keywords:",len(kws))
brands=r"stake ?mate|bet365|betfred|paddy ?power|william ?hill|coral|sky ?bet|sky ?vegas|ladbrokes|betfair|unibet|betway|virgin ?bet|midnite|talksport|bet442|goodwin|betvictor|888|mystake|databet|kwiff|betano|boylesports|tote|spreadex|betmgm|fanduel|draftkings|livescore|betgoodwin|pokerstars|fitzdares|matchbook|smarkets|bwin|grosvenor|mansion|casumo|leovegas|mr ?green|betuk|parimatch|1xbet|stake\.com|^stake$|bet uk|bet ?goodwin|luckster|netbet|vbet|bet ?fred|10bet|sportingbet|hollywoodbets|quinnbet|copybet|bresbet|dabble"
casino=r"casino|slot|spins|bingo|poker|roulette|blackjack|lottery|lotto|scratch"
bonushunt=r"no deposit|no wager|non ?uk|non gamstop|not on gamstop|nigeria|kenya|ghana|india|australia|usa"
info=r"tips|prediction|odds to|calculator|racecard|results|meaning|what is|how to|explained|rules|glossary|guide|strategy|jobs|news"
for e in kws.values():
    k=e["keyword"]
    if re.search(brands,k): e["bucket"]="competitor/brand"
    elif re.search(casino,k): e["bucket"]="casino (exclude)"
    elif re.search(bonushunt,k): e["bucket"]="bonus-hunter/offshore (exclude)"
    elif re.search(info,k): e["bucket"]="informational (exclude)"
    elif re.search(r"friend|mate|social|group|together|pool|syndicate",k): e["bucket"]="A social/bet-with-mates"
    elif re.search(r"app",k): e["bucket"]="B betting app"
    elif re.search(r"free bet|sign ?up|welcome|new customer|bonus|offer|promo",k): e["bucket"]="C offers/free bets"
    elif re.search(r"acca|accumulator|bet builder|build a bet|multiple",k): e["bucket"]="D acca/bet builder"
    elif re.search(r"football|premier league|championship|horse|racing|tennis|golf|cricket|darts|rugby|boxing|f1|nfl|nba|snooker|sport",k): e["bucket"]="E sport-specific"
    elif re.search(r"betting site|bookmaker|bookie|online betting|betting online|bet online|place a bet|new betting|best betting|betting compan|betting platform|uk betting",k): e["bucket"]="F generic betting/sites"
    else: e["bucket"]="G other"
rows=sorted(kws.values(),key=lambda e:-e["volume"])
with open("keywords_all.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["keyword","bucket","volume","cpc_usd","competition","intent","kd","sources"])
    for e in rows: w.writerow([e["keyword"],e["bucket"],e["volume"],e["cpc"],e["competition"],e["intent"],e["kd"],"|".join(sorted(e["src"]))])
from collections import Counter
c=Counter(); v=Counter()
for e in rows: c[e["bucket"]]+=1; v[e["bucket"]]+=e["volume"]
for b in sorted(c): print(f"{b:40s} n={c[b]:5d} vol={v[b]}")
print()
for b in ["A social/bet-with-mates","B betting app","C offers/free bets","D acca/bet builder","E sport-specific","F generic betting/sites","G other"]:
    print("=====",b)
    for e in [x for x in rows if x["bucket"]==b][:45]:
        print(f'{e["volume"]:>7} ${e["cpc"] or 0:<6} {e["intent"] or "":<14} {e["keyword"]}')
