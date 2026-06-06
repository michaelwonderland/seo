#!/usr/bin/env python3
"""
Reshape data/keyword_gap_pages.csv into the final page plan:
  A: Page
  B: New / Optimise
  C: SC Product Line          (which SC product/fabric backs the page)
  D: To Rank For              (up to 10 top keywords, comma-separated)
  E: Monthly Search Volume    (total demand across the page's keywords)
  F: Expected Traffic @ #3    (search volume x position-#3 CTR)
  G: Winnability              (high/medium/low, from avg keyword difficulty)
  H: Priority Score           (traffic x difficulty x product-fit; build order)

Sorted by Priority Score (best build-order first). New vs Optimise is decided by
whether the collection already exists in the live Shopify catalog.
Output: data/page_plan.csv
"""
import csv
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
SRC = DATA / "keyword_gap_pages.csv"
OUT = DATA / "page_plan.csv"
COLLECTIONS = DATA / "sc_collections.json"


def existing_handles():
    data = json.loads(COLLECTIONS.read_text())
    return {handle for _, handle, _ in data["collections"]}


def classify(url, existing):
    if url.startswith("/collections/"):
        return "Optimise" if url.rsplit("/", 1)[-1] in existing else "New"
    return "New"  # /pages/ guide pages are net-new


def main():
    existing = existing_handles()
    out = []
    with SRC.open() as f:
        for r in csv.DictReader(f):
            out.append({
                "Page": r["target_page_title"],
                "New / Optimise": classify(r["target_url"], existing),
                "SC Product Line": r["sc_product_line"],
                "To Rank For": ", ".join(r["example_keywords"].split(" | ")),
                "Monthly Search Volume": int(r["total_search_volume"]),
                "Expected Traffic @ #3": int(r["expected_traffic_pos3"]),
                "Winnability": r["winnability"],
                "Priority Score": int(r["priority_score"]),
            })
    out.sort(key=lambda r: r["Priority Score"], reverse=True)

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "Page", "New / Optimise", "SC Product Line", "To Rank For",
            "Monthly Search Volume", "Expected Traffic @ #3", "Winnability",
            "Priority Score"])
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT}  ({len(out)} pages)")
    new = sum(1 for r in out if r["New / Optimise"] == "New")
    print(f"  New: {new} | Optimise: {len(out) - new}")


if __name__ == "__main__":
    main()
