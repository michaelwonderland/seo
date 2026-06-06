#!/usr/bin/env python3
"""
Find domains that rank for the expanded bedding keyword space.

Calls DataForSEO Labs `serp_competitors/live` with the 6,031 keywords from
data/brooklinen_expansion.csv in batches of 200, aggregates domain-level
metrics across batches, filters out generalist retailers/marketplaces, and
writes a ranked domain list sorted by keyword footprint in the space.

Output:
  data/serp_competitors.csv
  data/raw_serp_competitors.json  (cached raw responses)

Auth: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD env vars
REFILTER=1  re-aggregates from cached raw JSON, no API calls.
"""
import os, csv, json, sys, base64
from pathlib import Path
from collections import defaultdict

import requests

BASE = "https://api.dataforseo.com/v3/dataforseo_labs/google"
SERP_COMP_URL = f"{BASE}/serp_competitors/live"

LOCATION_CODE = 2840
LANGUAGE_CODE = "en"
KW_BATCH = 200       # keywords per API call (endpoint max)
RESULTS_LIMIT = 1000  # competitor domains returned per call

HERE = Path(__file__).parent
DATA = HERE / "data"
EXPANSION_CSV = DATA / "brooklinen_expansion.csv"
RAW_OUT = DATA / "raw_serp_competitors.json"
CSV_OUT = DATA / "serp_competitors.csv"

# Generalist retailers, marketplaces, social/content platforms excluded from output
EXCLUDE = {
    "amazon.com", "amazon.co.uk", "amazon.ca", "amazon.com.au",
    "walmart.com", "target.com", "wayfair.com", "overstock.com",
    "homedepot.com", "lowes.com", "costco.com",
    "ebay.com", "etsy.com", "wish.com", "aliexpress.com",
    "macys.com", "bedbathandbeyond.com", "buybuybaby.com",
    "kohls.com", "jcpenney.com", "nordstrom.com", "bloomingdales.com",
    "sears.com", "belk.com", "tjmaxx.com", "marshalls.com",
    "google.com", "pinterest.com", "reddit.com",
    "wikipedia.org", "en.wikipedia.org", "youtube.com", "yelp.com",
    "quora.com", "m.wikipedia.org",
    "facebook.com", "instagram.com", "twitter.com", "tiktok.com",
    "tripadvisor.com",
    # SaaS / app-store / tech contamination from generic terms ("sheets" ->
    # Google Sheets, "robe"/etc.) — not part of the bedding landscape.
    "workspace.google.com", "docs.google.com", "play.google.com",
    "apps.apple.com", "essentials.withgoogle.com", "microsoft.com",
    "support.google.com", "chromewebstore.google.com",
}

# Editorial / publisher / review domains — part of the landscape (they capture
# traffic) but NOT direct commercial competitors. Tagged so they can be split out.
PUBLISHERS = {
    "nytimes.com", "wirecutter.com", "forbes.com", "fortune.com",
    "sleepfoundation.org",
    "thespruce.com", "goodhousekeeping.com", "cnn.com", "businessinsider.com",
    "nbcnews.com", "today.com", "realsimple.com", "housebeautiful.com",
    "architecturaldigest.com", "elle.com", "vogue.com", "nymag.com",
    "thestrategist.com", "rollingstone.com", "cnet.com", "wired.com",
    "mattressclarity.com", "mattressnerd.com", "sleepopolis.com",
    "tomsguide.com", "techradar.com", "usatoday.com", "people.com",
    "bhg.com", "marthastewart.com", "apartmenttherapy.com", "thespruceeats.com",
    "healthline.com", "webmd.com", "verywellhealth.com",
}

FIELDS = [
    "domain", "category", "keywords_in_space", "etv_in_space",
    "traffic_share_pct", "avg_position", "visibility",
]


def norm_domain(domain):
    """Strip leading www. so 'www.x.com' and 'x.com' collapse + match EXCLUDE."""
    d = (domain or "").lower().strip()
    return d[4:] if d.startswith("www.") else d


def auth_header():
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        sys.exit("ERROR: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set.")
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def post(url, payload, headers):
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    return r.json()


def load_keywords():
    with EXPANSION_CSV.open() as f:
        return [row["keyword"] for row in csv.DictReader(f)]


def items_of_response(resp):
    items = []
    for task in (resp.get("tasks") or []):
        for result in (task.get("result") or []):
            items.extend(result.get("items") or [])
    return items


def aggregate(responses):
    """Merge per-batch domain data. Keyword batches are disjoint subsets of the
    space, so keywords_count / etv / visibility sum cleanly across batches;
    avg_position is recombined as a keyword-weighted mean."""
    agg = defaultdict(lambda: {
        "keywords_in_space": 0,
        "etv_in_space": 0.0,
        "visibility": 0.0,
        "weighted_pos_sum": 0.0,
    })
    for resp in responses:
        for it in items_of_response(resp):
            domain = norm_domain(it.get("domain"))
            if not domain:
                continue
            kw_count = it.get("keywords_count") or 0
            d = agg[domain]
            d["keywords_in_space"] += kw_count
            d["etv_in_space"] += it.get("etv") or 0.0
            d["visibility"] += it.get("visibility") or 0.0
            d["weighted_pos_sum"] += (it.get("avg_position") or 0) * kw_count
    return agg


def main():
    keywords = load_keywords()
    print(f"keywords in space: {len(keywords)}")

    refilter = os.environ.get("REFILTER")
    if refilter:
        print("REFILTER: loading raw responses from disk (no API calls)")
        responses = json.loads(RAW_OUT.read_text())
    else:
        headers = auth_header()
        responses = []
        total_batches = (len(keywords) + KW_BATCH - 1) // KW_BATCH
        for i in range(0, len(keywords), KW_BATCH):
            batch = keywords[i:i + KW_BATCH]
            batch_num = i // KW_BATCH + 1
            payload = [{
                "keywords": batch,
                "location_code": LOCATION_CODE,
                "language_code": LANGUAGE_CODE,
                "limit": RESULTS_LIMIT,
            }]
            resp = post(SERP_COMP_URL, payload, headers)
            responses.append(resp)
            n = len(items_of_response(resp))
            print(f"  batch {batch_num}/{total_batches}: {n} domains")

        RAW_OUT.write_text(json.dumps(responses, indent=2))
        print(f"saved raw: {RAW_OUT}")

    agg = aggregate(responses)

    # traffic-share denominator: total ETV across ALL domains in the space
    # (including heavyweights) so the share reflects the true landscape.
    total_etv = sum(d["etv_in_space"] for d in agg.values()) or 1.0

    rows = []
    for domain, d in agg.items():
        if domain in EXCLUDE:
            continue
        kws = d["keywords_in_space"]
        avg_pos = round(d["weighted_pos_sum"] / kws, 1) if kws else None
        rows.append({
            "domain": domain,
            "category": "publisher" if domain in PUBLISHERS else "brand/retail",
            "keywords_in_space": kws,
            "etv_in_space": round(d["etv_in_space"]),
            "traffic_share_pct": round(100 * d["etv_in_space"] / total_etv, 2),
            "avg_position": avg_pos,
            "visibility": round(d["visibility"], 1),
        })

    # rank by estimated traffic captured from the space (traffic share)
    rows.sort(key=lambda r: r["etv_in_space"], reverse=True)

    excluded = {d for d in agg if d in EXCLUDE}
    print(f"\nTotal unique domains found: {len(agg)}")
    print(f"Excluded (heavyweights): {len(excluded)}")
    print(f"Remaining: {len(rows)}")
    brands = [r for r in rows if r["category"] == "brand/retail"]
    print(f"\nTop 40 brand/retail competitors by traffic share in the bedding space:")
    print(f"  {'domain':<30}{'kws':>6}{'etv':>12}{'share%':>9}{'avg_pos':>9}")
    for r in brands[:40]:
        print(
            f"  {r['domain']:<30}"
            f"{r['keywords_in_space']:>6}"
            f"{r['etv_in_space']:>12,}"
            f"{r['traffic_share_pct']:>8}%"
            f"{str(r['avg_position']):>9}"
        )

    with CSV_OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote: {CSV_OUT}")


if __name__ == "__main__":
    main()
