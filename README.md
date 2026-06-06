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

## Status / handoff
- Script written and committed.
- ✅ Run completed 2026-06-06:
  - `data/sundaycitizen_co.csv` — top 500 by ETV (46 brand keywords filtered out)
  - `data/brooklinen_com.csv` — 1,049 keywords with ETV > 80 (190 brand filtered out, 2 pages pulled)
  - Raw API responses saved alongside as `raw_<domain>.json`.
