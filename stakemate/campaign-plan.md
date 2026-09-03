# Stakemate — UK Non-Brand Web-to-App Search Campaign (Phase 2 build sheet)

Prepared 2026-09-02 from the Stakemate Google Ads account (customer 905-682-2850, under the
Wonderland.marketing MCC), the "Stakemate: Google Ads Action Plan" doc, and DataForSEO Labs
keyword data (United Kingdom, English). Match type: **phrase only**, per Michael's brief. Stakemate offers both sportsbook and casino, and
Meta is already split Sports / Casino, so Search mirrors that: sports ad groups and casino ad groups
with their own keywords and ads (section 2), and a rebuilt Brand campaign (section 7).

Data files in this folder:
- `data/dataforseo_uk_keywords.csv` — 3,517 UK keywords with volume, CPC, intent, difficulty, bucket
- `dataforseo_research.py` / `bucket_keywords.py` — the pulls and the bucketing logic

---

## 0. What the account looks like today (last 90 days, 4 Jun – 2 Sep 2026)

| Campaign | Status | Bidding | Spend | Clicks | Conv | Notes |
|---|---|---|---|---|---|---|
| Phrase Match – Mixed | Paused | Maximise clicks | £11,586 | 4,054 | 0 | Ran **broad** `casino`, `place bet`, `free spins`. Display on. Presence-or-interest. |
| Brand | Enabled | Max conv value | £1,311 | 166 | 0 | `stakemate casino` on broad. Display on. Presence-or-interest. |
| UK – Value – Search Terms | Enabled | Max conversions | £1,913 | 1,129 | 0 | 605k impressions at 0.19% CTR = Display on. Exact-match sports keywords. |

Things the new campaign has to fix or route around:

- **Zero negative keywords anywhere.** No ad-group negatives, no campaign negatives, no shared
  negative lists. The only shared set is a `Stakemate` brand list (type BRANDS, 1 member).
- **Conversions are not wired for bidding.** The three AppsFlyer iOS events (`sign_up`,
  `session_start`, `ecommerce_purchase`) exist but are all `primary_for_goal = false`. The
  account's primary goals are "YouTube channel subscriptions", "YouTube follow-on views",
  "Page view" and an offline upload. Every campaign shows 0 conversions in 90 days. Max
  Conversions will have nothing to learn from until `sign_up` is made primary (or set as the
  campaign-level goal).
- **Brand leaks into non-brand.** `stakemate betting` was the single biggest search term in the
  non-brand campaigns (100 clicks via phrase `betting app`, 34 via `place bet`, 17 via
  `gambling app`). Brand negatives are mandatory on the new campaign.
- **Search-term waste, 90 days** (all from the paused campaign unless noted): competitor brands
  (`mystake` £194, `virgin bet` £163, `william hill` £103, `sky vegas` £100, `databet` £129,
  `goldenbet`, `winner bet`, `yellowbet`, `chatki bet`, `midnite`, `paddy power`), casino /
  free-spins (`free spins no deposit` + variants ≈ £600), bonus hunters (`free bets no deposit`
  £67 in the live campaign), offshore (`sportybet nigeria`, `top non uk gambling sites`),
  informational (`bet calculator`, `lucky 15 tips`, `racecards`, `odds to win premier league`),
  and `stake` exact (76 clicks, £248 — that is Stake.com traffic, not Stakemate).
- **Landing page** used by both live campaigns: `https://www.stakemate.com/stakemate-bet-together-win-together`.
  Only Brand carries AppsFlyer parameters (`?af_c_id={campaignid}&utm_source=googleads`).
- Real CPCs in the account: phrase `betting app` £1.31, phrase `gambling app` £1.43,
  exact `betting sites` £10.67, exact `free bets` £10.85, exact `new betting apps` £11.78.
  DataForSEO's CPC column (USD, Google top-of-page estimate) reads $40–$80 for the same terms;
  treat it as a relative signal only.

---

## 1. Campaign settings

| Setting | Value |
|---|---|
| Campaign name | `UK \| Non-Brand \| Sports \| Phrase` and `UK \| Non-Brand \| Casino \| Phrase`. Two campaigns recommended (see 2b); if it has to be one, name it `UK \| Non-Brand \| Web-to-App \| Phrase` and keep the ad-group split exactly as below. |
| Type / goal | Search. Objective "App promotion" is **not** used (that forces App campaigns); use Search with a conversions goal. |
| Networks | Google Search only. **Search partners off. Display Network off.** |
| Locations | United Kingdom (geo 2826). Location option: **Presence** only (not presence-or-interest). Exclude: none needed once Presence is set. |
| Languages | English |
| Bidding | **Maximise conversions, no target** for weeks 1–3. Move to Target CPA at ideal +50% once ≥30 conversions in 30 days (Phase 1 point 3). |
| Conversion goal | Campaign-specific goal: **`com.stakemate (iOS) sign_up`** (AppsFlyer). Add the Android sign-up event the moment the Android link exists. Do *not* inherit the account default goals (YouTube / page view). Keep `session_start` and `ecommerce_purchase` as secondary/observation. |
| Daily budget | £100/day to start (same as the current campaigns). Doc target is ~30 sign-ups per 30 days; at the current £66 brand cost-per-sign-up that needs ≥£70/day, so £100 gives headroom. |
| Ad rotation | Optimise: prefer best performing ads |
| Devices | Mobile + tablet. **Desktop bid adjustment −100%** unless web sign-up without the app is possible — confirm with Stakemate. (Under Max Conversions only −100% adjustments are honoured.) |
| Ad schedule | None at launch. Revisit after 4 weeks of hourly data. |
| Start / end | Start on approval, no end date |
| Final URL (ad-level) | `https://www.stakemate.com/stakemate-bet-together-win-together` — the page must OS-detect to the right store with one dominant download CTA (Phase 2 point 4). |
| Final URL suffix (campaign-level) | Mirror Brand's AppsFlyer pattern and extend it so every layer is attributed: `af_c_id={campaignid}&af_adset_id={adgroupid}&af_ad_id={creative}&af_keywords={keyword}&utm_source=googleads&utm_medium=cpc&utm_campaign={campaignid}` — confirm the parameter names against the AppsFlyer OneLink/Google integration before saving. |
| Brand exclusions | Apply the existing `Stakemate` brand list as a **brand exclusion** on this campaign (belt and braces alongside the negatives). |
| Negative lists | Attach the shared list in section 4. |
| Audiences | Observation only: all-app-users (AppsFlyer/Firebase) and website visitors 30d. No targeting narrowing. |
| EU/UK political, ad content | Gambling certification must already be on the account (ads are approved under ONLINE_GAMBLING policy today). |

---

## 2. Ad groups and phrase keywords

Volumes are UK monthly searches from DataForSEO (Google's grouped volume, so close
variants share one figure). "Acct CPC" is the observed average CPC for the same keyword in
this account over the last 90 days where one exists.

### AG1 — Betting App (core theme, tightest intent)
| Phrase keyword | UK vol | Note |
|---|---|---|
| "betting app" | 18,100 | Acct CPC £1.31 on phrase. Brand negatives essential (`stakemate betting app` matched this). |
| "betting apps" | 18,100 | |
| "sports betting app" | 1,600 | |
| "football betting app" | 880 | |
| "new betting app" | 590 | Acct exact CPC £11.78 |
| "uk betting app" | 3,600 | |
| "betting app uk" | 3,600 | |
| "best betting app" | 8,100 | Comparison intent; keep but watch CPA, drop first if it lags. |
| "bookmaker app" | n/a | Low/no volume in dataset, cheap to include. |

### AG2 — Social / Bet With Mates (the proposition; low volume, high fit)
| Phrase keyword | UK vol |
|---|---|
| "bet with friends" | 70 |
| "bet with friends app" | 50 |
| "betting with friends app" | 50 |
| "social betting" | 40 |
| "social betting app" | n/a |
| "group bet" | 70 |
| "group betting" | n/a |
| "bet with mates" | n/a |
| "betting with mates" | n/a |
| "bet against friends" | n/a |

Total demand here is only a few hundred searches a month, but it is exactly the product. These
are the searches that should convert best and they are cheap. Keep this ad group even if it
reports "low search volume" on some terms.

### AG3 — Sign-up Offers / Free Bets
| Phrase keyword | UK vol | Note |
|---|---|---|
| "betting sign up offers" | 4,400 | Acct exact CPC £9.93 |
| "betting sign up offer" | — | singular variant |
| "free bets" | 14,800 | Acct exact CPC £10.85. High volume, attracts bonus hunters; `no deposit` negatives do the filtering. |
| "free bet offers" | 2,900 | Acct exact CPC £5.99 |
| "free bets uk" | 2,400 | |
| "free bets on sign up" | 1,600 | |
| "bookmaker sign up offers" | 1,600 | |
| "welcome offers betting" | 1,600 | |
| "betting welcome offer" | — | |
| "new customer free bets" | 720 | Acct exact CPC £3.22 |
| "new customer betting offers" | — | |
| "bet 10 get 20" | — | matches the live offer (£20 free bets for £10) |
| "betting offers" | 4,400 | broad-ish; monitor search terms weekly |

### AG4 — New Betting Sites / Bookmakers
| Phrase keyword | UK vol | Note |
|---|---|---|
| "new betting sites" | 9,900 | |
| "new betting sites uk" | 6,600 | |
| "new bookmakers" | 1,300 | |
| "new online betting sites" | 390 | |
| "betting sites" | 49,500 | Acct exact CPC £10.67. Biggest generic; keep in its own ad group so it can be budget-capped or paused without touching the rest. |
| "online betting" | 9,900 | |
| "online betting sites" | 6,600 | |
| "uk bookmakers" | 3,600 | |
| "online bookmakers" | 4,400 | |

### AG5 — Acca / Bet Builder
| Phrase keyword | UK vol |
|---|---|
| "bet builder" | 2,400 |
| "bet builder app" | n/a |
| "accumulator betting" | 1,300 |
| "accumulator bets" | 1,300 |
| "acca betting" | 1,000 |
| "football accumulator" | 2,400 |
| "acca app" | n/a |

Negatives `tips`, `tip`, `calculator`, `advice`, `hydraulic`, `profit accumulator` keep this
clean (the raw list is full of hydraulic accumulators and tipster sites).

### AG6 — Football Betting
| Phrase keyword | UK vol |
|---|---|
| "football betting" | 14,800 |
| "football betting sites" | 2,900 |
| "football betting online" | 1,900 |
| "online football betting" | 1,900 |
| "football betting uk" | 1,000 |
| "bet on football" | — |
| "premier league betting" | — |
| "bet on premier league" | — |

**Held back on purpose:** horse racing and greyhounds (12,100 + 27,100 UK searches) until
Stakemate confirms racing is in the product; "gambling app" / "gambling sites" (mixed intent,
neither sports nor casino).

### 2b. Casino ad groups (AG7–AG10)

Stakemate has a casino product and Meta already runs Sports and Casino as separate campaigns.
Search should do the same. **Recommendation: two campaigns, not one.** Casino CPCs run higher
(DataForSEO shows casino terms $10–$30 above the equivalent sports terms), casino queries carry
the heaviest bonus-hunter share (the paused campaign's £11.6k went mostly on `casino` and
`free spins` broad), and casino will want its own landing page in Phase 3. Separate campaigns
give each product its own budget and its own bidding history. If it must be one campaign, keep
these four ad groups as-is; the ad copy is what has to differ.

The old campaign already tried casino on **broad** match with `casino`, `online casino`,
`casino welcome bonus`, `UK casino`. What it matched was competitor brands (mystake, sky vegas,
goldenbet, mecca, foxy, rolletto) and no-deposit hunting. Phrase match plus the negatives below
is the fix, not dropping casino.

#### AG7 — Online Casino / Casino App
| Phrase keyword | UK vol | Note |
|---|---|---|
| "online casino uk" | 27,100 | |
| "uk online casino" | 9,900 | |
| "casino sites" | 22,200 | Biggest generic; same treatment as "betting sites". |
| "uk casino sites" | 18,100 | |
| "new online casino" | 5,400 | |
| "new casino sites" | 8,100 | |
| "new uk casino" | 2,400 | Old campaign's `UK casino` broad, now phrase. |
| "casino apps" | 2,400 | |
| "casino app" | — | |
| "online casino app" | — | |
| "uk casino app" | — | |
| "casino betting app" | 70 | Both products in one query; the Stakemate pitch. |
| "mobile casino" | — | |

#### AG8 — Slots
| Phrase keyword | UK vol |
|---|---|
| "online slots" | 49,500 |
| "online slots uk" | 18,100 |
| "slot sites" | 8,100 |
| "slot app" | 720 |
| "slots app" | — |
| "play slots online" | — |

#### AG9 — Live Casino & Table Games
| Phrase keyword | UK vol |
|---|---|
| "live casino" | 8,100 |
| "live casino uk" | 1,900 |
| "online roulette" | 2,900 |
| "online blackjack" | 2,400 |
| "roulette app" | — |
| "blackjack app" | — |

Only build AG9 if live dealer, roulette and blackjack are in the Stakemate casino. Confirm.

#### AG10 — Casino Offers
| Phrase keyword | UK vol | Note |
|---|---|---|
| "casino sign up bonus" | 3,600 | |
| "casino welcome bonus" | — | Old campaign ran this on broad and got "free bonus on registration no deposit uk". Phrase + `no deposit` negatives. |
| "casino welcome offer" | — | |
| "casino sign up offer" | — | |
| "new customer casino offer" | — | |

**Casino offer to confirm.** The live ads mention only the sports offer (£20 free bets for £10).
AG10 and the casino RSA need the real casino welcome offer wording (bonus, spins, wagering)
before build; the compliance line must include "wagering requirements apply" if there are any.

**Cross-negatives between the two campaigns.** Sports campaign: add `casino`, `slots`, `slot`,
`roulette`, `blackjack`, `live casino`, `spins` as negatives. Casino campaign: add `football`,
`acca`, `accumulator`, `bet builder`, `horse racing`, `free bets`, `sports betting` as
negatives. Neither campaign then competes with the other for the same query.

Roughly 55 sports and 30 casino phrase keywords across ten ad groups. Themes graduate to their
own campaign or landing page on their own conversion volume (Phase 2 point 5 / Phase 3 point 6).

---

## 3. Why phrase-only works here, and what it needs

Phrase match today includes close variants and implied intent, so "betting app" will match
"stakemate betting app", "best betting app for horse racing" and "betting app no deposit
bonus". That is fine as a Phase 2 net, but only with the negative list below applied from
day one and a weekly search-term review. If the exact-match `UK – Value – Search Terms`
campaign stays live alongside, it will split impressions with this one on the same queries;
recommendation is to pause it at launch and re-add any of its exact keywords that had traction
(`free bets no deposit` should not come back — it is a bonus-hunter term).

---

## 4. Shared negative keyword list — `Stakemate | Non-Brand Exclusions`

Attach to both non-brand campaigns and to `UK – Value – Search Terms`. The same list gates AI
Max in Phase 3. Use phrase match for multi-word entries and broad for single words unless noted.
Casino terms are **not** on this list any more; they live as cross-negatives on the Sports
campaign only (section 2b).

**Brand (keeps brand in the Brand campaign)**
stakemate, stake mate, steakmate, steak mate, stalemate, stale mate, stakemate app,
[stake] (exact — Stake.com traffic, £248 wasted on it)

**Competitors: not negated.** Competitor names (bet365, william hill, mystake, databet, sky vegas
and the rest seen in search terms) signal betting intent and stay in play. Review them in the
weekly search-term report and negate individually only if they fail to convert.

**Lottery, bingo, poker and social-casino games (not the product)**
lottery, lotto, euromillions, 49s, bonus ball, scratch, scratchcard, bingo, poker, mahjong,
solitaire, coin master, monopoly go, slotomania, house of fun, pop slots, cashman, mines,
free spins (phrase — every "free spins" query in 90 days was no-deposit hunting; lift it only if
the casino welcome offer is spins-based)

**Bonus hunters**
no deposit, without deposit, without any deposit, no wagering, no wager, on registration,
free money, risk free, free play, demo, free slots, free casino

**Offshore / non-UK**
non uk, non-uk, not on gamstop, gamstop, offshore, crypto, nigeria, kenya, ghana, india,
australia, usa, ireland, irish, canada, south africa

**Informational and tools**
tips, tip, tipster, prediction, predictions, predictor, odds, calculator, racecard, racecards,
results, result, meaning, what is, how to, how does, explained, rules, glossary, guide,
strategy, jobs, careers, news, login, log in, sign in, track my bet, cash out calculator,
hydraulic, profit accumulator, advice

**Not-the-product**
fantasy, fpl, fut, fifa, ea fc, web app, football manager, greyhound, greyhounds,
horse racing (pending product confirmation), pools, placepot, placepots

---

## 5. Responsive search ad (one per ad group, swap the pinned H1 per theme)

**Compliance rule (applies to every ad).** The three live RSAs each contain an "18+ | GambleAware"
asset (Brand: headline; UK – Value: headline and description; Phrase Match – Mixed: description)
but none of them is pinned, so Google can serve combinations with no age or GambleAware line.
The Brand offer description also has no "Terms apply". In the new campaign:

- Pin "18+ | BeGambleAware" to headline position 3 in every RSA.
- Pin "18+ | BeGambleAware.org | New UK customers only | T&Cs apply." to description position 2.
- Any headline, description, sitelink or callout that names the £20 offer carries "Terms apply"
  inside that same asset, so it cannot serve without it.

Current live RSAs rate Poor / Average / Good; aim for Excellent by using all 15 headlines and
4 descriptions with distinct content.

**Headlines (max 30 chars)**
1. *(pinned H1, per ad group)* AG1 `New UK Betting App` · AG2 `Bet With Your Mates` · AG3 `Bet £10, Get £20 Free Bets` · AG4 `New UK Betting Site` · AG5 `Build Your Acca Together` · AG6 `Football Betting With Mates`
2. Bet Together, Win Together
3. The Betting App For Mates
4. UK Licensed Betting App
5. £20 In Free Bets For New Users
6. Download Free On iOS & Android
7. Social Sports Betting App
8. Bet On Football With Friends
9. Instant Withdrawals
10. Build Bets In Group Chats
11. UK's #1 Social Betting App
12. Sign Up In Under 2 Minutes
13. Share Your Bets, Split The Win
14. New Customer Welcome Offer
15. *(pinned H3)* 18+ | BeGambleAware

**Descriptions (max 90 chars)**
1. Stakemate is the UK betting app built for mates. Pool stakes, back the same bet, win together.
2. Download the app, sign up and get £20 in free bets when you bet £10. Terms apply. 18+.
3. UK licensed, instant withdrawals and regular free bets. Bet together, win together.
4. *(pinned D2)* 18+ | BeGambleAware.org | New UK customers only | T&Cs apply.

**Assets**
- Sitelinks: Welcome Offer (T&Cs apply) · How It Works · Download for iPhone · Download for Android
- Callouts: UK Licensed · Instant Withdrawals · £20 Free Bets, T&Cs Apply · Bet With Mates
- Structured snippet (Types): Football, Acca, Bet Builder, Group Bets, Free Bets
- App asset: link the iOS app (ID 6446404482) and Android once linked
- Business name and logo assets

### Casino RSA (AG7–AG10)

Same compliance rule. Pinned H1 per ad group: AG7 `New UK Online Casino` · AG8 `Play Slots
On Stakemate` · AG9 `Live Casino On Your Phone` · AG10 `Casino Welcome Offer` (offer wording
to be confirmed).

**Headlines 2–15**
2. Stakemate Casino App
3. Slots, Roulette & Blackjack
4. UK Licensed Online Casino
5. Casino & Sportsbook In One App
6. Download Free On iOS & Android
7. Instant Withdrawals
8. New Customer Casino Offer *(needs "Terms apply" in the description it serves with; pin D2)*
9. Play Casino With Your Mates
10. Hundreds Of Slot Games
11. Live Dealer Tables
12. Sign Up In Under 2 Minutes
13. Brand New UK Casino
14. Spin, Bet, Win Together
15. *(pinned H3)* 18+ | BeGambleAware

**Descriptions**
1. Brand new UK casino app from Stakemate. Slots, live roulette and blackjack, plus the sportsbook.
2. *(pinned D2)* 18+ | BeGambleAware.org | New UK customers only | T&Cs and wagering apply.
3. Download the app, sign up and claim your casino welcome offer. Terms apply. 18+.
4. UK licensed, instant withdrawals, casino and sports betting in one place.

**Assets:** sitelinks Casino Welcome Offer (T&Cs apply) · Slots · Live Casino · Download the App;
callouts UK Licensed · Instant Withdrawals · Casino & Sportsbook · 18+ BeGambleAware;
structured snippet (Types): Slots, Roulette, Blackjack, Live Casino.

---

## 6. Pre-launch checklist (blocks launch if unchecked)

1. `com.stakemate (iOS) sign_up` set as the campaign conversion goal (or account primary).
2. Android conversion link live, or accept iOS-only optimisation and revisit.
3. Landing page OS-detects and has one download CTA; AppsFlyer parameters on the final URL suffix.
4. Shared negative list created and attached; `Stakemate` brand list applied as brand exclusion.
5. Display Network and Search partners off; location option = Presence.
6. `UK – Value – Search Terms` paused (or its exact keywords consciously kept as a twin).
7. Desktop decision made (−100% or not).
8. Weekly search-term review booked; theme graduation threshold agreed (suggest: a theme earns
   its own landing page at 10 sign-ups in 30 days).

---

## 7. Brand campaign — rebuild

### What Brand is doing today (90 days)

| | |
|---|---|
| Bidding | Maximise conversion value, with no conversion values recorded, so effectively unconstrained bidding |
| Avg CPC | **£7.90** overall; `stakemate casino` broad **£11.87**; `stakemate betting` exact £6.10; `stakemate` phrase £7.45 |
| Spend | £1,311 for 166 clicks, 0 recorded conversions |
| Networks | Display on |
| Location | Presence-or-interest |
| Keywords | 14, mixing exact, phrase and **broad** (`stakemate casino`, `stalemate betting`, `stale mate betting` on broad) |
| Search terms | Clean: `stakemate betting` (81 clicks), `stakemate` (25), `stakemate bet`, `stakemate welcome offer`, `stakemate promo code`. The problem is price, not relevance. |
| Ad | One RSA, strength Good, "18+ \| Gambleaware" headline unpinned, offer description with no "Terms apply" |
| Landing page | `/stakemate-bet-together-win-together?af_c_id={campaignid}&utm_source=googleads` |

Paying £6–£12 a click for your own brand name with no negatives and Display on is the
account's most fixable leak. The doc says brand's £66 per sign-up cannot be the benchmark;
the setup below is why it is that high.

### Settings

| Setting | Value |
|---|---|
| Name | `UK \| Brand \| Search` |
| Networks | Google Search only. Search partners off. Display off. |
| Location | United Kingdom, **Presence** only |
| Bidding | **Target impression share, 90% absolute top of page, max CPC bid limit £2.50.** Brand does not need Smart Bidding to find the right auctions; it needs a ceiling. Review the cap after two weeks: if impression share is below 80%, raise to £3.50. |
| Conversion goal | `com.stakemate (iOS) sign_up` for reporting (bidding is not conversion-based here) |
| Budget | **£25/day** (current run-rate is £14.60/day at inflated CPCs; the cap will bring CPC down and volume up) |
| Final URL suffix | Same AppsFlyer suffix as non-brand |
| Brand list | Keep the `Stakemate` brand list attached (it is the brand-inclusion signal if AI Max is ever tested on Brand) |
| Devices | Same desktop decision as non-brand |

### Ad groups and keywords (phrase, plus exact on the pure brand term; no broad)

| Ad group | Keywords |
|---|---|
| Brand – Core | [stakemate] · "stakemate" · "stake mate" · "stakemate app" · "stakemate betting" · "stakemate bet" · "stakemate download" |
| Brand – Casino | "stakemate casino" · "stake mate casino" · "stakemate slots" |
| Brand – Offers | "stakemate welcome offer" · "stakemate promo code" · "stakemate free bet" · "stakemate sign up offer" · "stakemate bonus" |
| Brand – Misspellings | "steakmate" · "steak mate" · "stalemate betting" · "stalemate casino" · "stalemate app" · "stale mate betting" |

The misspelling group must stay on phrase with a betting/casino/app modifier: `stalemate` on its
own is a chess word (and the current broad `stalemate betting` can reach it).

### Brand campaign negatives

- `[stake]`, "stake com", "stake casino", "stake login", "stake us", "stake uk", "stake bet" (Stake.com; `stake` exact already cost £248 in the non-brand campaign)
- "chess", "stalemate meaning", "stalemate definition", "stalemate rules", "what is a stalemate"
- "login", "log in", "sign in", "withdrawal", "customer service", "contact" (existing users; they will find the app anyway, and these queries do not create sign-ups)
- "jobs", "careers", "linkedin", "reviews", "trustpilot", "scam" (informational)

### Brand RSA (one per ad group; pinned H1 changes)

Pinned H1: Core `Stakemate Official App` · Casino `Official Stakemate Casino` · Offers
`Stakemate Welcome Offer` · Misspellings `Stakemate Official App`.

Headlines 2–15: Bet Together, Win Together · Download The Official App · Bet £10, Get £20
Free Bets · The Betting App For Mates · Sports Betting & Casino · UK Licensed · Instant
Withdrawals · Sign Up In Under 2 Minutes · Bet On Football With Friends · Slots, Roulette &
Blackjack · New Customer Welcome Offer · Free On iOS & Android · Bet With Your Mates · *(pinned
H3)* 18+ | BeGambleAware.

Descriptions: 1. The official Stakemate app. Bet on sport and play casino with your mates, in
one place. · 2. *(pinned D2)* 18+ | BeGambleAware.org | New UK customers only | T&Cs apply. ·
3. Sign up today and get £20 in free bets when you bet £10. Terms apply. 18+. · 4. UK licensed,
instant withdrawals and regular free bets. Download the official Stakemate app.

Assets: sitelinks Download for iPhone · Download for Android · Welcome Offer (T&Cs apply) ·
Casino; callouts Official App · UK Licensed · Instant Withdrawals · 18+ BeGambleAware; app asset;
business name and logo.

### Pre-launch for Brand

1. Switch bidding to Target impression share with the £2.50 cap **before** anything else; this alone should cut CPC by more than half.
2. Turn Display off and set Presence.
3. Replace the three broad keywords with the phrase set above.
4. Attach the brand negatives.
5. Pin the compliance headline and description, add "Terms apply" to the offer description.
