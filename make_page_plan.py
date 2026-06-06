#!/usr/bin/env python3
"""
Reshape data/keyword_gap.csv into the requested page plan:
  A: Page
  B: New / Optimise
  C: To Rank For   (up to 10 top keywords, comma-separated)
  D: Expected Traffic Volume  (sum of monthly search volume of the page's keywords)

Output: data/page_plan.csv
"""
import csv
import json
from pathlib import Path
from collections import defaultdict, Counter

DATA = Path(__file__).parent / "data"
SRC = DATA / "keyword_gap.csv"
OUT = DATA / "page_plan.csv"
COLLECTIONS = DATA / "sc_collections.json"
MAX_KWS = 10


def existing_handles():
    data = json.loads(COLLECTIONS.read_text())
    return {handle for _, handle, _ in data["collections"]}


def classify(url, existing):
    """New vs Optimise decided by whether the collection already exists."""
    if url.startswith("/collections/"):
        handle = url.rsplit("/", 1)[-1]
        return "Optimise" if handle in existing else "New"
    return "New"  # /pages/ guide pages are net-new


def main():
    existing = existing_handles()
    pages = defaultdict(lambda: {"titles": Counter(), "kws": [], "vol": 0})
    with SRC.open() as f:
        for r in csv.DictReader(f):
            url = r["target_handle_or_url"]
            p = pages[url]
            p["titles"][r["target_page_title"]] += 1
            p["kws"].append((int(r["search_volume"]), r["keyword"]))
            p["vol"] += int(r["search_volume"])

    rows = []
    for url, p in pages.items():
        top_kws = [k for _, k in sorted(p["kws"], reverse=True)[:MAX_KWS]]
        rows.append({
            "Page": p["titles"].most_common(1)[0][0],
            "New / Optimise": classify(url, existing),
            "To Rank For": ", ".join(top_kws),
            "Expected Traffic Volume": p["vol"],
        })
    rows.sort(key=lambda r: r["Expected Traffic Volume"], reverse=True)

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "Page", "New / Optimise", "To Rank For", "Expected Traffic Volume"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT}  ({len(rows)} pages)")
    new = sum(1 for r in rows if r["New / Optimise"] == "New")
    print(f"  New: {new} | Optimise: {len(rows) - new}")


if __name__ == "__main__":
    main()
