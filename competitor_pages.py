#!/usr/bin/env python3
"""
Build a "page to beat" map: for every keyword, the highest-ranking competitor
URL among Brooklinen / Parachute / Piglet in Bed / Pottery Barn / Latest Bedding
(Tempur-Pedic intentionally excluded).

Pulls each competitor's ranked_keywords (organic) with the ranking URL + position
and keeps, per keyword, the best (lowest) position each competitor holds. A later
step (serp_winnability.py) picks the single strongest competitor page per target
page and writes it into the plan.

Output: data/competitor_pages.json  { keyword: { domain: [position, url] } }

Auth: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD
  REFILTER=1  rebuild map from cached raw pulls (no API calls)
"""
import os, json, sys, base64
from pathlib import Path

import requests

RANKED_URL = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"
LOCATION_CODE = 2840
LANGUAGE_CODE = "en"
PAGE_SIZE = 1000
MAX_PAGES = 25          # up to 25k keywords/competitor by ETV (deep coverage)

HERE = Path(__file__).parent
DATA = HERE / "data"
RAW = DATA / "raw_competitor_pages.json"
OUT = DATA / "competitor_pages.json"

COMPETITORS = ["brooklinen.com", "parachutehome.com", "us.pigletinbed.com",
               "potterybarn.com", "latestbedding.com"]


def auth_header():
    login, pw = os.environ.get("DATAFORSEO_LOGIN"), os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not pw:
        sys.exit("ERROR: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set.")
    tok = base64.b64encode(f"{login}:{pw}".encode()).decode()
    return {"Authorization": f"Basic {tok}", "Content-Type": "application/json"}


def items_of(resp):
    out = []
    for t in (resp.get("tasks") or []):
        for r in (t.get("result") or []):
            out.extend(r.get("items") or [])
    return out


def norm(k):
    import re
    return re.sub(r"\s+", " ", (k or "").strip().lower())


def fetch_domain(domain, headers, raw_sink):
    pages = []
    for page in range(MAX_PAGES):
        payload = [{
            "target": domain, "location_code": LOCATION_CODE,
            "language_code": LANGUAGE_CODE, "limit": PAGE_SIZE,
            "offset": page * PAGE_SIZE,
            "order_by": ["ranked_serp_element.serp_item.etv,desc"],
            "filters": [["ranked_serp_element.serp_item.type", "=", "organic"]],
        }]
        r = requests.post(RANKED_URL, headers=headers, json=payload, timeout=180)
        r.raise_for_status()
        resp = r.json()
        pages.append(resp)
        n = len(items_of(resp))
        if n < PAGE_SIZE:
            break
    raw_sink[domain] = pages
    print(f"  {domain}: {sum(len(items_of(p)) for p in pages)} keywords, {len(pages)} pages")
    return pages


def build_map(raw):
    # display domain (strip leading us. etc. for the public host shown to user)
    kwmap = {}
    for domain, pages in raw.items():
        for pg in pages:
            for it in items_of(pg):
                kd = it.get("keyword_data") or {}
                kw = norm(kd.get("keyword"))
                serp = (it.get("ranked_serp_element") or {}).get("serp_item") or {}
                pos = serp.get("rank_absolute")
                url = serp.get("url")
                if not kw or pos is None or not url:
                    continue
                slot = kwmap.setdefault(kw, {})
                if domain not in slot or pos < slot[domain][0]:
                    slot[domain] = [pos, url]
    return kwmap


def main():
    if os.environ.get("REFILTER") and RAW.exists():
        raw = json.loads(RAW.read_text())
        print(f"REFILTER: rebuilding from cached pulls ({len(raw)} domains)")
    else:
        headers = auth_header()
        raw = {}
        for d in COMPETITORS:
            fetch_domain(d, headers, raw)
        RAW.write_text(json.dumps(raw))

    kwmap = build_map(raw)
    OUT.write_text(json.dumps(kwmap))
    print(f"wrote {OUT}  ({len(kwmap)} keywords with a competitor page)")


if __name__ == "__main__":
    main()
