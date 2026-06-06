#!/usr/bin/env python3
"""
Pull top non-brand organic keywords (ranked by estimated traffic / ETV) for a
set of domains from the DataForSEO Labs `ranked_keywords` endpoint.

For each domain it writes:
  data/raw_<domain>.json   - the unmodified API response (so we can re-slice
                             later without spending more API credits)
  data/<domain>.csv        - top N non-brand keywords, ETV-descending

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
PULL_LIMIT = 1000      # max rows per call; buffer so we still clear TOP_N after brand filtering
TOP_N = 500            # final keywords kept per domain

# domain -> list of regexes; a keyword matching ANY of these is treated as brand
BRAND_PATTERNS = {
    "sundaycitizen.com": [r"sunday\s*citizen", r"sundaycitizen"],
    "brooklinen.com":    [r"brooklinen", r"brooklyn\s*linen"],
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


def fetch_ranked_keywords(domain, headers):
    payload = [{
        "target": domain,
        "location_code": LOCATION_CODE,
        "language_code": LANGUAGE_CODE,
        "limit": PULL_LIMIT,
        "order_by": ["ranked_serp_element.serp_item.etv,desc"],
        "filters": [
            ["ranked_serp_element.serp_item.type", "=", "organic"], "and",
            ["keyword_data.keyword_info.search_volume", ">", 0],
        ],
    }]
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def is_brand(keyword, patterns):
    kw = (keyword or "").lower()
    return any(re.search(p, kw) for p in patterns)


def extract_rows(api_json):
    """Flatten the API response into simple dict rows."""
    rows = []
    tasks = api_json.get("tasks") or []
    for task in tasks:
        for result in (task.get("result") or []):
            for item in (result.get("items") or []):
                kd = item.get("keyword_data") or {}
                ki = kd.get("keyword_info") or {}
                kp = kd.get("keyword_properties") or {}
                si = kd.get("search_intent_info") or {}
                serp = (item.get("ranked_serp_element") or {}).get("serp_item") or {}
                rows.append({
                    "keyword": kd.get("keyword"),
                    "search_volume": ki.get("search_volume"),
                    "etv": serp.get("etv"),
                    "position": serp.get("rank_absolute"),
                    "ranking_url": serp.get("url"),
                    "keyword_difficulty": kp.get("keyword_difficulty"),
                    "cpc": ki.get("cpc"),
                    "search_intent": si.get("main_intent"),
                })
    return rows


CSV_FIELDS = ["keyword", "search_volume", "etv", "position",
              "ranking_url", "keyword_difficulty", "cpc", "search_intent"]


def process_domain(domain, headers):
    print(f"\n=== {domain} ===")
    api_json = fetch_ranked_keywords(domain, headers)

    OUT_DIR.mkdir(exist_ok=True)
    slug = domain.replace(".", "_")
    raw_path = OUT_DIR / f"raw_{slug}.json"
    raw_path.write_text(json.dumps(api_json, indent=2))

    rows = extract_rows(api_json)
    print(f"  pulled: {len(rows)} organic keywords")

    patterns = BRAND_PATTERNS.get(domain, [])
    non_brand = [r for r in rows if not is_brand(r["keyword"], patterns)]
    print(f"  removed brand keywords: {len(rows) - len(non_brand)}")

    non_brand.sort(key=lambda r: (r["etv"] or 0), reverse=True)
    top = non_brand[:TOP_N]
    print(f"  kept top {len(top)} by ETV")

    csv_path = OUT_DIR / f"{slug}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(top)
    print(f"  wrote: {csv_path}")
    return top


def main():
    headers = auth_header()
    for domain in BRAND_PATTERNS:
        process_domain(domain, headers)
    print("\nDone. CSVs + raw JSON are in ./data/")


if __name__ == "__main__":
    main()
