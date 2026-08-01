#!/usr/bin/env python3
"""
Build a full SEO profile for a target domain (plus its organic competitors)
from the DataForSEO Labs + Backlinks APIs.

For the target it pulls:
  - domain rank overview (position distribution, ETV, traffic value)
  - historical rank overview (12-month trend)
  - ranked keywords split into page 1 / page 2 / page 3
  - backlinks summary, referring domains, anchors, top backlinks
  - organic competitors

For each of the top competitors it pulls:
  - domain rank overview
  - backlinks summary
  - top keywords by estimated traffic

Every response is cached to data/raw/<name>.json so re-runs cost nothing.
Flattened CSVs land in data/.

Auth comes from environment secrets:
  DATAFORSEO_LOGIN
  DATAFORSEO_PASSWORD

Usage:
  python3 seo_profile.py
"""
import os
import sys
import csv
import json
import base64
from pathlib import Path

import requests

BASE = "https://api.dataforseo.com/v3"

TARGET = "wassersfurniture.com"
LOCATION_CODE = 2840   # United States
LANGUAGE_CODE = "en"   # English

N_COMPETITORS = 6      # competitors profiled in depth
KW_LIMIT = 1000        # max keyword rows per page-bucket call
COMP_KW_LIMIT = 100    # top keywords pulled per competitor

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data"

# Google's SERP pages, expressed as organic rank_group ranges.
PAGES = {
    "page1": (1, 10),
    "page2": (11, 20),
    "page3": (21, 30),
}

_spend = 0.0


def auth_header():
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        sys.exit("ERROR: DATAFORSEO_LOGIN and/or DATAFORSEO_PASSWORD are not set "
                 "in the environment.")
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


HEADERS = None


def post(path, payload, cache_name):
    """POST to DataForSEO, caching the raw response so re-runs are free."""
    global _spend
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_DIR / f"{cache_name}.json"
    if cache_path.exists():
        print(f"  [cached] {cache_name}")
        return json.loads(cache_path.read_text())

    resp = requests.post(BASE + path, headers=HEADERS, json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status_code") != 20000:
        sys.exit(f"API error on {cache_name}: {data.get('status_message')}")
    task = data["tasks"][0]
    if task.get("status_code") != 20000:
        print(f"  !! task error on {cache_name}: {task.get('status_message')}")

    cache_path.write_text(json.dumps(data, indent=2))
    _spend += data.get("cost", 0) or 0
    print(f"  [fetched] {cache_name}  (${data.get('cost', 0):.5f})")
    return data


def result_items(data):
    """Pull the items list out of a DataForSEO response."""
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


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path.relative_to(ROOT)}  ({len(rows)} rows)")


# --------------------------------------------------------------------------
# Labs: keywords
# --------------------------------------------------------------------------

KW_FIELDS = ["keyword", "position", "rank_absolute", "search_volume", "etv",
             "keyword_difficulty", "cpc", "competition", "search_intent",
             "ranking_url", "serp_page"]


def flatten_keyword(item):
    kd = item.get("keyword_data") or {}
    ki = kd.get("keyword_info") or {}
    kp = kd.get("keyword_properties") or {}
    si = kd.get("search_intent_info") or {}
    serp = (item.get("ranked_serp_element") or {}).get("serp_item") or {}
    rank_group = serp.get("rank_group")
    page = None
    if rank_group:
        page = (rank_group - 1) // 10 + 1
    return {
        "keyword": kd.get("keyword"),
        "position": rank_group,
        "rank_absolute": serp.get("rank_absolute"),
        "search_volume": ki.get("search_volume"),
        "etv": round(serp.get("etv") or 0, 1),
        "keyword_difficulty": kp.get("keyword_difficulty"),
        "cpc": ki.get("cpc"),
        "competition": ki.get("competition"),
        "search_intent": si.get("main_intent"),
        "ranking_url": serp.get("url"),
        "serp_page": page,
    }


def fetch_ranked_keywords(domain, cache_name, rank_from=None, rank_to=None,
                          limit=KW_LIMIT):
    filters = [["ranked_serp_element.serp_item.type", "=", "organic"]]
    if rank_from is not None:
        filters += ["and", ["ranked_serp_element.serp_item.rank_group", ">=", rank_from]]
    if rank_to is not None:
        filters += ["and", ["ranked_serp_element.serp_item.rank_group", "<=", rank_to]]

    payload = [{
        "target": domain,
        "location_code": LOCATION_CODE,
        "language_code": LANGUAGE_CODE,
        "limit": limit,
        "order_by": ["ranked_serp_element.serp_item.etv,desc"],
        "filters": filters,
    }]
    data = post("/dataforseo_labs/google/ranked_keywords/live", payload, cache_name)
    rows = [flatten_keyword(i) for i in result_items(data)]
    rows.sort(key=lambda r: (r["etv"] or 0, r["search_volume"] or 0), reverse=True)
    return rows


# --------------------------------------------------------------------------
# Labs: overview + competitors
# --------------------------------------------------------------------------

def fetch_overview(domain, cache_name):
    payload = [{"target": domain, "location_code": LOCATION_CODE,
                "language_code": LANGUAGE_CODE}]
    data = post("/dataforseo_labs/google/domain_rank_overview/live", payload, cache_name)
    items = result_items(data)
    if not items:
        return {}
    return (items[0].get("metrics") or {}).get("organic") or {}


def fetch_history(domain, cache_name):
    payload = [{"target": domain, "location_code": LOCATION_CODE,
                "language_code": LANGUAGE_CODE}]
    data = post("/dataforseo_labs/google/historical_rank_overview/live",
                payload, cache_name)
    rows = []
    for item in result_items(data):
        org = (item.get("metrics") or {}).get("organic") or {}
        rows.append({
            "year": item.get("year"),
            "month": item.get("month"),
            "keywords": org.get("count"),
            "etv": round(org.get("etv") or 0, 1),
            "traffic_value_usd": round(org.get("estimated_paid_traffic_cost") or 0, 2),
            "pos_1": org.get("pos_1"),
            "pos_2_3": org.get("pos_2_3"),
            "pos_4_10": org.get("pos_4_10"),
        })
    rows.sort(key=lambda r: (r["year"] or 0, r["month"] or 0))
    return rows


def fetch_competitors(domain, cache_name, limit=25):
    payload = [{
        "target": domain,
        "location_code": LOCATION_CODE,
        "language_code": LANGUAGE_CODE,
        "limit": limit,
        "exclude_top_domains": False,
        "order_by": ["intersections,desc"],
    }]
    data = post("/dataforseo_labs/google/competitors_domain/live", payload, cache_name)
    rows = []
    for item in result_items(data):
        org = ((item.get("metrics") or {}).get("organic") or {})
        rows.append({
            "domain": item.get("domain"),
            "shared_keywords": item.get("intersections"),
            "competitor_rank": item.get("competitor_metrics") and None,
            "organic_keywords": org.get("count"),
            "organic_traffic_est": round(org.get("etv") or 0, 1),
            "traffic_value_usd": round(org.get("estimated_paid_traffic_cost") or 0, 2),
            "pos_1": org.get("pos_1"),
            "pos_2_3": org.get("pos_2_3"),
            "pos_4_10": org.get("pos_4_10"),
        })
    return rows


# --------------------------------------------------------------------------
# Backlinks API
# --------------------------------------------------------------------------

def fetch_backlink_summary(domain, cache_name):
    payload = [{"target": domain, "internal_list_limit": 10,
                "include_subdomains": True, "backlinks_status_type": "live"}]
    data = post("/backlinks/summary/live", payload, cache_name)
    return first_result(data)


def fetch_referring_domains(domain, cache_name, limit=100):
    payload = [{
        "target": domain,
        "limit": limit,
        "include_subdomains": True,
        "backlinks_status_type": "live",
        "order_by": ["rank,desc"],
    }]
    data = post("/backlinks/referring_domains/live", payload, cache_name)
    rows = []
    for item in result_items(data):
        rows.append({
            "referring_domain": item.get("domain"),
            "domain_rank": item.get("rank"),
            "backlinks": item.get("backlinks"),
            "dofollow": item.get("backlinks") and (item.get("backlinks") - (item.get("nofollow") or 0)),
            "nofollow": item.get("nofollow"),
            "first_seen": item.get("first_seen"),
            "lost_date": item.get("lost_date"),
            "referring_pages": item.get("referring_pages"),
            "country": item.get("country"),
            "is_broken": item.get("broken_backlinks"),
        })
    return rows


def fetch_anchors(domain, cache_name, limit=100):
    payload = [{
        "target": domain,
        "limit": limit,
        "include_subdomains": True,
        "backlinks_status_type": "live",
        "order_by": ["backlinks,desc"],
    }]
    data = post("/backlinks/anchors/live", payload, cache_name)
    rows = []
    for item in result_items(data):
        rows.append({
            "anchor": item.get("anchor"),
            "backlinks": item.get("backlinks"),
            "referring_domains": item.get("referring_domains"),
            "dofollow_backlinks": item.get("backlinks") and (item.get("backlinks") - (item.get("nofollow") or 0)),
            "first_seen": item.get("first_seen"),
        })
    return rows


def fetch_backlinks(domain, cache_name, limit=200):
    payload = [{
        "target": domain,
        "limit": limit,
        "include_subdomains": True,
        "backlinks_status_type": "live",
        "mode": "one_per_domain",
        "order_by": ["rank,desc"],
    }]
    data = post("/backlinks/backlinks/live", payload, cache_name)
    rows = []
    for item in result_items(data):
        rows.append({
            "source_url": item.get("url_from"),
            "source_domain": item.get("domain_from"),
            "target_url": item.get("url_to"),
            "page_rank": item.get("page_from_rank"),
            "domain_rank": item.get("domain_from_rank"),
            "anchor": item.get("anchor"),
            "dofollow": item.get("dofollow"),
            "link_type": item.get("item_type"),
            "first_seen": item.get("first_seen"),
            "last_seen": item.get("last_seen"),
            "is_lost": item.get("is_lost"),
            "source_country": item.get("domain_from_country"),
        })
    return rows


def summarize_backlinks(summary):
    """Reduce a /backlinks/summary result to the headline numbers."""
    if not summary:
        return {}
    return {
        "domain_rank": summary.get("rank"),
        "backlinks": summary.get("backlinks"),
        "referring_domains": summary.get("referring_domains"),
        "referring_main_domains": summary.get("referring_main_domains"),
        "referring_ips": summary.get("referring_ips"),
        "referring_pages": summary.get("referring_pages"),
        "dofollow_backlinks": summary.get("backlinks", 0) - (summary.get("referring_links_attributes", {}) or {}).get("nofollow", 0),
        "nofollow_backlinks": (summary.get("referring_links_attributes", {}) or {}).get("nofollow"),
        "broken_backlinks": summary.get("broken_backlinks"),
        "broken_pages": summary.get("broken_pages"),
        "referring_domains_nofollow": summary.get("referring_domains_nofollow"),
        "internal_links_count": summary.get("internal_links_count"),
        "external_links_count": summary.get("external_links_count"),
        "crawled_pages": summary.get("crawled_pages"),
        "first_seen": summary.get("first_seen"),
        "lost_backlinks_last_30d": (summary.get("backlinks_spam_score") and None),
        "spam_score": summary.get("backlinks_spam_score"),
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def slug(domain):
    return domain.replace(".", "_").replace("/", "_")


def main():
    global HEADERS
    HEADERS = auth_header()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    profile = {"target": TARGET, "location_code": LOCATION_CODE,
               "language_code": LANGUAGE_CODE}

    # ---------- target: organic overview ----------
    print(f"\n=== {TARGET}: organic overview ===")
    profile["overview"] = fetch_overview(TARGET, "overview_target")

    print(f"\n=== {TARGET}: historical trend ===")
    history = fetch_history(TARGET, "history_target")
    profile["history"] = history
    if history:
        write_csv(OUT_DIR / "target_history.csv", history, list(history[0].keys()))

    # ---------- target: keywords by SERP page ----------
    all_kw = []
    for name, (lo, hi) in PAGES.items():
        print(f"\n=== {TARGET}: keywords {name} (positions {lo}-{hi}) ===")
        rows = fetch_ranked_keywords(TARGET, f"kw_target_{name}", lo, hi)
        profile.setdefault("keyword_counts", {})[name] = len(rows)
        all_kw.extend(rows)
        write_csv(OUT_DIR / f"target_keywords_{name}.csv", rows, KW_FIELDS)
    write_csv(OUT_DIR / "target_keywords_all.csv", all_kw, KW_FIELDS)

    # ---------- target: backlinks ----------
    print(f"\n=== {TARGET}: backlinks ===")
    bl_summary = fetch_backlink_summary(TARGET, "backlinks_summary_target")
    profile["backlinks"] = summarize_backlinks(bl_summary)

    ref_domains = fetch_referring_domains(TARGET, "refdomains_target")
    if ref_domains:
        write_csv(OUT_DIR / "target_referring_domains.csv", ref_domains,
                  list(ref_domains[0].keys()))

    anchors = fetch_anchors(TARGET, "anchors_target")
    if anchors:
        write_csv(OUT_DIR / "target_anchors.csv", anchors, list(anchors[0].keys()))

    backlinks = fetch_backlinks(TARGET, "backlinks_target")
    if backlinks:
        write_csv(OUT_DIR / "target_backlinks.csv", backlinks,
                  list(backlinks[0].keys()))

    # ---------- competitors ----------
    print(f"\n=== {TARGET}: organic competitors ===")
    competitors = fetch_competitors(TARGET, "competitors_target")
    competitors = [c for c in competitors if c["domain"] != TARGET]
    if competitors:
        write_csv(OUT_DIR / "competitors_overview.csv", competitors,
                  list(competitors[0].keys()))
    profile["competitors"] = competitors

    top_comps = competitors[:N_COMPETITORS]
    comp_detail = []
    for c in top_comps:
        d = c["domain"]
        print(f"\n--- competitor: {d} ---")
        s = slug(d)
        cbl = summarize_backlinks(fetch_backlink_summary(d, f"backlinks_summary_{s}"))
        ckw = fetch_ranked_keywords(d, f"kw_{s}", 1, 10, limit=COMP_KW_LIMIT)
        write_csv(OUT_DIR / f"competitor_keywords_{s}.csv", ckw, KW_FIELDS)
        comp_detail.append({
            "domain": d,
            "shared_keywords": c["shared_keywords"],
            "organic_keywords": c["organic_keywords"],
            "organic_traffic_est": c["organic_traffic_est"],
            "traffic_value_usd": c["traffic_value_usd"],
            "backlinks": cbl,
            "top_keywords": ckw[:25],
        })
    profile["competitor_detail"] = comp_detail

    # comparison table across target + competitors
    comparison = [{
        "domain": TARGET,
        "organic_keywords": profile["overview"].get("count"),
        "organic_traffic_est": round(profile["overview"].get("etv") or 0, 1),
        "traffic_value_usd": round(profile["overview"].get("estimated_paid_traffic_cost") or 0, 2),
        "domain_rank": profile["backlinks"].get("domain_rank"),
        "backlinks": profile["backlinks"].get("backlinks"),
        "referring_domains": profile["backlinks"].get("referring_domains"),
        "shared_keywords": None,
    }]
    for c in comp_detail:
        comparison.append({
            "domain": c["domain"],
            "organic_keywords": c["organic_keywords"],
            "organic_traffic_est": c["organic_traffic_est"],
            "traffic_value_usd": c["traffic_value_usd"],
            "domain_rank": c["backlinks"].get("domain_rank"),
            "backlinks": c["backlinks"].get("backlinks"),
            "referring_domains": c["backlinks"].get("referring_domains"),
            "shared_keywords": c["shared_keywords"],
        })
    write_csv(OUT_DIR / "comparison.csv", comparison, list(comparison[0].keys()))
    profile["comparison"] = comparison

    (OUT_DIR / "profile.json").write_text(json.dumps(profile, indent=2))
    print(f"\nWrote {(OUT_DIR / 'profile.json').relative_to(ROOT)}")
    print(f"Total spend this run: ${_spend:.4f}")


if __name__ == "__main__":
    main()
