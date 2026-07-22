# dukeislam.org

Modern web app for Islam @ Duke — every halal food option on Duke's campus plus a live
calendar of Muslim Life events. Built with Next.js, Tailwind CSS v4, shadcn/ui, and
Motion. Mobile-first, works great on desktop.

## How data flows

This app is a frontend over the existing scraping pipeline in the repo root — the
pipeline itself was not modified.

| Data | Source | Freshness |
|------|--------|-----------|
| Halal menus | `outputs/halal_menus.txt`, fetched at runtime from `raw.githubusercontent.com` | GitHub Actions re-scrapes twice daily; pages revalidate every 30 min (ISR) |
| Events | DukeGroups ICS feed, fetched at runtime | Pages revalidate every 30 min (ISR) |
| Nutrition facts | `data/nutrition.json`, bundled at build | Static snapshot from `outputs/restaurants/*.json` |
| Prayer times | AlAdhan API (`calendarByAddress`, ISNA method, Shafi Asr) for 2080 Duke University Road | Cached 12h |

## Prayer times

- The home page shows today's five prayer times (plus sunrise) with the next athan
  highlighted. Calculation: ISNA method with Shafi Asr (`method=2&school=0`).
- `/prayers.ics` is a public calendar feed: a 5-minute event at each athan for the
  current month. Subscribe via `webcal://dukeislam.org/prayers.ics` (the "Subscribe"
  button on the home page) and it auto-refreshes — the feed regenerates every 12
  hours (rolling into each new month) and calendar apps re-poll it periodically
  (`X-PUBLISHED-TTL: PT12H`).

Because menus and events are fetched at runtime with ISR, the site stays fresh
**without** needing a redeploy when the scraper commits new data.

### Refreshing nutrition data

After re-running the nutrition scrape (`src/nutri_scrape.py` + `src/nutri_split.py` in
the repo root), regenerate the bundled snapshot and commit it:

```bash
npm run extract-nutrition
```

## Local development

```bash
npm install
npm run dev
```

## Deploying to Vercel

1. Import `Naimy441/duke_halal` in Vercel (Add New → Project).
2. Set **Root Directory** to `dukeislam`. Framework preset: Next.js. No env vars needed.
3. Add the `dukeislam.org` domain under Project → Settings → Domains and point your
   DNS at Vercel (A record `76.76.21.21` or the CNAME Vercel shows you).

Vercel then auto-deploys on every push to `main`.

### Coexistence with the existing GitHub Actions setup

Nothing in `.github/workflows/main.yml` was changed. It keeps scraping twice daily and
committing PDFs + `outputs/halal_menus.txt` to `main`, and GitHub Pages keeps serving
`docs/` as before.

Those bot commits will also trigger Vercel deploys. That's harmless, but unnecessary
(data is fetched at runtime). To skip them, in Vercel go to Project → Settings → Git →
**Ignored Build Step** and choose "Only build Production if there are changes to the
Root Directory" — scrape commits never touch `dukeislam/`, so they won't rebuild.
