# Keyword Research — sundaycitizen.co & brooklinen.com

Pulls **non-brand organic keywords** for each domain from the DataForSEO Labs
`ranked_keywords` endpoint, ranked by **estimated traffic (ETV)**, and delivers
them as **one Google Sheet with two tabs** (one per domain).

## Parameters
- Market: **United States** (`location_code 2840`), **English** (`language_code en`)
- Source: DataForSEO Labs → `ranked_keywords/live`
- Ranking: estimated traffic value (ETV), descending
- Per-domain selection rule (`SELECTION` in `keyword_research.py`):
  - sundaycitizen.co → **top 500** by ETV
  - brooklinen.com → **every keyword with ETV > 80**
- The endpoint caps at 1000 rows/call, so the script paginates (via `offset`)
  until the selection rule is satisfied.
- "Non-brand" = keyword does not match the brand regexes in `keyword_research.py`
  - sundaycitizen.co → `sunday citizen`, `sundaycitizen`
  - brooklinen.com → `brooklinen`, `brooklyn linen`

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

## Status / handoff
- ✅ Run completed 2026-06-06:
  - `data/sundaycitizen_co.csv` — top 500 by ETV (46 brand keywords filtered out)
  - `data/brooklinen_com.csv` — 1,049 keywords with ETV > 80 (190 brand filtered out, 2 pages pulled)
  - `data/brooklinen_expansion.csv` — 6,031 net-new keywords from 1,042 seeds
  - Raw API responses saved alongside as `raw_<domain>.json`.
- Workbook `Keyword Research.xlsx` now has 3 tabs (the two domains + `brooklinen — expansion`).
