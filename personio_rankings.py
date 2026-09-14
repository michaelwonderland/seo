#!/usr/bin/env python3
"""Step 1: pull ranked keywords for personio.de (DE/de) and personio.com (US/en)."""
import os, json, base64, sys
from pathlib import Path
import requests

BASE = "https://api.dataforseo.com/v3"
OUT = Path("/home/user/seo/data/personio")

def headers():
    l, p = os.environ["DATAFORSEO_LOGIN"], os.environ["DATAFORSEO_PASSWORD"]
    t = base64.b64encode(f"{l}:{p}".encode()).decode()
    return {"Authorization": f"Basic {t}", "Content-Type": "application/json"}

def post(path, payload):
    r = requests.post(f"{BASE}{path}", headers=headers(), json=payload, timeout=180)
    r.raise_for_status()
    j = r.json()
    if j.get("status_code") != 20000:
        sys.exit(f"API error {j.get('status_code')}: {j.get('status_message')}")
    return j

TARGETS = [
    ("personio.de", 2276, "de"),   # Germany / German
    ("personio.com", 2840, "en"),  # United States / English
]

for domain, loc, lang in TARGETS:
    payload = [{
        "target": domain,
        "location_code": loc,
        "language_code": lang,
        "limit": 1000,
        "order_by": ["ranked_serp_element.serp_item.etv,desc"],
        "filters": [
            ["ranked_serp_element.serp_item.type", "=", "organic"], "and",
            ["keyword_data.keyword_info.search_volume", ">", 0],
        ],
    }]
    j = post("/dataforseo_labs/google/ranked_keywords/live", payload)
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"raw_{domain.replace('.','_')}.json"
    f.write_text(json.dumps(j))
    res = j["tasks"][0]["result"][0]
    print(f"{domain}: items={len(res.get('items') or [])} total_kw={res.get('total_count')} cost={j.get('cost')}")
