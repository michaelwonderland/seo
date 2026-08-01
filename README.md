# SEO Analysis — DataForSEO pulls

Scripts that build SEO profiles from the DataForSEO Labs + Backlinks APIs.

## Credentials (environment secrets)
Required env vars (added in the environment settings, injected at container boot):
- `DATAFORSEO_LOGIN`
- `DATAFORSEO_PASSWORD`

> NOTE: the **API password** is the generated key from the DataForSEO API
> dashboard, not the account login password.

Every script caches each API response to `data/raw/<name>.json` and skips the
call if the file already exists, so re-runs are free. Delete a cache file to
force a refresh.

---

## 1. `seo_profile.py` — Wasser's Furniture baseline profile

Market: **United States** (`location_code 2840`), **English** (`language_code en`).
Target: `wassersfurniture.com`.

Pulls, for the target:
- `domain_rank_overview` — position distribution, ETV, traffic value
- `historical_rank_overview` — 6-month trend
- `ranked_keywords` split into **page 1 (pos 1–10)**, **page 2 (11–20)**,
  **page 3 (21–30)** using organic `rank_group`
- `backlinks/summary`, `referring_domains`, `anchors`, `backlinks`
- `competitors_domain` — algorithmic organic competitors

Outputs to `data/`:
| file | contents |
|---|---|
| `target_keywords_page1/2/3.csv` | ranked keywords by SERP page |
| `target_keywords_all.csv` | pages 1–3 combined |
| `target_history.csv` | monthly keyword/traffic trend |
| `target_referring_domains.csv` | top 100 referring domains |
| `target_anchors.csv` | anchor text distribution |
| `target_backlinks.csv` | 200 backlinks, one per domain |
| `competitors_overview.csv` | domain-overlap competitors |
| `profile.json` | everything, structured |

> Caveat: the `metrics` block returned by `competitors_domain` is scoped to the
> **shared** keyword set, not the competitor's whole site. Use
> `competitor_comparison.csv` (script 2) for like-for-like totals.

## 2. `competitive_analysis.py` — market + competitor deep-dive

- `backlinks/domain_pages` — which linked pages are now 4xx (lost link equity).
  This endpoint rejects `order_by`, so rows are pulled wide and sorted locally.
- Sizes a seed set of South Florida luxury-furniture commercial keywords
  (`bulk_keyword_difficulty` + Google Ads `search_volume`).
- `serp_competitors` on those keywords — who actually owns the money SERPs.
  Ranked by **share of the keyword set**, not median position, so a site that
  ranks #1 for one obscure term doesn't outrank one owning a dozen head terms.
- Profiles a curated competitor list (`CURATED_COMPETITORS`) like-for-like:
  organic overview + backlink summary + top page-1 keywords.

Outputs to `data/`:
| file | contents |
|---|---|
| `market_seed_keywords.csv` | seed keyword volumes, CPC, difficulty |
| `serp_competitors_raw.csv` | every domain on the money SERPs |
| `competitor_comparison.csv` | target vs competitors, like-for-like |
| `competitor_kw_<domain>.csv` | each competitor's top page-1 keywords |
| `target_pages_by_backlinks.csv` | linked pages + HTTP status |
| `target_broken_pages_with_links.csv` | 4xx pages still holding links |
| `competitive.json` | everything, structured |

## How to run
```bash
python3 seo_profile.py
python3 competitive_analysis.py
python3 ranking_loss.py
```

## 3. `ranking_loss.py` — year-over-year comparison

- `historical_rank_overview` back to Jun 2024 (**26 months** of position-band
  counts) — the ranking-mix trend and the Aug 2025 vs Aug 2026 comparison.
- `ranked_keywords` with **`historical_serp_mode: "lost"`** — every keyword the
  domain used to rank for and no longer does, with the last position held and,
  critically, **the URL that held it**. That last field is what identifies the
  migration as the cause.

Outputs to `data/`:
| file | contents |
|---|---|
| `history_26mo.csv` | 26 months of keywords/ETV/position bands |
| `yoy_ranking_mix.csv` | Aug 2025 vs Aug 2026 per position band |
| `lost_keywords.csv` | all 819 lost rankings + last position + lost URL |
| `lost_recoverable_page1.csv` | the 185 page-one rankings lost on legacy URLs |
| `ranking_loss.json` | everything, structured |

## 4. `keyword_research.py` — earlier one-off
Top 500 non-brand keywords by ETV for `sundaycitizen.com` and `brooklinen.com`.
Unrelated to the Wasser's work; kept for reference.

---

## Headline findings — Wasser's Furniture (Aug 2026)

1. **Down 91.6% year on year.** Aug 2025: 2,262 keywords / 4,497 est. monthly
   visits. Aug 2026: 191 keywords / 892 visits. Two distinct phases — erosion
   Dec 2024–Jul 2025 (page-one keywords 769 → 331), nine flat months, then a
   cliff from May 2026 (366 → 20).
2. **Cause: an un-redirected replatform.** The site moved from a legacy
   Magento-style `.html` URL structure to Shopify `/products/<slug>`
   (IP `23.227.38.74`, Cloudflare in front). Legacy URLs return **404, not 301**.
   Of the **819 lost rankings, 801 (97.8%) were held by a legacy `.html` URL**;
   only 3 were lost on a live Shopify page.
3. **No category layer.** 98 of the top 100 indexed URLs are `/products/` PDPs.
   The site has essentially nothing to rank on category terms.
4. **65% of remaining organic traffic is one branded term** ("wassers", 578 of
   892 ETV). Non-brand organic is negligible.
5. **Absent from the top 100** for every commercial term tested, local
   ("furniture stores miami", "luxury furniture miami") and category
   ("modern coffee table", "glass dining table") alike.
6. **Backlink profile is small and spammy** — 392 referring domains, spam score
   26, dominated by blogspot link farms and domains like `daolink.mom`,
   `buzzshrink.website`, `beforeitsnews.com`.
