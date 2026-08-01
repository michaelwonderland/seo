#!/usr/bin/env python3
"""
Phase 3: year-over-year ranking comparison for Wasser's Furniture.

Answers two questions:
  1. How does the ranking mix now compare with the mix 12 months ago?
     -> historical_rank_overview, 26 months of position-band counts.
  2. Which keyword rankings were actually lost?
     -> ranked_keywords with historical_serp_mode="lost", which returns every
        keyword the domain used to rank for and no longer does, together with
        the last position held and the URL that held it.

The lost-keyword URLs are the useful part: they show whether a ranking died
with the old .html catalogue (recoverable by redirecting) or on a current
Shopify URL (a different problem).

Responses are cached to data/raw/ so re-runs cost nothing.

Usage:
  python3 ranking_loss.py
"""
import os
import re
import sys
import csv
import json
import base64
from pathlib import Path
from collections import Counter, defaultdict

import requests

BASE = "https://api.dataforseo.com/v3"
TARGET = "wassersfurniture.com"
LOCATION_CODE = 2840
LANGUAGE_CODE = "en"
HISTORY_FROM = "2024-06-01"

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data"

BRAND = re.compile(r"wasser|wesser|\bw\.?s\b", re.I)

# Position bands, as SERP pages.
BANDS = [
    ("Position 1",     "pos_1"),
    ("Positions 2-3",  "pos_2_3"),
    ("Positions 4-10", "pos_4_10"),
    ("Positions 11-20", "pos_11_20"),
    ("Positions 21-30", "pos_21_30"),
    ("Positions 31-40", "pos_31_40"),
    ("Positions 41-50", "pos_41_50"),
    ("Positions 51-60", "pos_51_60"),
    ("Positions 61-70", "pos_61_70"),
    ("Positions 71-80", "pos_71_80"),
    ("Positions 81-90", "pos_81_90"),
    ("Positions 91-100", "pos_91_100"),
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


def post(path, payload, cache_name):
    global _spend
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_DIR / f"{cache_name}.json"
    if cache_path.exists():
        print(f"  [cached] {cache_name}")
        return json.loads(cache_path.read_text())
    resp = requests.post(BASE + path, headers=HEADERS, json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    task = (data.get("tasks") or [{}])[0]
    if task.get("status_code") != 20000:
        sys.exit(f"API error on {cache_name}: {task.get('status_message')}")
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


def write_csv(path, rows, fields=None):
    if not rows:
        print(f"  (no rows for {path.name})")
        return
    fields = fields or list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path.relative_to(ROOT)}  ({len(rows)} rows)")


# --------------------------------------------------------------------------

def history():
    print("\n=== 26-month ranking history ===")
    data = post("/dataforseo_labs/google/historical_rank_overview/live",
                [{"target": TARGET, "location_code": LOCATION_CODE,
                  "language_code": LANGUAGE_CODE, "date_from": HISTORY_FROM}],
                "history_long")
    rows = []
    for it in items_of(data):
        o = (it.get("metrics") or {}).get("organic") or {}
        row = {
            "year": it.get("year"),
            "month": it.get("month"),
            "period": f"{it.get('year')}-{str(it.get('month')).zfill(2)}",
            "keywords": o.get("count"),
            "etv": round(o.get("etv") or 0, 1),
            "traffic_value_usd": round(o.get("estimated_paid_traffic_cost") or 0, 2),
        }
        for _, key in BANDS:
            row[key] = o.get(key)
        row["page1"] = (o.get("pos_1") or 0) + (o.get("pos_2_3") or 0) + (o.get("pos_4_10") or 0)
        row["page2"] = o.get("pos_11_20") or 0
        row["page3"] = o.get("pos_21_30") or 0
        row["page4plus"] = sum(o.get(k) or 0 for k in
                               ["pos_31_40", "pos_41_50", "pos_51_60", "pos_61_70",
                                "pos_71_80", "pos_81_90", "pos_91_100"])
        rows.append(row)
    rows.sort(key=lambda r: (r["year"], r["month"]))
    write_csv(OUT_DIR / "history_26mo.csv", rows)
    return rows


def current_snapshot():
    data = post("/dataforseo_labs/google/domain_rank_overview/live",
                [{"target": TARGET, "location_code": LOCATION_CODE,
                  "language_code": LANGUAGE_CODE}], "overview_target")
    items = items_of(data)
    return ((items[0].get("metrics") or {}).get("organic") or {}) if items else {}


def lost_keywords():
    print("\n=== Lost keyword rankings ===")
    data = post("/dataforseo_labs/google/ranked_keywords/live",
                [{"target": TARGET, "location_code": LOCATION_CODE,
                  "language_code": LANGUAGE_CODE, "limit": 1000,
                  "historical_serp_mode": "lost",
                  "order_by": ["ranked_serp_element.serp_item.etv,desc"]}],
                "lost_keywords")
    rows = []
    for it in items_of(data):
        kd = it.get("keyword_data") or {}
        ki = kd.get("keyword_info") or {}
        kp = kd.get("keyword_properties") or {}
        si = kd.get("search_intent_info") or {}
        el = it.get("ranked_serp_element") or {}
        serp = el.get("serp_item") or {}
        url = serp.get("url") or ""
        rows.append({
            "keyword": kd.get("keyword"),
            "last_position": serp.get("rank_group"),
            "last_rank_absolute": serp.get("rank_absolute"),
            "search_volume": ki.get("search_volume"),
            "etv_when_ranking": round(serp.get("etv") or 0, 1),
            "keyword_difficulty": kp.get("keyword_difficulty"),
            "cpc": ki.get("cpc"),
            "search_intent": si.get("main_intent"),
            "lost_url": url,
            "url_type": classify_url(url),
            "is_brand": bool(BRAND.search(kd.get("keyword") or "")),
            "last_seen": el.get("last_updated_time"),
        })
    rows.sort(key=lambda r: (r["etv_when_ranking"] or 0, r["search_volume"] or 0),
              reverse=True)
    write_csv(OUT_DIR / "lost_keywords.csv", rows)
    return rows


def classify_url(url):
    """Which generation of the site held this ranking?"""
    if not url:
        return "unknown"
    path = re.sub(r"^https?://[^/]+", "", url)
    if path in ("", "/"):
        return "homepage"
    if path.endswith(".html"):
        return "legacy .html"
    if "/shop-by-brand" in path or "/furniture/" in path:
        return "legacy category"
    if path.startswith("/products/"):
        return "shopify /products/"
    if path.startswith("/collections/"):
        return "shopify /collections/"
    if path.startswith("/pages/"):
        return "shopify /pages/"
    if "blog." in url:
        return "blog subdomain"
    return "other"


def page_of(pos):
    if not pos:
        return None
    return (pos - 1) // 10 + 1


def main():
    global HEADERS
    HEADERS = auth_header()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    hist = history()
    now = current_snapshot()
    by_period = {r["period"]: r for r in hist}

    then = by_period.get("2025-08")
    print("\n=== YEAR-OVER-YEAR RANKING MIX: Aug 2025 vs Aug 2026 ===")
    print(f"{'band':<20} {'Aug 2025':>10} {'Aug 2026':>10} {'change':>10} {'%':>9}")
    print("-" * 62)
    comparison = []
    for label, key in BANDS:
        a = then.get(key) or 0
        b = now.get(key) or 0
        pct = ((b - a) / a * 100) if a else None
        comparison.append({"band": label, "aug_2025": a, "aug_2026": b,
                           "change": b - a,
                           "pct_change": round(pct, 1) if pct is not None else ""})
        print(f"{label:<20} {a:>10} {b:>10} {b-a:>+10} "
              f"{(f'{pct:+.1f}%' if pct is not None else '—'):>9}")

    for label, a, b in [
        ("PAGE 1 (1-10)", (then.get("pos_1") or 0) + (then.get("pos_2_3") or 0)
         + (then.get("pos_4_10") or 0),
         (now.get("pos_1") or 0) + (now.get("pos_2_3") or 0) + (now.get("pos_4_10") or 0)),
        ("PAGE 2 (11-20)", then.get("pos_11_20") or 0, now.get("pos_11_20") or 0),
        ("PAGE 3 (21-30)", then.get("pos_21_30") or 0, now.get("pos_21_30") or 0),
        ("TOTAL KEYWORDS", then.get("keywords") or 0, now.get("count") or 0),
    ]:
        pct = ((b - a) / a * 100) if a else 0
        comparison.append({"band": label, "aug_2025": a, "aug_2026": b,
                           "change": b - a, "pct_change": round(pct, 1)})
        print(f"{label:<20} {a:>10} {b:>10} {b-a:>+10} {pct:>+8.1f}%")

    etv_then = then.get("etv") or 0
    etv_now = round(now.get("etv") or 0, 1)
    comparison.append({"band": "EST. VISITS/MO", "aug_2025": etv_then,
                       "aug_2026": etv_now, "change": round(etv_now - etv_then, 1),
                       "pct_change": round((etv_now - etv_then) / etv_then * 100, 1)})
    print(f"{'EST. VISITS/MO':<20} {etv_then:>10} {etv_now:>10} "
          f"{etv_now-etv_then:>+10.1f} {(etv_now-etv_then)/etv_then*100:>+8.1f}%")
    write_csv(OUT_DIR / "yoy_ranking_mix.csv", comparison)

    lost = lost_keywords()

    print(f"\n=== LOST KEYWORDS: {len(lost)} total ===")
    band_counts = Counter()
    for r in lost:
        p = page_of(r["last_position"])
        band_counts["page 1" if p == 1 else "page 2" if p == 2
                     else "page 3" if p == 3 else "page 4+"] += 1
    print("  by last position held:")
    for k in ["page 1", "page 2", "page 3", "page 4+"]:
        print(f"    {k:<10} {band_counts[k]:>4}")

    print("  by URL that held the ranking:")
    url_counts = Counter(r["url_type"] for r in lost)
    url_etv = defaultdict(float)
    for r in lost:
        url_etv[r["url_type"]] += r["etv_when_ranking"] or 0
    for k, v in url_counts.most_common():
        print(f"    {k:<22} {v:>4} keywords   {url_etv[k]:>8.0f} est. visits/mo")

    lost_etv = sum(r["etv_when_ranking"] or 0 for r in lost)
    lost_vol = sum(r["search_volume"] or 0 for r in lost)
    nonbrand = [r for r in lost if not r["is_brand"]]
    print(f"\n  total estimated visits lost:  {lost_etv:,.0f}/mo")
    print(f"  total search volume lost:     {lost_vol:,}/mo")
    print(f"  non-brand share:              {len(nonbrand)}/{len(lost)}")

    # The recoverable set: page-1 rankings that died on a legacy URL.
    recoverable = [r for r in lost
                   if page_of(r["last_position"]) == 1
                   and r["url_type"].startswith("legacy")]
    recoverable.sort(key=lambda r: r["etv_when_ranking"] or 0, reverse=True)
    write_csv(OUT_DIR / "lost_recoverable_page1.csv", recoverable)
    print(f"\n  page-1 rankings lost on legacy URLs (redirect candidates): "
          f"{len(recoverable)}  ->  {sum(r['etv_when_ranking'] or 0 for r in recoverable):,.0f} est. visits/mo")

    top_urls = Counter()
    for r in lost:
        if r["lost_url"]:
            top_urls[r["lost_url"]] += 1
    print("\n  URLs that lost the most rankings:")
    for u, c in top_urls.most_common(12):
        print(f"    {c:>3}  {u[:96]}")

    (OUT_DIR / "ranking_loss.json").write_text(json.dumps({
        "history": hist, "current": now, "yoy": comparison,
        "lost_keywords": lost,
    }, indent=2))
    print(f"\nWrote data/ranking_loss.json")
    print(f"Total spend this run: ${_spend:.4f}")


if __name__ == "__main__":
    main()
