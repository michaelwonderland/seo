#!/usr/bin/env python3
"""
Phase 2 of the Wasser's Furniture SEO profile.

1. Finds the pages on the target that still hold backlinks but now 404
   (link equity lost in the replatform).
2. Sizes the South Florida luxury-furniture keyword market.
3. Identifies who actually owns those SERPs (real competitors, not the
   social/marketplace noise that domain-overlap returns).
4. Pulls a full, like-for-like profile for each real competitor:
   organic overview, backlink summary, and top keywords.

Responses are cached to data/raw/ so re-runs cost nothing.

Usage:
  python3 competitive_analysis.py
"""
import os
import sys
import csv
import json
import time
import base64
from pathlib import Path

import requests

BASE = "https://api.dataforseo.com/v3"
TARGET = "wassersfurniture.com"
LOCATION_CODE = 2840
LANGUAGE_CODE = "en"

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data"

# The commercial terms a South Florida luxury furniture retailer should own.
SEED_KEYWORDS = [
    "furniture stores miami", "luxury furniture miami", "italian furniture miami",
    "modern furniture miami", "contemporary furniture miami", "high end furniture miami",
    "designer furniture miami", "custom furniture miami",
    "furniture stores fort lauderdale", "luxury furniture fort lauderdale",
    "italian furniture fort lauderdale", "modern furniture fort lauderdale",
    "furniture stores hallandale", "furniture stores aventura",
    "furniture stores hollywood fl", "furniture stores sunny isles",
    "luxury furniture store", "italian furniture store", "high end furniture store",
    "modern furniture store near me", "sectional sofas miami", "dining room sets miami",
    "bedroom furniture miami", "outdoor furniture miami", "office furniture miami",
    "interior design miami", "furniture showroom miami", "european furniture miami",
]

# Domains that show up in overlap but are not furniture-retail competitors:
# social, marketplaces, directories and lead-gen aggregators.
NOISE = {
    "youtube.com", "instagram.com", "facebook.com", "pinterest.com", "yelp.com",
    "amazon.com", "ebay.com", "walmart.com", "wayfair.com", "macys.com",
    "bloomingdales.com", "houzz.com", "reddit.com", "tiktok.com", "etsy.com",
    "target.com", "overstock.com", "homedepot.com", "lowes.com", "costco.com",
    "linkedin.com", "mapquest.com", "yellowpages.com", "tripadvisor.com",
    "apartmenttherapy.com", "architecturaldigest.com", "nytimes.com",
    "furniture.com", "decorilla.com", "miamidesigndistrict.com",
    "thecurated.group", "thebrowarddesigncenter.com",
}

# The retailers Wasser's actually competes with in the South Florida market.
# Data-driven (top of the SERP-competitor table) plus the two largest regional
# players, which rank locally but sit outside the seed-keyword sample.
CURATED_COMPETITORS = [
    "modernmiami.com",        # Modern Miami - top organic winner on the money terms
    "addisonhouse.com",       # Addison House - luxury, Aventura/Miami
    "mh2g.com",               # MH2G - modern furniture Miami
    "scandesign.com",         # Scan Design - FL chain
    "camerichmiami.com",      # Camerich Miami - contemporary
    "habitusfurniture.com",   # Habitus - contemporary Miami
    "baers.com",              # Baer's Furniture - major FL chain
    "cityfurniture.com",      # City Furniture - largest FL chain
    "eldoradofurniture.com",  # El Dorado Furniture - major FL chain
    "modani.com",             # Modani - modern, Miami-founded
]

_spend = 0.0
HEADERS = None


def auth_header():
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        sys.exit("ERROR: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set.")
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def post(path, payload, cache_name, retries=3):
    global _spend
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_DIR / f"{cache_name}.json"
    if cache_path.exists():
        print(f"  [cached] {cache_name}")
        return json.loads(cache_path.read_text())

    for attempt in range(retries):
        resp = requests.post(BASE + path, headers=HEADERS, json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        task = (data.get("tasks") or [{}])[0]
        if data.get("status_code") == 20000 and task.get("status_code") == 20000:
            break
        print(f"  .. retry {attempt+1} on {cache_name}: {task.get('status_message')}")
        time.sleep(4)

    cache_path.write_text(json.dumps(data, indent=2))
    _spend += data.get("cost", 0) or 0
    print(f"  [fetched] {cache_name}  (${data.get('cost', 0):.5f})")
    return data


def items_of(data):
    out = []
    for task in data.get("tasks") or []:
        for result in (task.get("result") or []):
            out.extend(result.get("items") or [])
    return out


def first_result(data):
    for task in data.get("tasks") or []:
        for result in (task.get("result") or []):
            return result
    return {}


def write_csv(path, rows, fields=None):
    if not rows:
        print(f"  (no rows for {path.name})")
        return
    fields = fields or list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path.relative_to(ROOT)}  ({len(rows)} rows)")


# --------------------------------------------------------------------------
# 1. Broken pages that still hold backlinks
# --------------------------------------------------------------------------

def broken_link_equity():
    print("\n=== Pages with backlinks, by status ===")
    # domain_pages rejects order_by, so pull a wide slice and sort locally.
    payload = [{
        "target": TARGET,
        "limit": 1000,
        "include_subdomains": True,
        "backlinks_status_type": "live",
    }]
    data = post("/backlinks/domain_pages/live", payload, "backlink_pages_target")
    rows = []
    for it in items_of(data):
        meta = it.get("meta") or {}
        ps = it.get("page_summary") or {}
        rows.append({
            "page": it.get("page"),
            "status_code": it.get("status_code"),
            "redirects_to": it.get("location"),
            "backlinks": ps.get("backlinks"),
            "referring_domains": ps.get("referring_domains"),
            "referring_main_domains": ps.get("referring_main_domains"),
            "page_rank": ps.get("rank"),
            "spam_score": ps.get("backlinks_spam_score"),
            "title": meta.get("title"),
            "first_seen": ps.get("first_seen"),
            "last_visited": it.get("fetch_time"),
        })
    rows.sort(key=lambda r: (r["referring_domains"] or 0, r["backlinks"] or 0),
              reverse=True)
    write_csv(OUT_DIR / "target_pages_by_backlinks.csv", rows)

    dead = [r for r in rows if r["status_code"] and int(r["status_code"]) >= 400]
    alive = [r for r in rows if r["status_code"] and int(r["status_code"]) < 300]
    unknown = [r for r in rows if not r["status_code"]]
    print(f"  pages with links: {len(rows)}")
    print(f"    live (2xx):   {len(alive):>4}  links={sum(r['backlinks'] or 0 for r in alive)}"
          f"  refdomains={sum(r['referring_domains'] or 0 for r in alive)}")
    print(f"    broken (4xx+):{len(dead):>4}  links={sum(r['backlinks'] or 0 for r in dead)}"
          f"  refdomains={sum(r['referring_domains'] or 0 for r in dead)}")
    print(f"    unknown:      {len(unknown):>4}")
    write_csv(OUT_DIR / "target_broken_pages_with_links.csv",
              sorted(dead, key=lambda r: r["referring_domains"] or 0, reverse=True))
    return rows, dead


# --------------------------------------------------------------------------
# 2. Market sizing on the seed keywords
# --------------------------------------------------------------------------

def market_keywords():
    print("\n=== Seed keyword volumes (South Florida luxury furniture) ===")
    payload = [{
        "keywords": SEED_KEYWORDS,
        "location_code": LOCATION_CODE,
        "language_code": LANGUAGE_CODE,
    }]
    data = post("/dataforseo_labs/google/bulk_keyword_difficulty/live",
                [{"keywords": SEED_KEYWORDS, "location_code": LOCATION_CODE,
                  "language_code": LANGUAGE_CODE}], "seed_kd")
    kd_map = {i.get("keyword"): i.get("keyword_difficulty") for i in items_of(data)}

    sv = post("/keywords_data/google_ads/search_volume/live", payload, "seed_volume")
    rows = []
    for it in items_of(sv) or (first_result(sv) if isinstance(first_result(sv), list) else []):
        rows.append({
            "keyword": it.get("keyword"),
            "search_volume": it.get("search_volume"),
            "cpc": it.get("cpc"),
            "competition": it.get("competition"),
            "keyword_difficulty": kd_map.get(it.get("keyword")),
        })
    # google_ads search_volume returns results directly, not under items
    if not rows:
        for task in sv.get("tasks") or []:
            for it in (task.get("result") or []):
                rows.append({
                    "keyword": it.get("keyword"),
                    "search_volume": it.get("search_volume"),
                    "cpc": it.get("cpc"),
                    "competition": it.get("competition"),
                    "keyword_difficulty": kd_map.get(it.get("keyword")),
                })
    rows.sort(key=lambda r: r["search_volume"] or 0, reverse=True)
    write_csv(OUT_DIR / "market_seed_keywords.csv", rows)
    return rows


# --------------------------------------------------------------------------
# 3. Who actually owns those SERPs
# --------------------------------------------------------------------------

def serp_competitors(seed_rows):
    print("\n=== SERP competitors on the money keywords ===")
    kws = [r["keyword"] for r in seed_rows if (r["search_volume"] or 0) > 0][:20]
    payload = [{
        "keywords": kws,
        "location_code": LOCATION_CODE,
        "language_code": LANGUAGE_CODE,
        "limit": 100,
        "order_by": ["median_position,asc"],
    }]
    data = post("/dataforseo_labs/google/serp_competitors/live", payload, "serp_competitors")
    rows = []
    for it in items_of(data):
        rows.append({
            "domain": it.get("domain"),
            "keywords_ranked": it.get("keywords_count"),
            "median_position": it.get("median_position"),
            "visibility": round(it.get("visibility") or 0, 4),
            "relevant_serp_items": it.get("relevant_serp_items"),
        })
    # Rank by how much of the money-keyword set a domain owns, not by median
    # position - otherwise a site that ranks #1 for one obscure term outranks
    # a site that owns a dozen head terms.
    rows.sort(key=lambda r: (r["keywords_ranked"] or 0, r["visibility"] or 0),
              reverse=True)
    write_csv(OUT_DIR / "serp_competitors_raw.csv", rows)

    def root(d):
        return d[4:] if d.startswith("www.") else d

    real = [r for r in rows
            if root(r["domain"]) not in NOISE and root(r["domain"]) != TARGET]
    return rows, real


# --------------------------------------------------------------------------
# 4. Full like-for-like profile per competitor
# --------------------------------------------------------------------------

KW_FIELDS = ["keyword", "position", "search_volume", "etv", "keyword_difficulty",
             "cpc", "search_intent", "ranking_url"]


def flatten_keyword(item):
    kd = item.get("keyword_data") or {}
    ki = kd.get("keyword_info") or {}
    kp = kd.get("keyword_properties") or {}
    si = kd.get("search_intent_info") or {}
    serp = (item.get("ranked_serp_element") or {}).get("serp_item") or {}
    return {
        "keyword": kd.get("keyword"),
        "position": serp.get("rank_group"),
        "search_volume": ki.get("search_volume"),
        "etv": round(serp.get("etv") or 0, 1),
        "keyword_difficulty": kp.get("keyword_difficulty"),
        "cpc": ki.get("cpc"),
        "search_intent": si.get("main_intent"),
        "ranking_url": serp.get("url"),
    }


def slug(d):
    return d.replace(".", "_").replace("/", "_").replace("-", "_")


def profile_domain(domain):
    s = slug(domain)
    ov = post("/dataforseo_labs/google/domain_rank_overview/live",
              [{"target": domain, "location_code": LOCATION_CODE,
                "language_code": LANGUAGE_CODE}], f"ov_{s}")
    items = items_of(ov)
    organic = ((items[0].get("metrics") or {}).get("organic") or {}) if items else {}

    bl = post("/backlinks/summary/live",
              [{"target": domain, "internal_list_limit": 5,
                "include_subdomains": True, "backlinks_status_type": "live"}],
              f"bl_{s}")
    bls = first_result(bl)

    kw = post("/dataforseo_labs/google/ranked_keywords/live",
              [{"target": domain, "location_code": LOCATION_CODE,
                "language_code": LANGUAGE_CODE, "limit": 100,
                "order_by": ["ranked_serp_element.serp_item.etv,desc"],
                "filters": [["ranked_serp_element.serp_item.type", "=", "organic"], "and",
                            ["ranked_serp_element.serp_item.rank_group", "<=", 10]]}],
              f"kw_{s}")
    kws = [flatten_keyword(i) for i in items_of(kw)]
    kws.sort(key=lambda r: r["etv"] or 0, reverse=True)
    write_csv(OUT_DIR / f"competitor_kw_{s}.csv", kws, KW_FIELDS)

    return {
        "domain": domain,
        "organic_keywords": organic.get("count"),
        "organic_traffic_est": round(organic.get("etv") or 0, 1),
        "traffic_value_usd": round(organic.get("estimated_paid_traffic_cost") or 0, 2),
        "pos_1": organic.get("pos_1"),
        "pos_2_3": organic.get("pos_2_3"),
        "pos_4_10": organic.get("pos_4_10"),
        "pos_11_20": organic.get("pos_11_20"),
        "pos_21_30": organic.get("pos_21_30"),
        "keywords_lost": organic.get("is_lost"),
        "keywords_new": organic.get("is_new"),
        "domain_rank": bls.get("rank"),
        "backlinks": bls.get("backlinks"),
        "referring_domains": bls.get("referring_domains"),
        "referring_main_domains": bls.get("referring_main_domains"),
        "referring_ips": bls.get("referring_ips"),
        "spam_score": bls.get("backlinks_spam_score"),
        "broken_pages": bls.get("broken_pages"),
        "crawled_pages": bls.get("crawled_pages"),
        "first_seen": bls.get("first_seen"),
        "top_keywords": kws[:20],
    }


def main():
    global HEADERS
    HEADERS = auth_header()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pages, dead = broken_link_equity()
    seeds = market_keywords()
    raw_comp, real_comp = serp_competitors(seeds)

    print("\n=== SERP competitors, by share of the money-keyword set ===")
    for c in real_comp[:15]:
        print(f"  {c['domain']:<34} kws={c['keywords_ranked']:<4} "
              f"median_pos={c['median_position']}  vis={c['visibility']}")

    print("\n=== Curated competitor shortlist ===")
    shortlist = CURATED_COMPETITORS
    for d in shortlist:
        print(f"  {d}")

    print("\n=== Profiling target + competitors ===")
    profiles = [profile_domain(TARGET)]
    for d in shortlist:
        print(f"\n--- {d} ---")
        profiles.append(profile_domain(d))

    cmp_fields = ["domain", "organic_keywords", "organic_traffic_est",
                  "traffic_value_usd", "pos_1", "pos_2_3", "pos_4_10",
                  "pos_11_20", "pos_21_30", "keywords_new", "keywords_lost",
                  "domain_rank", "backlinks", "referring_domains",
                  "referring_main_domains", "spam_score", "crawled_pages"]
    write_csv(OUT_DIR / "competitor_comparison.csv", profiles, cmp_fields)

    (OUT_DIR / "competitive.json").write_text(json.dumps({
        "target": TARGET,
        "broken_pages_with_links": dead,
        "seed_keywords": seeds,
        "serp_competitors_raw": raw_comp,
        "profiles": profiles,
    }, indent=2))
    print(f"\nWrote data/competitive.json")
    print(f"Total spend this run: ${_spend:.4f}")


if __name__ == "__main__":
    main()
