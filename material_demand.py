#!/usr/bin/env python3
"""
Measure real search demand for Sunday Citizen's actual product lines / materials.

The Brooklinen-seeded universe under-represents SC's signature fabrics (it has
ZERO "lyocell"/"modal" keywords). This pulls keyword_suggestions/live directly
for SC's own material vocabulary so we can answer "is there volume for lyocell?"
authoritatively, and feed those keywords back into the gap/page plan.

Outputs:
  data/material_keywords.csv   (every textile-relevant keyword found, w/ volume + SC line)
  data/material_demand.csv     (per-line rollup: total volume, #kws, top kws)
  data/raw_material_demand.json (cached raw responses)

Auth: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD
  REFILTER=1  rebuild from cached raw (no API calls)
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

SUGGEST_URL = "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live"
LOCATION_CODE = 2840
LANGUAGE_CODE = "en"
LIMIT = 250
MIN_VOL = 20

HERE = Path(__file__).parent
DATA = HERE / "data"
RAW = DATA / "raw_material_demand.json"
KW_CSV = DATA / "material_keywords.csv"
ROLLUP_CSV = DATA / "material_demand.csv"

# Sunday Citizen product line -> seed material words (their real catalog vocab)
SC_LINES = {
    "Silky Lyocell (TENCEL™)":      ["lyocell", "tencel"],
    "Premium Lumière (Bamboo)":     ["bamboo sheets", "bamboo bedding", "bamboo duvet", "bamboo pillowcase"],
    "Naked Modal":                  ["modal sheets", "modal bedding", "modal pajamas"],
    "European Flax Linacel (Linen)":["linen sheets", "linen duvet cover", "french linen bedding", "linen pillowcase"],
    "Muslin":                       ["muslin blanket", "muslin bedding", "muslin throw"],
    "Waffle":                       ["waffle blanket", "waffle towel", "waffle robe", "waffle duvet"],
    "Luce Cotton Sateen":           ["sateen sheets", "cotton sateen sheets"],
    "Percale":                      ["percale sheets"],
    "Cloud Cool / Cooling":         ["cooling sheets", "cooling comforter", "cooling blanket", "cooling duvet"],
    "Snug (Chunky Knit / Faux Fur)":["chunky knit blanket", "faux fur throw", "knit throw blanket"],
    "Crystal Weighted Blanket":     ["weighted blanket"],
    "Organic Cotton":               ["organic cotton sheets", "organic cotton bedding"],
    "Velvet":                       ["velvet quilt", "velvet duvet"],
    "Bath / Towels":                ["turkish towels", "bamboo towels", "organic cotton towels"],
}

# textile relevance gate (drop "bamboo plant", "modal verb", etc.)
CAT_TERMS = ["sheet", "sheets", "bedding", "duvet", "comforter", "blanket",
             "blankets", "throw", "throws", "pillow", "pillows", "pillowcase",
             "pillowcases", "sham", "shams", "quilt", "quilts", "towel", "towels",
             "robe", "robes", "bedspread", "coverlet", "sheets set", "linens",
             "pajama", "pajamas", "loungewear", "bathrobe"]
CAT_RE = re.compile(r"\b(" + "|".join(map(re.escape, CAT_TERMS)) + r")\b")
BARE_MATERIAL = {"lyocell", "tencel", "modal", "muslin", "waffle", "sateen",
                 "percale", "linen", "linens"}


def relevant(kw):
    return bool(CAT_RE.search(kw)) or kw.strip() in BARE_MATERIAL


def auth_header():
    login = os.environ.get("DATAFORSEO_LOGIN")
    pw = os.environ.get("DATAFORSEO_PASSWORD")
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


def norm(kw):
    return re.sub(r"\s+", " ", (kw or "").strip().lower())


def main():
    if os.environ.get("REFILTER"):
        raw = json.loads(RAW.read_text())
    else:
        headers = auth_header()
        raw = {}
        for line, seeds in SC_LINES.items():
            for seed in seeds:
                payload = [{
                    "keyword": seed, "location_code": LOCATION_CODE,
                    "language_code": LANGUAGE_CODE, "limit": LIMIT,
                    "order_by": ["keyword_info.search_volume,desc"],
                    "filters": [["keyword_info.search_volume", ">=", MIN_VOL]],
                }]
                r = requests.post(SUGGEST_URL, headers=headers, json=payload, timeout=120)
                r.raise_for_status()
                raw.setdefault(line, []).append({"seed": seed, "resp": r.json()})
                print(f"  {line:<32} seed='{seed}'")
        RAW.write_text(json.dumps(raw))

    # aggregate: keyword -> (volume, cpc, kd, SC line). First line that claims it wins.
    kw_rows = {}
    for line, entries in raw.items():
        for entry in entries:
            for it in items_of(entry["resp"]):
                kw = norm(it.get("keyword"))
                if not kw or not relevant(kw):
                    continue
                info = it.get("keyword_info") or {}
                props = it.get("keyword_properties") or {}
                vol = info.get("search_volume") or 0
                if kw not in kw_rows or vol > kw_rows[kw]["search_volume"]:
                    kw_rows[kw] = {
                        "keyword": kw,
                        "search_volume": vol,
                        "cpc": round(info.get("cpc") or 0, 2),
                        "keyword_difficulty": props.get("keyword_difficulty") or "",
                        "sc_product_line": line,
                    }

    rows = sorted(kw_rows.values(), key=lambda r: r["search_volume"], reverse=True)
    with KW_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["keyword", "search_volume", "cpc",
                                          "keyword_difficulty", "sc_product_line"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {KW_CSV}  ({len(rows)} unique textile keywords)")

    # per-line rollup
    by_line = defaultdict(lambda: {"vol": 0, "kws": []})
    for r in rows:
        by_line[r["sc_product_line"]]["vol"] += r["search_volume"]
        by_line[r["sc_product_line"]]["kws"].append((r["search_volume"], r["keyword"]))
    roll = []
    for line, d in by_line.items():
        top = [k for _, k in sorted(d["kws"], reverse=True)[:8]]
        roll.append({"sc_product_line": line, "keyword_count": len(d["kws"]),
                     "total_search_volume": d["vol"], "top_keywords": ", ".join(top)})
    roll.sort(key=lambda r: r["total_search_volume"], reverse=True)
    with ROLLUP_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sc_product_line", "keyword_count",
                                          "total_search_volume", "top_keywords"])
        w.writeheader()
        w.writerows(roll)
    print(f"wrote {ROLLUP_CSV}\n")
    print(f"{'SC product line':<32}{'#kw':>5}{'total vol':>11}")
    for r in roll:
        print(f"  {r['sc_product_line']:<30}{r['keyword_count']:>5}{r['total_search_volume']:>11,}")


if __name__ == "__main__":
    main()
