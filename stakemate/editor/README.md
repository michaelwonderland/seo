# Stakemate — Google Ads Editor import

`Stakemate_Search_Recommended_Build.csv` is the full recommended build in the same format as
Michael's 3 Sep export (UTF-16, tab-delimited, Google Ads Editor column set). Import via
Editor → Account → Import → From file. Everything is created **Paused**.

## Review of the 3 Sep export (WM | UK | Non-Brand | Web-to-App | Phrase)

Fix these before enabling, whether or not the recommended file is imported:

1. **Networks includes Search Partners.** Switch to Google search only.
2. **Audiences look like Targeting, not Observation.** Campaign "Audience targeting: Audience
   segments" with Flexible Reach "Audience segments", and Sports Fans (90200) + All Converters
   attached. If that is Targeting mode the campaign only serves to those two lists. Check in the
   UI and set both to Observation.
3. **Languages = All.** Set English.
4. **"Ad group 1" is a catch-all** holding betting app, offers, sites, bet builder and football
   keywords, and those same keywords are duplicated in the themed ad groups ("free bets",
   "betting sign up offers", "football betting", "new customer free bets", "betting offers").
   Duplicates bid against each other. Rename Ad group 1 to "Betting App" and keep only the app
   keywords there (the recommended file does this).
5. **"Sign Up - Free Bet Offers" appears twice** in the export with identical keywords and ad.
   Delete one.
6. **Final URL is `http://stakemate.com`.** Use the landing page
   `https://www.stakemate.com/stakemate-bet-together-win-together` and add the AppsFlyer
   final URL suffix at campaign level (in the recommended file).
7. **Headline "Bet £10 ‍Get £20 free bets" contains a hidden zero-width joiner** between
   "£10" and "Get". It will render oddly and can trip policy review. Retype it as
   "Bet £10, Get £20 Free Bets" (used in the recommended file).
8. **"Free Betting App" (Headline 3)** reads as a free-bet claim next to the offer copy. The
   recommended file drops it in favour of the offer line in H15.
9. **No negative keywords** in the export. The recommended file adds campaign-level negatives
   (brand, no-deposit/bonus-hunter, offshore, informational, lottery/bingo/social-casino, and
   cross-negatives between Sports and Casino). Competitor names are **not** negatives: they
   signal intent and stay in play for now; review them in the search-term report and negate
   individually later if they do not convert. No single-word "free" negative anywhere, since
   free-bet keywords are targeted; the only free-prefixed negatives are multi-word bonus-hunter
   phrases ("free money", "free play", "free slots", "free casino") plus "free spins" on
   Sports only.
10. Budget £300/day kept as set. Casino £100/day, Brand £25/day.

## RSA structure (unchanged from Michael's)

Headline 1 "Stakemate" unpinned by design. Headline 13 "18+ | BeGambleAware" pinned position 3.
Description 4 compliance line pinned position 2. Headline 14 = the ad-group-specific line.
Headline 15 = offer line ("Bet £10, Get £20 Free Bets") or a second theme line.

## What is in the file

| Campaign | Ad groups | Keywords | Negatives |
|---|---|---|---|
| WM \| UK \| Non-Brand \| Sports \| Phrase | Betting App · Social - Bet With Mates · Sign Up - Free Bet Offers · New Betting Sites · Acca & Bet Builder · Football Betting | 56 phrase | 106 incl. casino cross-negatives |
| WM \| UK \| Non-Brand \| Casino \| Phrase | Online Casino & Casino App · Slots · Live Casino & Table Games · Casino Offers | 30 phrase | 104 incl. sports cross-negatives |
| WM \| UK \| Brand \| Search | Brand - Core · Brand - Sports · Brand - Casino · Brand - Offers · Brand - Misspellings | 25 phrase + [stakemate] exact | 25 |

Brand bidding: the export format has no columns for impression-share settings, so the row says
"Target impression share" and the Comment column carries 90% / Absolute top / £2.50 cap. Set
those in the UI after import.
