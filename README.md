# Keyword Research — sundaycitizen.co & the bedding competitor set

Pulls **non-brand organic keywords** for each domain from the DataForSEO Labs
`ranked_keywords` endpoint, ranked by **estimated traffic (ETV)**, and delivers
them as **one Google Sheet with a tab per domain**.

## Parameters
- Market: **United States** (`location_code 2840`), **English** (`language_code en`)
- Source: DataForSEO Labs → `ranked_keywords/live`
- Ranking: estimated traffic value (ETV), descending
- Per-domain selection rule (`SELECTION` in `keyword_research.py`):
  - sundaycitizen.co → **top 500** by ETV
  - brooklinen.com → **every keyword with ETV > 80**
  - potterybarn.com, latestbedding.com, tempurpedic.com, us.pigletinbed.com,
    parachutehome.com → **top 500** by ETV (the bedding competitor set surfaced
    by the competing-domains analysis)
- The endpoint caps at 1000 rows/call, so the script paginates (via `offset`)
  until the selection rule is satisfied.
- "Non-brand" = keyword does not match the brand regexes in `keyword_research.py`
  (e.g. brooklinen → `brooklinen`/`brooklyn linen`, tempurpedic → `tempur(-pedic)`,
  piglet in bed → `piglet`, parachute home → `parachute`, etc.)
- Run a subset by passing domains as args, e.g.
  `python3 keyword_research.py potterybarn.com tempurpedic.com` — no args runs all
  (avoids re-spending credits on domains already pulled).

## Columns delivered (per keyword)
`keyword · search_volume · etv (estimated traffic) · position · ranking_url · keyword_difficulty · cpc · search_intent`

The **ranking_url** is the page on the domain that ranks for the keyword and
earns the ETV.

## Network access requirement
The cloud environment's egress proxy must allow the DataForSEO host, or the
script fails with `403 Host not in allowlist` (this is the proxy, not
DataForSEO — no API credits are spent). In the environment's **Edit
environment** dialog:
- **Network access** → **Custom**
- **Allowed domains** → add `api.dataforseo.com`
- Keep **"Also include default list of common package managers"** checked
  (so PyPI stays reachable for `pip install openpyxl`)

Changes apply to **new** sessions, so start a fresh session after saving.

## Credentials (environment secrets)
Required env vars (added in the environment settings, injected at container boot):
- `DATAFORSEO_LOGIN`
- `DATAFORSEO_PASSWORD`

> NOTE: the **API password** is the generated key from the DataForSEO API
> dashboard, not the account login password.

## How to run (in a session where the secrets are present)
```bash
python3 keyword_research.py
```
This writes, into `./data/`:
- `raw_<domain>.json` — full API response (kept so we can re-slice without re-spending credits)
- `<domain>.csv` — top 500 non-brand keywords, ETV-descending

Then build + upload the 2-tab Google Sheet (handled via the Google Drive
integration in-session). `openpyxl` is needed for the workbook step:
```bash
pip install openpyxl
```

## Keyword expansion (`keyword_expansion.py`)
Expands a seed list (`data/seed_keywords.txt`) into **net-new** keyword
opportunities for brooklinen.com via DataForSEO Labs:
- `keyword_ideas/live` — topically relevant expansion (seeds batched ≤200/call).
- `keyword_suggestions/live` — long-tail variants for the top 50 seeds by volume.
- Excludes: brand, the seeds themselves, anything brooklinen **already ranks for**
  (full ranked set, cached to `data/brooklinen_ranked_keywords.txt`), and applies
  `search_volume ≥ 100`.
- Cleaning: a category-relevance gate on ideas-sourced terms, a negative-term
  list (furniture/mattresses, competitors, pests, deal/coupon noise), drops
  navigational intent, and collapses word-order/stopword variants + repeated-word junk.
- Output: `data/brooklinen_expansion.csv` (columns: keyword · search_volume · cpc ·
  competition · keyword_difficulty · search_intent · source).
- `REFILTER=1 python3 keyword_expansion.py` re-runs cleaning from saved raw
  responses with **no API calls**; `REFRESH_RANKED=1` forces a fresh ranked-set pull.

## Competing domains (`competitor_domains.py`)
Maps the **competitive bedding landscape for sundaycitizen.co**. The Brooklinen
keywords were only proxy seeds to define the niche; this step asks *who actually
owns traffic in that 6,031-keyword space*.

- Sends every keyword from `data/brooklinen_expansion.csv` to DataForSEO Labs
  `serp_competitors/live` in 200-keyword batches (batches are disjoint subsets).
- Each returned domain carries per-batch `keywords_count`, `etv`, `visibility`,
  `avg_position`; these sum cleanly across batches (`avg_position` recombined as
  a keyword-weighted mean).
- **traffic_share_pct** = a domain's ETV in the space ÷ total ETV of *all*
  domains in the space (heavyweights included in the denominator, so the share
  reflects the true landscape).
- Excludes generalist heavyweights (Amazon, Walmart, Target, Wayfair, …, plus
  social/search platforms) and SaaS/app contamination from generic terms
  ("sheets" → Google Sheets). Tags editorial/review sites (NYT/Wirecutter,
  Forbes, Sleep Foundation, …) as `category=publisher` so they can be split from
  `brand/retail` competitors.
- Output: `data/serp_competitors.csv` (columns: domain · category ·
  keywords_in_space · etv_in_space · traffic_share_pct · avg_position · visibility),
  sorted by ETV captured from the space.
- `REFILTER=1 python3 competitor_domains.py` re-aggregates from the cached raw
  responses with **no API calls** (used for tuning the exclude/publisher lists).

## Keyword gap → page plan (`keyword_gap.py`)
Turns the competitive landscape into an action plan: **which keywords Sunday
Citizen should rank for, and the page to do it with**.

- **Demand universe** = every keyword the bedding competitors rank for (their
  `*_com.csv` ranked sets) UNION `brooklinen_expansion.csv`, keeping the max
  search volume / CPC / ETV and the set of competitors ranking per keyword.
- **Gap** = universe keywords that sundaycitizen.co does **not** already rank for
  (absent, or best organic position > 20 — pulled fresh from `ranked_keywords`
  and cached to `data/sc_ranked_keywords.json`), restricted to product
  categories Sunday Citizen actually sells (soft textiles + home/decor; hard
  goods, competitor brands, and pure noise filtered out), deduped on
  word-order/stopword variants, top 500 by search volume.
- **Page mapping** uses the live Shopify catalog (`data/sc_collections.json`,
  pulled via the Shopify MCP):
  - bare head category (e.g. *sheets*, *quilt*) → **optimize** the existing
    category collection;
  - material/size/style + category (e.g. *percale sheets*, *king comforter
    sets*) → an existing dedicated collection if one matches, else **build a new
    collection page** (suggested handle + title);
  - informational queries (*bedding sizes*, *how to fold fitted sheets*) →
    **build a guide/blog page**.
- Outputs: `data/keyword_gap.csv` (per-keyword: volume · cpc · difficulty ·
  competitors_ranking · sc_current_position · theme · recommended_action ·
  target page) and `data/keyword_gap_pages.csv` (the rollup — one row per target
  page, ranked by total opportunity volume, with example keywords).
- `REFILTER=1 python3 keyword_gap.py` reuses the cached SC ranked set (no API calls).

## SC product-line demand (`material_demand.py`)
The Brooklinen-seeded universe missed Sunday Citizen's signature fabrics
(**zero** "lyocell"/"modal" keywords). This pulls `keyword_suggestions/live`
directly for SC's own catalog vocabulary so demand is measured against the real
product lines:

| SC line | total monthly vol |
|---|---|
| Crystal Weighted Blanket | 1.30M |
| Premium Lumière (Bamboo) | 1.04M |
| European Flax Linacel (Linen) | 1.01M |
| Cloud Cool / Cooling | 849k |
| Percale | 772k |
| Snug (Chunky Knit / Faux Fur) | 619k |
| Organic Cotton | 400k |
| Waffle | 224k |
| **Silky Lyocell (TENCEL™)** | **192k** ("lyocell" 27k @ KD 11) |
| Muslin | 191k |
| Luce Cotton Sateen | 128k |
| **Naked Modal** | **71k** |

Outputs `data/material_keywords.csv` (every textile keyword + the SC line) and
`data/material_demand.csv` (per-line rollup). These keywords are fed back into
the gap universe so the lyocell/modal/muslin/waffle/sateen pages surface.

## SERP reality-check + realistic plan (`serp_winnability.py`)
The page plan is reality-checked against **live Google SERPs** so winnability and
traffic reflect what actually ranks, not a DataForSEO KD guess. For each page's
top keywords it pulls `serp/google/organic/live/advanced` and judges:

- **PEER** domains (DTC bedding brands of similar authority — Brooklinen,
  Parachute, Coyuchi, Sheet Society, Bedsure, Sijo, …): if peers rank, SC can.
- **HARD** walls (Amazon/Walmart/Wayfair/big-box + publishers like Wirecutter):
  a SERP owned by these is not winnable for a mid-authority brand.
- **Head-term cap**: brand-defining terms ("sheets" 2.2M) stay low/medium even
  when peers eventually rank — they're multi-year authority plays, not quick wins.

`winnability (SERP)` = high / medium / low, with a `SERP Reality` evidence string
(which peers rank, which walls dominate). **Realistic Traffic /mo** = total page
demand × a capture rate set by winnability (high 6%, medium 1.8%, low 0.3%) —
replacing the unrealistic "#3 for everything." Product-gap pages (no SC product:
flannel/percale/microfiber) are dropped. Output rewrites `data/page_plan.csv`,
sorted by realistic traffic. Raw SERPs cache to `data/raw_serp_winnability.json`;
`REFILTER=1` re-tunes the scoring with no API calls.

## Expected traffic at position #3 (gap-engine ceiling)
`keyword_gap.py` reports **`expected_traffic_pos3` = search_volume × POS3_CTR**
(`POS3_CTR = 0.10`, industry-avg organic CTR at rank #3). The page plan is
ranked by this so it reflects realistic capture, not raw demand. Each page is
tagged with the **SC product line** that backs it (or flagged `— no current
line` where it's a product gap, e.g. percale/flannel) and a **winnability**
score (high/medium/low from avg keyword difficulty), giving a deliberate mix of
high-volume head pages and low-volume, low-competition product pages.

`data/page_plan.csv` is the clean deliverable:
Page · New/Optimise · SC Product Line · To Rank For (≤10 kws) · Monthly Search
Volume · Expected Traffic @ #3 · Winnability.

## Status / handoff
- ✅ Run completed 2026-06-06:
  - `data/sundaycitizen_co.csv` — top 500 by ETV (46 brand keywords filtered out)
  - `data/brooklinen_com.csv` — 1,049 keywords with ETV > 80 (190 brand filtered out, 2 pages pulled)
  - Bedding competitor set, top 500 by ETV each: `data/potterybarn_com.csv`
    (261 brand filtered), `data/latestbedding_com.csv` (0 brand),
    `data/tempurpedic_com.csv` (971 brand, 2 pages), `data/us_pigletinbed_com.csv`
    (15 brand), `data/parachutehome_com.csv` (90 brand)
  - `data/brooklinen_expansion.csv` — 6,031 net-new keywords from 1,042 seeds
  - `data/serp_competitors.csv` — 10,452 competing domains (38 heavyweights excluded)
    ranked by traffic share in the bedding space.
  - `data/keyword_gap.csv` — top 500 gap keywords (with expected_traffic_pos3 +
    SC product line) mapped to a target page; `data/keyword_gap_pages.csv` /
    `data/page_plan.csv` — 204 target pages ranked by expected traffic @ #3
    (172 New, 32 Optimise), each tagged with backing SC product line +
    winnability. Catalog snapshot in `data/sc_collections.json`.
  - `data/material_demand.csv` / `data/material_keywords.csv` — SC product-line
    demand pulled against the real catalog vocabulary.
  - Raw API responses saved alongside as `raw_<domain>.json`.
- Workbook `Keyword Research.xlsx` now has 13 tabs: the 7 domains, `brooklinen —
  expansion`, `competing domains`, `PAGE PLAN`, `GAP — pages (detail)`,
  `GAP — top 500 keywords`, and `SC material demand`.
- **Strategic read:** sundaycitizen.co ranks **#1006** among brand/retail
  competitors in its own category (15 keywords / ~1,427 ETV) — i.e. almost the
  entire 6k-keyword bedding space is whitespace for it. Top specialist
  competitors capturing that traffic: The Company Store, Pottery Barn, Beddy's,
  Bedsure, Piglet in Bed, Sheet Society, Peacock Alley, Parachute, Coyuchi,
  Magic Linen, Coop Sleep Goods.
