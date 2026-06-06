#!/usr/bin/env python3
"""
Reality-check the page plan against live Google SERPs.

For each proposed page we pull the actual SERP for its top keywords and judge
winnability by WHO RANKS, not by DataForSEO's KD:
  - PEER  = a DTC bedding/home-textile brand of similar authority to SC. If peers
            rank, SC can realistically rank too.
  - HARD  = Amazon/Walmart/Wayfair/big-box + major publishers (Wirecutter, etc.).
            A SERP wall of these means low winnability regardless of KD.

Winnability (SERP):
  high   -> peers routinely rank (>=2 peers across the page's top keywords on avg,
            or SC already ranks top-10)
  medium -> a peer shows up but the SERP is mixed/retail-heavy
  low    -> peers absent; owned by mega-retail + publishers

Realistic traffic replaces the naive "#3 for everything": total page demand x a
capture rate set by SERP winnability (high 8%, medium 2.5%, low 0.4%).

Product-gap pages (no SC product, e.g. flannel/percale) are dropped.

Input:  data/keyword_gap_pages.csv
Output: data/page_plan.csv   (rewritten, realistic)
        data/raw_serp_winnability.json  (per-keyword SERP cache)

Auth: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD
  REFILTER=1   rebuild from cached SERPs (no API calls)
"""
import os, csv, json, sys, base64
from pathlib import Path

import requests

SERP_URL = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
LOCATION_CODE = 2840
LANGUAGE_CODE = "en"
KWS_PER_PAGE = 3        # top keywords per page to SERP-check
TOP_N_ORGANIC = 10      # judge winnability on the top-10 organic results

HERE = Path(__file__).parent
DATA = HERE / "data"
PAGES_CSV = DATA / "keyword_gap_pages.csv"
RAW = DATA / "raw_serp_winnability.json"
OUT = DATA / "page_plan.csv"
COLLECTIONS = DATA / "sc_collections.json"

# DTC bedding / home-textile brands of comparable authority to Sunday Citizen.
# If one of these ranks, the SERP is reachable for a focused SC page.
PEERS = {
    "sundaycitizen.co", "brooklinen.com", "parachutehome.com", "coyuchi.com",
    "sheetsociety.com", "pigletinbed.com", "us.pigletinbed.com", "bedsurehome.com",
    "magiclinen.com", "snowe.com", "cozyearth.com", "ettitude.com", "buffy.co",
    "peacockalley.com", "quince.com", "bollandbranch.com", "boll-and-branch.com",
    "garnethill.com", "thecitizenry.com", "nestbedding.com", "plutopillow.com",
    "bearaby.com", "baloo-living.com", "balooliving.com", "luxome.com",
    "sijohome.com", "sijo.co", "rileyhome.com", "saatva.com", "loomandleaf.com",
    "tuft.com", "tuftandneedle.com", "sheex.com", "slipsilkpillowcase.com",
    "blissy.com", "cariloha.com", "linenme.com", "rough-linen.com",
    "thecompanystore.com", "annieselke.com", "pureparima.com", "lolablankets.com",
    "softminkyblankets.com", "sandcloud.com", "doraihome.com", "pigletinbed.co.uk",
    "weighted blankets", "gravityblankets.com", "yourlauralake.com",
}
# Mega-retail, marketplaces, big-box home, and major publishers (hard to outrank)
HARD = {
    "amazon.com", "walmart.com", "target.com", "wayfair.com", "overstock.com",
    "homedepot.com", "lowes.com", "costco.com", "ebay.com", "etsy.com",
    "macys.com", "bedbathandbeyond.com", "kohls.com", "jcpenney.com",
    "nordstrom.com", "bloomingdales.com", "ikea.com", "potterybarn.com",
    "westelm.com", "crateandbarrel.com", "cb2.com", "anthropologie.com",
    "urbanoutfitters.com", "qvc.com", "hsn.com", "biglots.com", "ross.com",
    "tjmaxx.com", "homegoods.com", "wfcdn.com", "containerstore.com",
    "dillards.com", "belk.com", "kirklands.com", "worldmarket.com",
    "nytimes.com", "wirecutter.com", "goodhousekeeping.com", "forbes.com",
    "cnn.com", "sleepfoundation.org", "sleepopolis.com", "mattressclarity.com",
    "realsimple.com", "bhg.com", "housebeautiful.com", "architecturaldigest.com",
    "thespruce.com", "today.com", "people.com", "businessinsider.com", "cnet.com",
    "tomsguide.com", "wikipedia.org", "en.wikipedia.org", "reddit.com",
    "quora.com", "youtube.com", "instagram.com", "pinterest.com", "tiktok.com",
    "usatoday.com", "nbcnews.com", "marthastewart.com", "apartmenttherapy.com",
    "elle.com", "vogue.com", "nymag.com", "rollingstone.com",
}

# realistic share of the page's total cluster demand captured once the page
# ranks as well as the SERP allows (conservative, not a #3-everywhere fantasy).
CAPTURE = {"high": 0.06, "medium": 0.018, "low": 0.003}


def norm_domain(d):
    d = (d or "").lower().strip()
    return d[4:] if d.startswith("www.") else d


def auth_header():
    login, pw = os.environ.get("DATAFORSEO_LOGIN"), os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not pw:
        sys.exit("ERROR: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set.")
    tok = base64.b64encode(f"{login}:{pw}".encode()).decode()
    return {"Authorization": f"Basic {tok}", "Content-Type": "application/json"}


def serp_domains(resp):
    """Top-N organic domains, in rank order."""
    doms = []
    for t in (resp.get("tasks") or []):
        for r in (t.get("result") or []):
            for it in (r.get("items") or []):
                if it.get("type") == "organic" and it.get("domain"):
                    doms.append(norm_domain(it["domain"]))
    return doms[:TOP_N_ORGANIC]


def existing_handles():
    data = json.loads(COLLECTIONS.read_text())
    return {h for _, h, _ in data["collections"]}


def classify_page(url, existing):
    if url.startswith("/collections/"):
        return "Optimise" if url.rsplit("/", 1)[-1] in existing else "New"
    return "New"


def main():
    rows = [r for r in csv.DictReader(PAGES_CSV.open())
            if "no current line" not in r["sc_product_line"]]
    print(f"pages to evaluate: {len(rows)} (dropped product-gap pages)")

    # collect the top keywords to SERP-check
    page_kws = {}
    need = []
    for r in rows:
        kws = [k for k in r["example_keywords"].split(" | ") if k][:KWS_PER_PAGE]
        page_kws[r["target_url"]] = kws
        need.extend(kws)
    need = list(dict.fromkeys(need))  # dedupe, keep order

    cache = json.loads(RAW.read_text()) if RAW.exists() else {}
    if os.environ.get("REFILTER"):
        print(f"REFILTER: using {len(cache)} cached SERPs, no API calls")
    else:
        headers = auth_header()
        todo = [k for k in need if k not in cache]
        print(f"keywords to pull: {len(todo)} (of {len(need)}; {len(cache)} cached)")
        for i, kw in enumerate(todo, 1):
            payload = [{"keyword": kw, "location_code": LOCATION_CODE,
                        "language_code": LANGUAGE_CODE, "depth": 20}]
            try:
                resp = requests.post(SERP_URL, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                cache[kw] = serp_domains(resp.json())
            except Exception as e:
                print(f"  ! {kw}: {e}")
                cache[kw] = []
            if i % 25 == 0:
                RAW.write_text(json.dumps(cache))
                print(f"  {i}/{len(todo)}")
        RAW.write_text(json.dumps(cache))

    existing = existing_handles()
    out = []
    for r in rows:
        kws = page_kws[r["target_url"]]
        peer_counts, hard_counts, reach_flags = [], [], []
        sc_ranks, peers_seen, hard_seen, others_seen = False, set(), set(), set()
        for kw in kws:
            doms = cache.get(kw, [])
            if not doms:
                continue
            pc = hc = 0
            for d in doms:
                if d in PEERS:
                    pc += 1
                    if d == "sundaycitizen.co":
                        sc_ranks = True
                    else:
                        peers_seen.add(d)
                elif d in HARD:
                    hc += 1
                    hard_seen.add(d)
                else:
                    others_seen.add(d)        # small/unknown brands = beatable
            peer_counts.append(pc)
            hard_counts.append(hc)
            # reachable: a peer ranks, OR the top-10 isn't a retail/publisher wall
            reach_flags.append(1 if (pc >= 1 or hc <= 3) else 0)

        n = len(peer_counts) or 1
        avg_peer = sum(peer_counts) / n
        avg_hard = sum(hard_counts) / n
        reach = sum(reach_flags) / n
        head_vol = int(r.get("head_keyword_volume") or 0)

        # Winnability for a mid-authority DTC brand. A reachable SERP (peers rank
        # / not a retail wall) is necessary but NOT sufficient: brand-defining
        # head terms ("sheets" 2.2M) stay hard even when peers eventually rank,
        # so big head volumes cap winnability down.
        reachable = avg_peer >= 1 or reach >= 0.66
        wall = avg_hard >= 6
        if sc_ranks and head_vol < 200000:
            win = "high"
        elif wall or head_vol >= 500000:
            win = "low"
        elif reachable and avg_hard <= 3 and head_vol < 100000:
            win = "high"
        elif head_vol >= 150000 and not reachable:
            win = "low"
        else:
            win = "medium"

        vol = int(r["total_search_volume"])
        realistic = round(vol * CAPTURE[win])
        evidence_peers = ", ".join(sorted(peers_seen)[:3]) or \
            (", ".join(sorted(others_seen)[:2]) + " (small brands)" if others_seen else "none")
        evidence_hard = ", ".join(sorted(hard_seen)[:3]) or "none"
        serp_reality = f"peers: {evidence_peers} | walls: {evidence_hard}"
        if sc_ranks:
            serp_reality = "SC already in top-10 | " + serp_reality

        out.append({
            "Page": r["target_page_title"],
            "New / Optimise": classify_page(r["target_url"], existing),
            "Current / Proposed URL": "https://sundaycitizen.co" + r["target_url"],
            "SC Product Line": r["sc_product_line"],
            "To Rank For": ", ".join(r["example_keywords"].split(" | ")),
            "Monthly Search Volume": vol,
            "Traffic Potential @#3 (ceiling)": int(r["expected_traffic_pos3"]),
            "Winnability (SERP)": win,
            "SERP Reality": serp_reality,
            "Realistic Traffic /mo": realistic,
        })

    out.sort(key=lambda x: x["Realistic Traffic /mo"], reverse=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT}  ({len(out)} pages)")
    from collections import Counter
    print("  winnability:", dict(Counter(r["Winnability (SERP)"] for r in out)))


if __name__ == "__main__":
    main()
