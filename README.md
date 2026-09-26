# Islam @ Duke Scraper — How to Use

## dukeislam.org — the new website

The `dukeislam/` folder contains the new [dukeislam.org](https://dukeislam.org) website — a modern, mobile-first Next.js app (shadcn/ui + Tailwind) that replaces the PDF-only site with:

- **Halal food** (`/food`): every halal item on campus with hours, search, and full nutrition facts — reads `outputs/halal_menus.txt` at runtime, so it stays fresh from the scraper below without redeploys
- **Events** (`/events`): a live list + month calendar of Muslim Life events from the DukeGroups feed
- **Prayer times**: today's timings on the home page (ISNA, Shafi Asr) plus a subscribable, auto-updating athan calendar feed at `/prayers.ics`

It deploys automatically to Vercel on push to `main` (Root Directory: `dukeislam`) and is refreshed by the direct NetNutrition workflow below. See [`dukeislam/README.md`](dukeislam/README.md) for details.

## Refreshing the halal catalog

The scheduled refresh uses the direct NetNutrition client as its primary path. It
fetches the current restaurant/menu/item data and nutrition labels over HTTP, then
adapts the results into the text, PDF, and website JSON formats. No browser, clicks,
or hardcoded waits are involved.

```bash
./refresh_catalog.sh
```

This runs, with a live progress display and per-step logs in `outputs/logs/`:

1. `netnutrition_client.py` — direct requests for current halal items and nutrition → `outputs/netnutrition-direct.json`
2. `build_catalog_outputs.py` — menu text/PDF and per-restaurant nutrition files
3. `extract-nutrition.mjs` — the compact catalog the website bundles → `dukeislam/data/nutrition.json`

Then review with `git status`, commit, and push — the Vercel deploy picks up the new catalog.

## Mobile Order menus

The Mac Mobile Order workflow refreshes current restaurant menus into
`outputs/mobile_order/`. Run `./mobile_order/refresh_menus.sh` locally; the
workflow can also refresh them through GitHub Actions when the saved Transact
session is valid.

## Direct NetNutrition client

`src/netnutrition_client.py` calls the NetNutrition session endpoints directly,
without Selenium or browser clicks. It can list restaurants, fetch menus and
items, and optionally fetch structured nutrition labels:

```bash
python src/netnutrition_client.py --list-units
python src/netnutrition_client.py \
  --unit "Tandoor Indian Cuisine" \
  --halal-only --nutrition \
  --output outputs/tandoor-netnutrition.json
```

Use `--unit-id` to select by NetNutrition `unitOid`, `--max-items` for a small
test, and `--insecure` only when a local TLS-intercepting proxy is replacing
the site certificate. The client verifies TLS by default.

---

Visit the website [naimy441.github.io](https://naimy441.github.io) to view the latest PDF version of the halal menus and Muslim events.

Alternatively, you can clone this repository and use the scripts provided:

- Use `netnutrition_client.py` for the primary no-browser refresh.
- Use `get_muslim_calendar.py` to get ICS resource from DukeGroups and output as PDF.
- The older Selenium scripts remain available only as historical/debugging fallbacks.

The refresh generates these catalog artifacts:
- `halal_menus.pdf`: A nicely formatted, colorful PDF version of the scraped menus.
- `halal_menus.txt`: A simplified, plain-text version of the menus.
- `outputs/restaurants/*.json`: Structured per-restaurant nutrition data.
- `dukeislam/data/nutrition.json`: The compact nutrition snapshot bundled by the website.

---

## 1. Install Python

Make sure you have **Python 3.x** installed. You can check by running:

```bash
python --version
```

If it’s not installed, [download Python here](https://www.python.org/downloads/).

---

## 2. Install Required Packages

Open your terminal or command prompt and run:

```bash
pip install -r requirements.txt
```

The direct refresh uses:

- **reportlab**: Generates the PDF output
- **requests**: Makes direct HTTP requests
- **beautifulsoup4**: Parses NetNutrition and Campus Hours responses

---

## 3. Run the Script

After cloning the repository, navigate to its directory and run one of the following scripts:

**For the primary direct refresh:**

```bash
./refresh_catalog.sh
```

The direct client can also be run by itself:

```bash
python src/netnutrition_client.py --halal-only --nutrition \
  --output outputs/netnutrition-direct.json
```

If traffic is being intercepted by the local mitmproxy certificate:

```bash
NETNUTRITION_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem ./refresh_catalog.sh
```

---

## 4. What Happens

- The direct client loads the NetNutrition page and keeps one HTTP session
- It selects units and menus through the observed MVC endpoints
- It parses menu fragments and requests nutrition labels directly
- The adapter fetches Campus Hours and preserves the existing output formats
- Writes the result into the catalog outputs:

```
halal_menus.txt
halal_menus.pdf
```

- The script gets the ICS feed directly from DukeGroups
- Writes the result into one output files:

```
muslim_calendar.pdf
```

 - The calendar includes events from the following groups:
```
28807 - CML
28808 - MSA
28704 - Graduate and Professional MSA
28600 - Duke Students for Justice in Palestine
72105 - Duke Black Muslim Coalition
73950 - One for All
```

---

## 5. Output Folders

The primary refresh writes `halal_menus.pdf` into `docs/outputs/`,
`halal_menus.txt` and per-restaurant JSON files into `outputs/`, and the bundled
nutrition catalog into `dukeislam/data/nutrition.json`.

`outputs/nutri_menus.json` is retained only for the older Selenium nutrition
scraper; the primary direct workflow does not regenerate it.

The older Selenium scripts remain available for historical/debugging use, but
they are no longer part of the scheduled refresh.

## 6. Output Example (`halal_menus.txt`)

```
Gothic Grill
  Build Your Own Taco Protein:
    - Grilled Chicken Breast
  Build Your Own Burger (Choose Your Ingredients):
    - Beef Patty
```

The PDF version (`halal_menus.pdf`) will have a similar layout but in a visually appealing format.

---

## 7. Notes

- The direct client removes duplicate item names within each restaurant/category.
- Chrome is only required for the historical Selenium scripts or optional
  mobile-order session recovery; scheduled refreshes do not launch it.
- `--delay` defaults to `0`; pass it only when a slower request rate is needed.
