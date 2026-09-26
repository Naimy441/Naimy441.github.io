# Islam @ Duke

Tools for the [dukeislam.org](https://dukeislam.org) website and its Duke dining
catalog.

## Primary catalog refresh

The current workflow uses direct HTTP requests to NetNutrition. It does not open
a browser or click through the website.

```bash
pip install -r requirements.txt
./refresh_catalog.sh
```

The workflow is:

1. `src/netnutrition_client.py` fetches restaurants, menus, halal items, and
   nutrition labels into the ignored intermediate file
   `outputs/netnutrition-direct.json`.
2. `src/build_catalog_outputs.py` writes the menu text/PDF and
   `outputs/restaurants/*.json`.
3. `dukeislam/scripts/extract-nutrition.mjs` builds the website's compact
   nutrition file at `dukeislam/data/nutrition.json`.

The request delay defaults to zero. The refresh writes:

- `outputs/halal_menus.txt`
- `docs/outputs/halal_menus.pdf`
- `outputs/restaurants/*.json`
- `dukeislam/data/nutrition.json`

If HTTPS is being intercepted by a local mitmproxy, provide its CA certificate:

```bash
NETNUTRITION_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem ./refresh_catalog.sh
```

GitHub Actions connects directly and does not need this variable.

## Run the direct client by itself

```bash
python src/netnutrition_client.py --list-units
python src/netnutrition_client.py \
  --unit "Tandoor Indian Cuisine" \
  --halal-only --nutrition \
  --output outputs/tandoor-netnutrition.json
```

Useful options include `--unit-id`, `--max-items`, `--delay`, `--ca-bundle`, and
`--insecure` for a trusted local TLS-intercepting proxy.

## Legacy Selenium workflow

The older browser-based scripts are still available for debugging or reproducing
the previous workflow, but they are not used by `refresh_catalog.sh` or the
scheduled catalog refresh:

- `src/scrape.py` — visible Chrome scrape.
- `src/bot_scrape.py` — headless Chrome scrape used by the old automation.
- `src/full_scrape.py` — broad menu scrape, including non-halal items.
- `src/nutri_scrape.py` — old browser-based nutrition scrape; writes
  `outputs/nutri_menus.json`.
- `src/nutri_split.py` — splits that legacy file into
  `outputs/restaurants/*.json`.

`outputs/nutri_menus.json` is retained for this legacy path only. The primary
direct workflow writes the per-restaurant files directly and does not regenerate
it. The legacy scripts require the browser/Selenium dependencies in
`requirements.txt`; `nutri_split.py` itself only needs Python.

## Other refreshes

- `src/get_muslim_calendar.py` refreshes the DukeGroups events PDF at
  `docs/outputs/muslim_calendar.pdf`.
- `mobile_order/refresh_with_reauth.py` fetches Mobile Order menus through the
  API using the saved session tokens. The scheduled workflow uses `--no-reauth`:
  if the tokens are missing or expired, existing exports are preserved.
- `mobile_order/refresh_menus.sh` is the separate local Mac-app/session-capture
  workflow.

## Website

The `dukeislam/` folder contains the Next.js website. Run it locally with:

```bash
cd dukeislam
npm install
npm run dev
```

The site deploys to Vercel from the `dukeislam` directory. See
[`dukeislam/README.md`](dukeislam/README.md) for website-specific details.
