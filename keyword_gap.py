#!/usr/bin/env python3
"""
Keyword GAP analysis for sundaycitizen.co.

Demand universe = every keyword the bedding competitors rank for (their ranked
CSVs) UNION the expansion list. Gap = demand keywords that Sunday Citizen does
NOT already rank for (absent, or ranking below position GAP_POS), restricted to
product categories Sunday Citizen actually sells.

For each gap keyword we recommend the Sunday Citizen page that should rank for
it: an existing collection (optimize it) or, when none fits, a NEW collection
page (with a suggested handle/title). Output is the top TOP_N by search volume.

Inputs (already on disk):
  data/brooklinen_expansion.csv
  data/{brooklinen_com,potterybarn_com,latestbedding_com,
        tempurpedic_com,us_pigletinbed_com,parachutehome_com}.csv
  data/sc_collections.json           (Sunday Citizen catalog from Shopify)
Pulls (cached):
  data/sc_ranked_keywords.json       (sundaycitizen.co full ranked set)

Output:
  data/keyword_gap.csv

Auth: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD
  REFILTER=1   skip the SC ranked-set pull, use cache (no API calls)
"""
import os
import re
import csv
import json
import sys
import base64
from pathlib import Path
from collections import defaultdict

import requests

RANKED_URL = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"
LOCATION_CODE = 2840
LANGUAGE_CODE = "en"
PAGE_SIZE = 1000
SC_MAX_PAGES = 40

GAP_POS = 20          # SC "already ranks" if best organic position <= this
MIN_VOLUME = 150      # floor before taking the top N
TOP_N = 500
POS3_CTR = 0.10       # industry-avg organic click-through rate at position #3;
                      # expected_traffic_pos3 = search_volume * POS3_CTR

HERE = Path(__file__).parent
DATA = HERE / "data"
SC_RANKED_RAW = DATA / "sc_ranked_keywords.json"
COLLECTIONS = DATA / "sc_collections.json"
OUT_CSV = DATA / "keyword_gap.csv"

COMPETITOR_CSVS = {
    "brooklinen.com":     "brooklinen_com.csv",
    "potterybarn.com":    "potterybarn_com.csv",
    "latestbedding.com":  "latestbedding_com.csv",
    "tempurpedic.com":    "tempurpedic_com.csv",
    "pigletinbed.com":    "us_pigletinbed_com.csv",
    "parachutehome.com":  "parachutehome_com.csv",
}
EXPANSION_CSV = "brooklinen_expansion.csv"

# ---- relevance: Sunday Citizen sells soft textiles + home/decor, not hard goods.
CATEGORY_TERMS = [
    "sheet", "sheets", "bedsheet", "bedsheets", "sheet set", "bed sheets",
    "duvet", "duvets", "duvet cover", "comforter", "comforters", "bedding",
    "bed spread", "bedspread", "coverlet", "quilt", "quilts", "blanket",
    "blankets", "throw", "throws", "weighted blanket", "pillow", "pillows",
    "pillowcase", "pillowcases", "pillow case", "pillow sham", "sham", "shams",
    "linen", "linens", "sateen", "percale", "bamboo", "lyocell", "modal",
    "tencel", "flannel", "waffle", "muslin", "matelasse", "velvet",
    "towel", "towels", "bath towel", "beach towel", "washcloth", "hand towel",
    "robe", "robes", "bathrobe", "bathrobes", "kimono",
    "loungewear", "pajama", "pajamas", "pyjama", "pyjamas", "sleepwear",
    "lounge set", "rug", "rugs", "candle", "candles", "diffuser",
    "duvet insert", "pillow insert", "mattress topper", "bed skirt",
]
CAT_RE = re.compile(r"\b(" + "|".join(map(re.escape, sorted(CATEGORY_TERMS, key=len, reverse=True))) + r")\b")

NEGATIVE_TERMS = [
    "mattress topper",  # keep toppers? -> handled: appears in CATEGORY, exclude bare mattress below
    "mattress", "mattresses", "bed frame", "bed frames", "headboard", "murphy",
    "sofa", "futon", "bunk", "daybed", "day bed", "crib", "trundle", "ottoman",
    "nightstand", "dresser", "bookcase", "desk", "recliner",
    "bug", "bugs", "bedbug", "sitz", "sanitary", "diaper", "coloring",
    "amazon", "walmart", "target", "costco", "wayfair", "ikea", "wholesale",
    "bed bath", "bath and beyond", "bath & beyond", "promo code", "coupon",
    "discount code", "garden", "missouri", "dog", "puppy", "yarn",
    "paper towel", "paper towels", "shower curtain", "shower chair",
    "tablecloth", "napkin", "apron", "curtain", "curtains",
    "linen seed", "linseed", "flax seed", "flaxseed", "loft bed",
    # apparel/fashion garments that ride in on fabric words (e.g. "linen shirts",
    # "silk dress") — not SC products and not bedding. NOTE: "skirt" is omitted
    # on purpose so "bed skirt" survives.
    "shirt", "dress", "blouse", "jeans", "blazer", "trouser", "tunic",
    "jumpsuit", "romper", "overalls", "clothing", "trousers",
]
# bare "mattress" should die but "mattress topper" / "mattress pad" survive
NEG_RE = re.compile(r"(" + "|".join(map(re.escape, [t for t in NEGATIVE_TERMS if t != "mattress topper"])) + r")")

# brand terms (competitors + Sunday Citizen itself) -> drop, they're navigational
BRAND_RE = re.compile(
    r"\b(brooklinen|brooklyn linen|pottery barn|potterybarn|tempur|tempurpedic|"
    r"piglet|parachute|sunday citizen|sundaycitizen|west elm|coyuchi|"
    r"casper|purple|boll and branch|boll & branch|buffy|cozy earth|quince|"
    r"company store|garnet hill|ettitude|saatva|nectar|avocado|"
    r"ruggable|crate and barrel|crate & barrel|wayfair|"
    r"bedsure|bedsure|sandcloud|sand cloud|cariloha|magiclinen|magic linen|"
    r"snowe|riley home|the citizenry|citizenry|sheex|slip|nordstrom|macy)\b"
)

STOPWORDS = {"for", "with", "and", "the", "in", "of", "a", "to", "on", "&",
             "my", "your", "an", "at", "is", "are", "best", "where",
             "buy", "shop", "near", "me", "size", "sizes"}


def norm(kw):
    return re.sub(r"\s+", " ", (kw or "").strip().lower())


def canon_key(kw):
    toks = kw.split()
    if len(set(toks)) != len(toks):
        return None
    key = tuple(sorted(t for t in toks if t not in STOPWORDS))
    return key or tuple(toks)


def auth_header():
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        sys.exit("ERROR: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set.")
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def items_of(api_json):
    out = []
    for task in (api_json.get("tasks") or []):
        for result in (task.get("result") or []):
            out.extend(result.get("items") or [])
    return out


def fetch_sc_ranked(headers):
    """sundaycitizen.co: keyword -> best organic position. Cached."""
    if SC_RANKED_RAW.exists() and os.environ.get("REFILTER"):
        pages = json.loads(SC_RANKED_RAW.read_text())
    else:
        pages = []
        for page in range(SC_MAX_PAGES):
            payload = [{
                "target": "sundaycitizen.co", "location_code": LOCATION_CODE,
                "language_code": LANGUAGE_CODE, "limit": PAGE_SIZE,
                "offset": page * PAGE_SIZE,
                "order_by": ["ranked_serp_element.serp_item.etv,desc"],
                "filters": [["ranked_serp_element.serp_item.type", "=", "organic"]],
            }]
            r = requests.post(RANKED_URL, headers=headers, json=payload, timeout=180)
            r.raise_for_status()
            resp = r.json()
            pages.append(resp)
            if len(items_of(resp)) < PAGE_SIZE:
                break
        SC_RANKED_RAW.write_text(json.dumps(pages))
    pos = {}
    for pg in pages:
        for it in items_of(pg):
            kd = it.get("keyword_data") or {}
            kw = norm(kd.get("keyword"))
            p = ((it.get("ranked_serp_element") or {}).get("serp_item") or {}).get("rank_absolute")
            if kw and p is not None:
                pos[kw] = min(p, pos.get(kw, 10**9))
    return pos


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def build_universe():
    """keyword -> {search_volume, cpc, kd, competitors:set, etv}"""
    uni = {}

    def upsert(kw, vol, cpc, kd, src, etv=0.0):
        kw = norm(kw)
        if not kw:
            return
        d = uni.setdefault(kw, {"search_volume": 0, "cpc": 0.0, "kd": None,
                                "competitors": set(), "etv": 0.0})
        d["search_volume"] = max(d["search_volume"], vol)
        d["cpc"] = max(d["cpc"], cpc)
        d["etv"] = max(d["etv"], etv)
        if kd is not None:
            d["kd"] = kd if d["kd"] is None else max(d["kd"], kd)
        if src:
            d["competitors"].add(src)

    for domain, fname in COMPETITOR_CSVS.items():
        path = DATA / fname
        if not path.exists():
            continue
        with path.open() as f:
            for row in csv.DictReader(f):
                upsert(row["keyword"], num(row.get("search_volume")),
                       num(row.get("cpc")), num(row.get("keyword_difficulty")) or None,
                       domain, num(row.get("etv")))

    with (DATA / EXPANSION_CSV).open() as f:
        for row in csv.DictReader(f):
            upsert(row["keyword"], num(row.get("search_volume")),
                   num(row.get("cpc")), num(row.get("keyword_difficulty")) or None,
                   "expansion")

    # Sunday Citizen's own material/product-line demand (lyocell, modal, muslin,
    # bamboo, ...) — pulled directly because the Brooklinen seeds missed them.
    mat = DATA / "material_keywords.csv"
    if mat.exists():
        with mat.open() as f:
            for row in csv.DictReader(f):
                upsert(row["keyword"], num(row.get("search_volume")),
                       num(row.get("cpc")), num(row.get("keyword_difficulty")) or None,
                       "sc-material")
    return uni


# ---------------- page mapping ----------------
def load_collections():
    data = json.loads(COLLECTIONS.read_text())
    return {handle: title for title, handle, _ in data["collections"]}


# material/fabric detection (token -> canonical material)
MATERIALS = [
    (r"\bbamboo\b", "bamboo"),
    (r"\blyocell\b", "lyocell"),
    (r"\btencel\b", "lyocell"),
    (r"\bmodal\b", "modal"),
    (r"\blinen\b|\bflax\b", "linen"),
    (r"\bsateen\b", "sateen"),
    (r"\bpercale\b", "percale"),
    (r"\bflannel\b", "flannel"),
    (r"\bwaffle\b", "waffle"),
    (r"\bmuslin\b", "muslin"),
    (r"\bvelvet\b", "velvet"),
    (r"\bsilk\b|\bsilque\b|\becosilk\b", "silk"),
    (r"\bfaux fur\b|\bfur\b", "faux fur"),
    (r"\bmicrofiber\b", "microfiber"),
    (r"\borganic cotton\b", "organic cotton"),
    (r"\bcotton\b", "cotton"),
    (r"\bcool|cooling\b", "cooling"),
]

# category detection (regex -> (canonical category, existing collection handle or None))
CATEGORIES = [
    (r"\bsheet sets?\b|\bbed sheets?\b|\bbedsheets?\b", "sheets", "sheets"),
    (r"\bsheets?\b", "sheets", "sheets"),
    (r"\bduvet covers?\b", "duvet cover", "duvet-covers"),
    (r"\bduvets?\b", "duvet", "comforters-duvets"),
    (r"\bcomforters?\b", "comforter", "comforters"),
    (r"\bquilts?\b", "quilt", "blankets-quilts"),
    (r"\bcoverlets?\b", "coverlet", "blankets-quilts"),
    (r"\bbedspreads?\b", "bedspread", "blankets-quilts"),
    (r"\bweighted blankets?\b", "weighted blanket", "weighted-blankets"),
    (r"\bbaby blankets?\b", "baby blanket", "blankets"),
    (r"\bthrow blankets?\b|\bthrows?\b", "throw", "throws"),
    (r"\bblankets?\b", "blanket", "blankets"),
    (r"\bpillowcases?\b|\bpillow cases?\b", "pillowcase", "pillowcases"),
    (r"\bshams?\b", "sham", "shams"),
    (r"\bthrow pillows?\b|\bdecorative pillows?\b|\blumbar\b|\bbolster\b", "throw pillow", "throw-pillows"),
    (r"\bpillows?\b", "pillow", "pillows"),
    (r"\bbeach towels?\b", "beach towel", "beach-towels"),
    (r"\bbath towels?\b|\bhand towels?\b|\bwashcloths?\b|\btowels?\b", "towel", "bath"),
    (r"\bbathrobes?\b|\bbath robes?\b", "bath robe", "bath-robes"),
    (r"\brobes?\b|\bkimonos?\b", "robe", "robes-kimonos"),
    (r"\bpajamas?\b|\bpyjamas?\b|\bsleepwear\b|\bloungewear\b|\blounge set\b", "loungewear", "loungewear"),
    (r"\brugs?\b", "rug", "rugs"),
    (r"\bcandles?\b|\bdiffusers?\b|\broom spray\b", "candle", "candles-scents"),
    (r"\bduvet inserts?\b|\bpillow inserts?\b|\binserts?\b", "insert", "bedding-inserts"),
    (r"\bmattress topper\b|\bmattress pad\b", "mattress topper", None),
    (r"\bbath\b", "bath", "bath"),
    (r"\bbedding\b", "bedding", "bedding"),
]

# (material, category) pairs that ALREADY have a dedicated SC collection
MATERIAL_CATEGORY_PAGES = {
    ("bamboo", "sheets"): "premium-bamboo-sheets",
    ("bamboo", "bedding"): "premium-bamboo-bedding",
    ("bamboo", "comforter"): "premium-bamboo-comforters-duvets",
    ("bamboo", "duvet"): "premium-bamboo-comforters-duvets",
    ("bamboo", "sham"): "premium-bamboo-shams-pillowcases",
    ("bamboo", "pillowcase"): "premium-bamboo-shams-pillowcases",
    ("lyocell", "sheets"): "silky-lyocell-sheets",
    ("lyocell", "comforter"): "silky-lyocell-comforters-duvets",
    ("lyocell", "duvet"): "silky-lyocell-comforters-duvets",
    ("lyocell", "loungewear"): "silky-lyocell-loungewear",
    ("linen", "bedding"): "linacel-collection",
    ("linen", "sheets"): "linacel-collection",
    ("cooling", "sheets"): "cooling-edit-bedding",
    ("cooling", "bedding"): "cooling-edit-bedding-1",
    ("cooling", "throw"): "cooling-edit-throws",
    ("cooling", "loungewear"): "cooling-edit-loungewear",
    ("cooling", "comforter"): "summer-edit-comforters",
    ("waffle", "bedding"): "all-things-waffle",
    ("waffle", "throw"): "snug-waffle",
    ("velvet", "bedding"): "velvet-bedding",
    ("velvet", "throw pillow"): "velvet-pillows",
    ("velvet", "pillow"): "velvet-pillows",
    ("faux fur", "bedding"): "faux-fur-bedding",
    ("faux fur", "throw"): "faux-fur",
    ("organic cotton", "bedding"): "organic-cotton",
    ("cotton", "pillow"): "cotton-pillows",
    ("muslin", "bedding"): "muslin",
}

# bare-category fallbacks confirmed present in catalog
CATEGORY_PAGES_PRESENT = {
    "sheets", "duvet-covers", "comforters", "comforters-duvets", "blankets",
    "blankets-quilts", "throws", "weighted-blankets", "pillows", "throw-pillows",
    "pillowcases", "shams", "bath", "bath-robes", "robes-kimonos", "loungewear",
    "rugs", "candles-scents", "bedding-inserts", "bedding",
}


# size modifiers -> canonical label (drives size-segmented collection pages)
SIZES = [
    (r"\bcalifornia king\b|\bcal king\b", "california king"),
    (r"\balaskan? king\b", "alaskan king"),
    (r"\bsplit king\b", "split king"),
    (r"\bking\b", "king"),
    (r"\bqueen\b", "queen"),
    (r"\bfull\b|\bdouble\b", "full"),
    (r"\btwin xl\b", "twin xl"),
    (r"\btwin\b", "twin"),
    (r"\bcrib\b|\btoddler\b", "toddler"),
]

# style / attribute modifiers that justify a dedicated page
STYLES = [
    (r"\borganic\b", "organic"),
    (r"\bstriped?\b", "striped"),
    (r"\bruffled?\b", "ruffled"),
    (r"\bboho\b", "boho"),
    (r"\bembroidered\b", "embroidered"),
    (r"\bquilted\b", "quilted"),
    (r"\breversible\b", "reversible"),
    (r"\blightweight\b", "lightweight"),
    (r"\boversized\b|\boversize\b", "oversized"),
    (r"\bbreathable\b", "breathable"),
    (r"\bdeep pocket\b", "deep pocket"),
    (r"\bhotel\b", "hotel"),
    (r"\bluxury\b", "luxury"),
]


# informational intent -> a size guide / blog page, not a shopping collection
INFO_RE = re.compile(
    r"\b(measurements?|dimensions?|sizing|size chart|size guide|"
    r"how to|how big|what size|thread count)\b"
)
INFO_SIZE_RE = re.compile(
    r"\b(bedding|comforters?|duvets?|sheets?|quilts?|blankets?|pillows?|"
    r"towels?|sham|shams)\s+sizes?\b"
)


def is_info(kw):
    return bool(INFO_RE.search(kw) or INFO_SIZE_RE.search(kw))


def detect_one(kw, table):
    for pat, label in table:
        if re.search(pat, kw):
            return label
    return None


# detected material -> the Sunday Citizen product line that can fill the page.
# "— ..." means SC has no current line for it (a product gap, not just an SEO gap).
MATERIAL_TO_LINE = {
    "bamboo": "Premium Lumière (Bamboo)",
    "lyocell": "Silky Lyocell (TENCEL™)",
    "modal": "Naked Modal",
    "linen": "European Flax Linacel",
    "muslin": "Muslin / Snug Muslin",
    "waffle": "Waffle",
    "sateen": "Luce Cotton Sateen",
    "velvet": "Velvet",
    "faux fur": "Snug / Faux Fur",
    "organic cotton": "Organic Cotton",
    "cotton": "Cotton (Luce Sateen / Organic / Woven)",
    "cooling": "Cloud Cool / Cooling Edit",
    "silk": "Ecosilk / Silky Lyocell",
    "percale": "— no current line (product gap)",
    "flannel": "— no current line (product gap)",
    "microfiber": "— no current line (product gap)",
}
# bare category -> backing line (where the category itself is the product)
CATEGORY_TO_LINE = {
    "weighted blanket": "Crystal Weighted Blanket",
}


def product_line(mat, cat):
    if mat and mat in MATERIAL_TO_LINE:
        return MATERIAL_TO_LINE[mat]
    if cat and cat in CATEGORY_TO_LINE:
        return CATEGORY_TO_LINE[cat]
    return "— (category page, all fabrics)"


def detect_category(kw):
    for pat, cat, handle in CATEGORIES:
        if re.search(pat, kw):
            return cat, handle
    return None, None


def suggest_handle(*parts):
    base = "-".join(p for p in parts if p)
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")


def map_page(kw, collections):
    """Return (action, page_type, url, title, theme).

    A bare head category (no modifier) maps to the existing category collection
    to optimize. Any material / size / style modifier means a query-specific
    landing page is needed: an existing dedicated collection if one matches,
    otherwise a NEW collection page. Informational queries get a guide page.
    """
    mat = detect_one(kw, MATERIALS)
    size = detect_one(kw, SIZES)
    style = detect_one(kw, STYLES)
    cat, cat_handle = detect_category(kw)
    theme = " / ".join(x for x in (mat, cat) if x) or (cat or "general bedding")

    def coll(handle):
        return f"/collections/{handle}"

    # 0. informational intent -> size guide / blog page (not a shopping collection)
    if is_info(kw):
        base = cat or "bedding"
        return ("build guide/blog page", "guide/blog",
                f"/pages/{suggest_handle(base, 'size-guide')}",
                f"{base.title()} Size Guide", f"{base} size guide")

    # 1. material + category with an existing dedicated collection -> optimize it
    if mat and cat and (mat, cat) in MATERIAL_CATEGORY_PAGES:
        h = MATERIAL_CATEGORY_PAGES[(mat, cat)]
        return ("optimize existing", "collection", coll(h), collections.get(h, h), theme)

    # 2. material + category, no dedicated page -> NEW page (e.g. Linen Duvet Covers)
    if mat and cat:
        return ("build new collection", "collection", coll(suggest_handle(mat, cat)),
                f"{mat.title()} {cat.title()}", theme)

    # 3. size + category -> size-segmented NEW page (e.g. King Comforter Sets)
    if size and cat:
        return ("build new collection", "collection", coll(suggest_handle(size, cat)),
                f"{size.title()} {cat.title()}", f"{size} / {cat}")

    # 4. style + category -> attribute NEW page (e.g. Organic Sheets)
    if style and cat:
        return ("build new collection", "collection", coll(suggest_handle(style, cat)),
                f"{style.title()} {cat.title()}", f"{style} / {cat}")

    # 5. bare category -> optimize existing category collection if present
    if cat:
        if cat_handle and cat_handle in CATEGORY_PAGES_PRESENT:
            return ("optimize existing", "collection", coll(cat_handle),
                    collections.get(cat_handle, cat_handle), theme)
        return ("build new collection", "collection",
                coll(cat_handle or suggest_handle(cat)), cat.title(), theme)

    # 6. material only -> material landing collection (NEW)
    if mat:
        return ("build new collection", "collection", coll(suggest_handle(mat, "collection")),
                f"{mat.title()} Collection", theme)

    return ("build new collection", "collection", coll(suggest_handle("bedding")),
            "Bedding", theme)


def main():
    refilter = os.environ.get("REFILTER")
    headers = None if (refilter and SC_RANKED_RAW.exists()) else auth_header()

    print("pulling sundaycitizen.co ranked set...")
    sc_pos = fetch_sc_ranked(headers)
    print(f"  SC ranks for {len(sc_pos)} keywords")

    print("building competitor demand universe...")
    uni = build_universe()
    print(f"  universe: {len(uni)} unique keywords")

    collections = load_collections()

    # 1) filter to in-scope gap keywords
    candidates = []
    drops = defaultdict(int)
    for kw, d in uni.items():
        if BRAND_RE.search(kw):
            drops["brand"] += 1; continue
        if NEG_RE.search(kw):
            drops["noise"] += 1; continue
        if not CAT_RE.search(kw):
            drops["off-category"] += 1; continue
        if d["search_volume"] < MIN_VOLUME:
            drops["low-vol"] += 1; continue
        sc_p = sc_pos.get(kw)
        if sc_p is not None and sc_p <= GAP_POS:
            drops["sc-already-ranks"] += 1; continue
        ck = canon_key(kw)
        if ck is None:
            drops["dup-word"] += 1; continue
        candidates.append((ck, kw, d, sc_p))

    # 2) collapse word-order/stopword variants, keeping the highest-volume one
    best = {}
    for ck, kw, d, sc_p in candidates:
        if ck not in best or d["search_volume"] > best[ck][2]["search_volume"]:
            best[ck] = (ck, kw, d, sc_p)
    drops["variant"] = len(candidates) - len(best)

    # 3) build rows
    rows = []
    for ck, kw, d, sc_p in best.values():
        action, ptype, url, title, theme = map_page(kw, collections)
        line = product_line(detect_one(kw, MATERIALS), detect_category(kw)[0])
        vol = int(d["search_volume"])
        rows.append({
            "keyword": kw,
            "search_volume": vol,
            "expected_traffic_pos3": round(vol * POS3_CTR),
            "cpc": round(d["cpc"], 2),
            "keyword_difficulty": int(d["kd"]) if d["kd"] is not None else "",
            "competitors_ranking": len(d["competitors"]),
            "competitor_list": ",".join(sorted(d["competitors"])),
            "sc_current_position": int(sc_p) if sc_p is not None else "",
            "theme": theme,
            "sc_product_line": line,
            "recommended_action": action,
            "target_page_type": ptype,
            "target_handle_or_url": url,
            "target_page_title": title,
        })

    rows.sort(key=lambda r: r["search_volume"], reverse=True)
    top = rows[:TOP_N]

    print(f"\n  dropped: " + "  ".join(f"{k}:{v}" for k, v in sorted(drops.items())))
    print(f"  gap candidates: {len(rows)} -> taking top {len(top)} by volume")

    from collections import Counter as _Counter
    act = _Counter(r["recommended_action"] for r in top)
    print("  " + " | ".join(f"{k}: {v}" for k, v in act.most_common()))
    print(f"  distinct new collection pages to build: "
          f"{len({r['target_handle_or_url'] for r in top if r['recommended_action'].startswith('build new')})}")

    fields = ["keyword", "search_volume", "expected_traffic_pos3", "cpc",
              "keyword_difficulty", "competitors_ranking", "competitor_list",
              "sc_current_position", "theme", "sc_product_line",
              "recommended_action", "target_page_type",
              "target_handle_or_url", "target_page_title"]
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(top)
    print(f"wrote {OUT_CSV}")

    # ---- page-level rollup: built from the FULL candidate set (not the top-500
    # keyword slice) so winnable low-volume product pages (lyocell, modal, muslin,
    # waffle, sateen) survive instead of being buried under head terms.
    PAGE_MIN_VOL = 3000   # minimum total page demand to be worth a page
    pages = {}
    for r in rows:
        url = r["target_handle_or_url"]
        p = pages.setdefault(url, {
            "target_page_title": r["target_page_title"],
            "target_url": url,
            "sc_product_line": r["sc_product_line"],
            "recommended_action": r["recommended_action"],
            "target_page_type": r["target_page_type"],
            "keyword_count": 0, "total_search_volume": 0,
            "expected_traffic_pos3": 0, "kds": [], "kws": [],
        })
        p["keyword_count"] += 1
        p["total_search_volume"] += r["search_volume"]
        p["expected_traffic_pos3"] += r["expected_traffic_pos3"]
        if r["keyword_difficulty"] != "":
            p["kds"].append(r["keyword_difficulty"])
        p["kws"].append((r["search_volume"], r["keyword"]))

    def product_factor(line):
        if "no current line" in line:
            return 0.6                # demand exists but SC must build the product
        if line.startswith("—"):
            return 1.0                # broad category page (any fabric)
        return 1.15                   # backed by a real SC product line

    page_rows = []
    for p in pages.values():
        if p["total_search_volume"] < PAGE_MIN_VOL:
            continue
        avg_kd = round(sum(p["kds"]) / len(p["kds"])) if p["kds"] else ""
        winnability = ("" if avg_kd == "" else
                       "high" if avg_kd <= 20 else
                       "medium" if avg_kd <= 40 else "low")
        # priority = realistic traffic, discounted by difficulty and product fit.
        # difficulty factor: low KD -> ~1.0, high KD -> ~0.1; unknown -> 0.5 neutral.
        diff_factor = 0.5 if avg_kd == "" else max(0.1, min(1.0, (100 - avg_kd) / 100))
        priority = round(p["expected_traffic_pos3"] * diff_factor
                         * product_factor(p["sc_product_line"]))
        sorted_kws = sorted(p["kws"], reverse=True)
        head_vol = sorted_kws[0][0] if sorted_kws else 0
        top_kws = [k for _, k in sorted_kws[:10]]
        page_rows.append({
            "target_page_title": p["target_page_title"],
            "target_url": p["target_url"],
            "sc_product_line": p["sc_product_line"],
            "recommended_action": p["recommended_action"],
            "target_page_type": p["target_page_type"],
            "keyword_count": p["keyword_count"],
            "head_keyword_volume": head_vol,
            "total_search_volume": p["total_search_volume"],
            "expected_traffic_pos3": p["expected_traffic_pos3"],
            "avg_keyword_difficulty": avg_kd,
            "winnability": winnability,
            "priority_score": priority,
            "example_keywords": " | ".join(top_kws),
        })
    page_rows.sort(key=lambda r: r["priority_score"], reverse=True)
    pages_csv = DATA / "keyword_gap_pages.csv"
    with pages_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "target_page_title", "target_url", "sc_product_line",
            "recommended_action", "target_page_type", "keyword_count",
            "head_keyword_volume", "total_search_volume", "expected_traffic_pos3",
            "avg_keyword_difficulty", "winnability", "priority_score",
            "example_keywords"])
        w.writeheader()
        w.writerows(page_rows)
    print(f"wrote {pages_csv}  ({len(page_rows)} target pages, full candidate set)")

    # theme summary
    by_theme = defaultdict(lambda: [0, 0])
    for r in top:
        by_theme[r["theme"]][0] += 1
        by_theme[r["theme"]][1] += r["search_volume"]
    print("\nTop themes by total search volume:")
    for theme, (n, vol) in sorted(by_theme.items(), key=lambda x: x[1][1], reverse=True)[:25]:
        print(f"  {theme:<28} {n:>4} kws   {vol:>9,} vol")


if __name__ == "__main__":
    main()
