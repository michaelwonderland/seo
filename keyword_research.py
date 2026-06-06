#!/usr/bin/env python3
"""
Pull top non-brand organic keywords (ranked by estimated traffic / ETV) for a
set of domains from the DataForSEO Labs `ranked_keywords` endpoint.

Each domain has its own selection rule (see SELECTION):
  ("top_n", N)    keep the top N non-brand keywords by ETV
  ("etv_min", X)  keep every non-brand keyword with ETV > X

The endpoint returns at most 1000 rows per call, so we paginate with `offset`
until the selection rule is satisfied (top N reached, or ETV drops to/below the
threshold), or the domain runs out of keywords.

For each domain it writes:
  data/raw_<domain>.json   - the unmodified API responses (one per page) so we
                             can re-slice later without spending more credits
  data/<domain>.csv        - selected non-brand keywords, ETV-descending

Auth comes from environment variables (added as environment secrets):
  DATAFORSEO_LOGIN
  DATAFORSEO_PASSWORD

Usage:
  python3 keyword_research.py
"""
import os
import re
import csv
import json
import sys
import base64
from pathlib import Path

import requests

API_URL = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"

LOCATION_CODE = 2840   # United States
LANGUAGE_CODE = "en"   # English
PAGE_SIZE = 1000       # max rows per call
MAX_PAGES = 10         # safety cap on pagination (10k rows / domain)

# domain -> list of regexes; a keyword matching ANY of these is treated as brand
BRAND_PATTERNS = {
    "sundaycitizen.co":  [r"sunday\s*citizen", r"sundaycitizen"],
    "brooklinen.com":    [r"brooklinen", r"brooklyn\s*linen"],
}

# domain -> selection rule applied to the non-brand keywords
#   ("top_n", N)   -> top N by ETV
#   ("etv_min", X) -> every keyword with ETV > X
SELECTION = {
    "sundaycitizen.co": ("top_n", 500),
    "brooklinen.com":   ("etv_min", 80),
}

OUT_DIR = Path(__file__).parent / "data"


def auth_header():
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        sys.exit("ERROR: DATAFORSEO_LOGIN and/or DATAFORSEO_PASSWORD are not set "
                 "in the environment. Start a fresh session after adding the secrets.")
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def fetch_page(domain, headers, offset):
    payload = [{
        "target": domain,
        "location_code": LOCATION_CODE,
        "language_code": LANGUAGE_CODE,
        "limit": PAGE_SIZE,
        "offset": offset,
        "order_by": ["ranked_serp_element.serp_item.etv,desc"],
        "filters": [
            ["ranked_serp_element.serp_item.type", "=", "organic"], "and",
            ["keyword_data.keyword_info.search_volume", ">", 0],
        ],
    }]
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def items_from_response(api_json):
    items = []
    for task in (api_json.get("tasks") or []):
        for result in (task.get("result") or []):
            items.extend(result.get("items") or [])
    return items


def is_brand(keyword, patterns):
    kw = (keyword or "").lower()
    return any(re.search(p, kw) for p in patterns)


def row_from_item(item):
    kd = item.get("keyword_data") or {}
    ki = kd.get("keyword_info") or {}
    kp = kd.get("keyword_properties") or {}
    si = kd.get("search_intent_info") or {}
    serp = (item.get("ranked_serp_element") or {}).get("serp_item") or {}
    return {
        "keyword": kd.get("keyword"),
        "search_volume": ki.get("search_volume"),
        "etv": serp.get("etv"),
        "position": serp.get("rank_absolute"),
        "ranking_url": serp.get("url"),
        "keyword_difficulty": kp.get("keyword_difficulty"),
        "cpc": ki.get("cpc"),
        "search_intent": si.get("main_intent"),
    }


def item_etv(item):
    return (item.get("ranked_serp_element") or {}).get("serp_item", {}).get("etv") or 0


CSV_FIELDS = ["keyword", "search_volume", "etv", "position",
              "ranking_url", "keyword_difficulty", "cpc", "search_intent"]


def enough(items, mode, value, patterns):
    """Stop paginating once the selection rule can be fully satisfied."""
    if mode == "top_n":
        non_brand = sum(1 for it in items
                        if not is_brand((it.get("keyword_data") or {}).get("keyword"), patterns))
        return non_brand >= value
    if mode == "etv_min":
        # results are ETV-descending, so once the last row dips to/below the
        # threshold every remaining keyword is also below it.
        return bool(items) and item_etv(items[-1]) <= value
    raise ValueError(f"unknown selection mode: {mode}")


def process_domain(domain, headers):
    print(f"\n=== {domain} ===")
    patterns = BRAND_PATTERNS.get(domain, [])
    mode, value = SELECTION[domain]

    pages = []
    items = []
    for page in range(MAX_PAGES):
        api_json = fetch_page(domain, headers, offset=page * PAGE_SIZE)
        pages.append(api_json)
        page_items = items_from_response(api_json)
        items.extend(page_items)
        if len(page_items) < PAGE_SIZE:
            break  # ran out of keywords
        if enough(items, mode, value, patterns):
            break
    print(f"  pulled: {len(items)} organic keywords across {len(pages)} page(s)")

    OUT_DIR.mkdir(exist_ok=True)
    slug = domain.replace(".", "_")
    (OUT_DIR / f"raw_{slug}.json").write_text(json.dumps({"pages": pages}, indent=2))

    rows = [row_from_item(it) for it in items]
    non_brand = [r for r in rows if not is_brand(r["keyword"], patterns)]
    print(f"  removed brand keywords: {len(rows) - len(non_brand)}")

    non_brand.sort(key=lambda r: (r["etv"] or 0), reverse=True)
    if mode == "top_n":
        selected = non_brand[:value]
        print(f"  kept top {len(selected)} by ETV")
    else:  # etv_min
        selected = [r for r in non_brand if (r["etv"] or 0) > value]
        print(f"  kept {len(selected)} with ETV > {value}")

    csv_path = OUT_DIR / f"{slug}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(selected)
    print(f"  wrote: {csv_path}")
    return selected


def main():
    headers = auth_header()
    for domain in SELECTION:
        process_domain(domain, headers)
    print("\nDone. CSVs + raw JSON are in ./data/")


if __name__ == "__main__":
    main()
