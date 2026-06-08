#!/usr/bin/env python3
"""
Expand a seed keyword list into relevant NET-NEW keyword opportunities for
brooklinen.com using DataForSEO Labs.

Pipeline:
  1. Load + normalize seeds from data/seed_keywords.txt.
  2. Pull brooklinen.com's FULL ranked keyword set (paginated) -> exclusion set,
     so the output excludes anything the domain already ranks for.
  3. keyword_ideas/live  -> topically relevant expansion (seeds batched, <=200/call).
  4. keyword_suggestions/live -> long-tail variants for the TOP_SEEDS seeds
     (ranked by their search volume in brooklinen's ranked data).
  5. Merge, dedupe, drop brand + seeds + already-ranking, filter search_volume,
     sort by volume.

Writes:
  data/brooklinen_expansion.csv
  data/raw_brooklinen_expansion.json   (ideas + suggestions raw responses)

Auth from env: DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD
"""
import os
import re
import csv
import json
import sys
import base64
from pathlib import Path

import requests

BASE = "https://api.dataforseo.com/v3/dataforseo_labs/google"
IDEAS_URL = f"{BASE}/keyword_ideas/live"
SUGGEST_URL = f"{BASE}/keyword_suggestions/live"
RANKED_URL = f"{BASE}/ranked_keywords/live"

TARGET = "brooklinen.com"
LOCATION_CODE = 2840
LANGUAGE_CODE = "en"

MIN_VOLUME = 100                  # keep keywords with search_volume >= this
PAGE_SIZE = 1000                  # API max rows/call
IDEAS_SEED_BATCH = 200           # max seeds per keyword_ideas call
IDEAS_MAX_PAGES = 5              # safety cap per ideas batch
TOP_SEEDS = 50                   # how many seeds get keyword_suggestions
SUGGEST_LIMIT = 200             # suggestions kept per seed (volume-desc)
RANKED_MAX_PAGES = 40           # safety cap on full ranked-set pull

BRAND = [r"brooklinen", r"brooklyn\s*linen"]

# keyword_ideas is category-based and drifts off-topic (e.g. "cotton bowl").
# Ideas-sourced keywords must contain one of these product terms to be kept;
# suggestions are inherently on-topic (they contain a seed) and bypass this.
CATEGORY_TERMS = [
    "sheet", "sheets", "bedsheet", "bedsheets", "towel", "towels", "duvet",
    "duvets", "comforter", "comforters", "bedding", "linen", "linens", "pillow",
    "pillows", "pillowcase", "pillowcases", "sham", "shams", "quilt", "quilts",
    "blanket", "blankets", "throw", "throws", "robe", "robes", "bathrobe",
    "bathrobes", "bath", "shower", "curtain", "curtains", "rug",
    "rugs", "mat", "mats", "bedspread", "bedspreads", "doona", "coverlet",
    "sateen", "percale", "flannel", "flannelette", "duvet cover",
    "eye mask", "sleep mask", "dryer balls", "washcloth", "wash cloth",
]
CAT_RE = re.compile(r"\b(" + "|".join(map(re.escape, CATEGORY_TERMS)) + r")\b")

# Hard-goods / competitor / pest / deal noise — dropped regardless of source.
# Brooklinen sells soft textiles, not furniture, mattresses, or appliances.
NEGATIVE_TERMS = [
    "mattress", "mattresses", "bed frame", "bed frames", "frame", "frames",
    "murphy", "sofa", "futon", "headboard", "bunk", "daybed", "day bed",
    "crib", "cot ", "trundle", "ottoman", "nightstand", "dresser",
    "bug", "bugs", "bedbug",
    "bath and beyond", "bath & beyond", "bed bath", "ikea", "wayfair",
    "amazon", "walmart", "target", "costco", "wholesale", "promo code",
    "coupon", "discount code", "bath and body works", "body works",
    "beds en bedding", "garden", "coloring", "sitz", "sanitary", "missouri",
    "diaper", "raised", "dog", "cat ", "puppy",
]
NEG_RE = re.compile(r"(" + "|".join(map(re.escape, NEGATIVE_TERMS)) + r")")

# stopwords stripped when canonicalizing word-order variants, so that
# "cover for duvet" / "duvet cover" / "cover duvet" collapse to one keyword.
STOPWORDS = {"for", "with", "and", "the", "in", "of", "a", "to", "on", "&",
             "my", "your", "an", "at", "is", "are"}


def canon_key(kw):
    """Token-set signature for de-duping word-order/stopword variants.
    Returns None for malformed keywords with a repeated word."""
    toks = (kw or "").split()
    if len(set(toks)) != len(toks):
        return None  # repeated word -> grammar-scramble junk
    key = tuple(sorted(t for t in toks if t not in STOPWORDS))
    return key or tuple(toks)


def on_topic(kw):
    return bool(CAT_RE.search(kw or ""))


def is_noise(kw):
    return bool(NEG_RE.search(kw or ""))

HERE = Path(__file__).parent
DATA = HERE / "data"
SEEDS_FILE = DATA / "seed_keywords.txt"
RANKED_RAW = DATA / "raw_brooklinen_com.json"   # reused for seed volumes
RANKED_CACHE = DATA / "brooklinen_ranked_keywords.txt"  # cached exclusion set


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


def items_of(api_json):
    out = []
    for task in (api_json.get("tasks") or []):
        for result in (task.get("result") or []):
            out.extend(result.get("items") or [])
    return out


# --- defensive field access (item shape differs across endpoints) ---
def f_keyword(it):
    return it.get("keyword") or (it.get("keyword_data") or {}).get("keyword")

def f_info(it):
    return it.get("keyword_info") or (it.get("keyword_data") or {}).get("keyword_info") or {}

def f_props(it):
    return it.get("keyword_properties") or (it.get("keyword_data") or {}).get("keyword_properties") or {}

def f_intent(it):
    return it.get("search_intent_info") or (it.get("keyword_data") or {}).get("search_intent_info") or {}


def is_brand(kw):
    kw = (kw or "").lower()
    return any(re.search(p, kw) for p in BRAND)


def norm(kw):
    return re.sub(r"\s+", " ", (kw or "").strip().lower())


def load_seeds():
    seeds, seen = [], set()
    for line in SEEDS_FILE.read_text().splitlines():
        k = norm(line)
        if k and k not in seen:
            seen.add(k)
            seeds.append(k)
    return seeds


def fetch_ranked_set(headers):
    """All keywords brooklinen.com currently ranks for. Cached to disk; set
    env REFRESH_RANKED=1 to force a fresh pull."""
    if RANKED_CACHE.exists() and not os.environ.get("REFRESH_RANKED"):
        cached = {norm(k) for k in RANKED_CACHE.read_text().splitlines() if k.strip()}
        print(f"  (using cached ranked set: {len(cached)} keywords; REFRESH_RANKED=1 to refresh)")
        return cached
    ranked = set()
    for page in range(RANKED_MAX_PAGES):
        payload = [{
            "target": TARGET, "location_code": LOCATION_CODE,
            "language_code": LANGUAGE_CODE, "limit": PAGE_SIZE,
            "offset": page * PAGE_SIZE,
            "order_by": ["ranked_serp_element.serp_item.etv,desc"],
            "filters": [["ranked_serp_element.serp_item.type", "=", "organic"]],
        }]
        items = items_of(post(RANKED_URL, payload, headers))
        for it in items:
            ranked.add(norm(f_keyword(it)))
        if len(items) < PAGE_SIZE:
            break
    RANKED_CACHE.write_text("\n".join(sorted(ranked)))
    return ranked


def seed_volume_map():
    """keyword -> search_volume from brooklinen's saved ranked data."""
    if not RANKED_RAW.exists():
        return {}
    raw = json.loads(RANKED_RAW.read_text())
    pages = raw.get("pages") if isinstance(raw, dict) else [raw]
    vol = {}
    for pg in pages:
        for it in items_of(pg):
            vol[norm(f_keyword(it))] = f_info(it).get("search_volume") or 0
    return vol


def fetch_ideas(seeds, headers, raw_sink):
    rows = {}
    for i in range(0, len(seeds), IDEAS_SEED_BATCH):
        batch = seeds[i:i + IDEAS_SEED_BATCH]
        for page in range(IDEAS_MAX_PAGES):
            payload = [{
                "keywords": batch, "location_code": LOCATION_CODE,
                "language_code": LANGUAGE_CODE, "limit": PAGE_SIZE,
                "offset": page * PAGE_SIZE,
                "order_by": ["keyword_info.search_volume,desc"],
                "filters": [["keyword_info.search_volume", ">=", MIN_VOLUME]],
            }]
            resp = post(IDEAS_URL, payload, headers)
            raw_sink.setdefault("ideas", []).append(resp)
            items = items_of(resp)
            for it in items:
                add_row(rows, it, "ideas")
            if len(items) < PAGE_SIZE:
                break
        print(f"  ideas batch {i//IDEAS_SEED_BATCH + 1}: running total {len(rows)} unique")
    return rows


def fetch_suggestions(top_seeds, headers, rows, raw_sink):
    for n, seed in enumerate(top_seeds, 1):
        payload = [{
            "keyword": seed, "location_code": LOCATION_CODE,
            "language_code": LANGUAGE_CODE, "limit": SUGGEST_LIMIT,
            "order_by": ["keyword_info.search_volume,desc"],
            "filters": [["keyword_info.search_volume", ">=", MIN_VOLUME]],
        }]
        resp = post(SUGGEST_URL, payload, headers)
        raw_sink.setdefault("suggestions", []).append(resp)
        for it in items_of(resp):
            add_row(rows, it, "suggestion")
        if n % 10 == 0:
            print(f"  suggestions: {n}/{len(top_seeds)} seeds, {len(rows)} unique")
    return rows


def add_row(rows, it, source):
    kw = norm(f_keyword(it))
    if not kw:
        return
    info, props, intent = f_info(it), f_props(it), f_intent(it)
    if kw in rows:
        if source not in rows[kw]["source"]:
            rows[kw]["source"] += f"+{source}"
        return
    rows[kw] = {
        "keyword": f_keyword(it),
        "search_volume": info.get("search_volume"),
        "cpc": info.get("cpc"),
        "competition": info.get("competition_level") or info.get("competition"),
        "keyword_difficulty": props.get("keyword_difficulty"),
        "search_intent": intent.get("main_intent"),
        "source": source,
    }


FIELDS = ["keyword", "search_volume", "cpc", "competition",
          "keyword_difficulty", "search_intent", "source"]


def gather_from_raw():
    """Rebuild the candidate rows from saved raw responses (no API calls).
    Used when REFILTER=1 to tune filters without spending credits."""
    raw = json.loads((DATA / "raw_brooklinen_expansion.json").read_text())
    rows = {}
    for resp in raw.get("ideas", []):
        for it in items_of(resp):
            add_row(rows, it, "ideas")
    for resp in raw.get("suggestions", []):
        for it in items_of(resp):
            add_row(rows, it, "suggestion")
    return rows


def main():
    headers = None if os.environ.get("REFILTER") else auth_header()
    seeds = load_seeds()
    seed_set = set(seeds)
    print(f"seeds: {len(seeds)} unique")

    if os.environ.get("REFILTER"):
        print("REFILTER: rebuilding candidates from saved raw responses (no API calls)")
        ranked = fetch_ranked_set(None)  # cached set, no network
        rows = gather_from_raw()
    else:
        print("pulling brooklinen full ranked set for exclusion...")
        ranked = fetch_ranked_set(headers)
        print(f"  already ranking for: {len(ranked)} keywords")

        raw_sink = {}
        print("keyword_ideas expansion...")
        rows = fetch_ideas(seeds, headers, raw_sink)

        vols = seed_volume_map()
        top_seeds = sorted(seeds, key=lambda s: vols.get(s, 0), reverse=True)[:TOP_SEEDS]
        print(f"keyword_suggestions for top {len(top_seeds)} seeds...")
        fetch_suggestions(top_seeds, headers, rows, raw_sink)

        DATA.mkdir(exist_ok=True)
        (DATA / "raw_brooklinen_expansion.json").write_text(json.dumps(raw_sink, indent=2))

    # filter: brand, seeds, already-ranking, volume
    out = []
    drop_brand = drop_seed = drop_ranked = drop_vol = drop_offtopic = drop_noise = drop_nav = 0
    for kw, r in rows.items():
        if is_brand(kw):
            drop_brand += 1; continue
        if is_noise(kw):
            drop_noise += 1; continue
        if r["search_intent"] == "navigational":
            drop_nav += 1; continue
        if kw in seed_set:
            drop_seed += 1; continue
        if kw in ranked:
            drop_ranked += 1; continue
        if (r["search_volume"] or 0) < MIN_VOLUME:
            drop_vol += 1; continue
        if "suggestion" not in r["source"] and not on_topic(kw):
            drop_offtopic += 1; continue
        out.append(r)
    out.sort(key=lambda r: (r["search_volume"] or 0), reverse=True)

    # collapse word-order/stopword variants; drop repeated-word junk
    canon, drop_variant, drop_dupword = {}, 0, 0
    deduped = []
    for r in out:  # already volume-desc, so first seen = highest volume
        key = canon_key(norm(r["keyword"]))
        if key is None:
            drop_dupword += 1; continue
        if key in canon:
            drop_variant += 1; continue
        canon[key] = r
        deduped.append(r)
    out = deduped

    print(f"\nraw unique expanded: {len(rows)}")
    print(f"  dropped brand:{drop_brand} noise:{drop_noise} navigational:{drop_nav} "
          f"seed:{drop_seed} already-ranking:{drop_ranked} low-vol:{drop_vol} off-topic:{drop_offtopic}")
    print(f"  dropped dup-word:{drop_dupword} word-order-variant:{drop_variant}")
    print(f"NET-NEW keywords: {len(out)}")

    csv_path = DATA / "brooklinen_expansion.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print(f"wrote: {csv_path}")


if __name__ == "__main__":
    main()
