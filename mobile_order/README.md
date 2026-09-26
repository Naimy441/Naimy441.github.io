# Mobile Order menu scraper

This folder contains a Mac workflow that captures fresh menus from the Mobile
Order app and saves the generated files under `outputs/mobile_order/`.

## Files in this folder

### Normal GitHub Actions and web-login flow

- `refresh_with_reauth.py` is the main refresh coordinator. It tests the
  current Transact session, fetches normally when it works, and starts web SSO
  recapture only after an authentication failure. When configured, it uses a
  private Vercel Blob as the persistent session store.
- `check_transact_session.py` makes one small menu request to determine whether
  the current login token is usable. Exit code `0` means valid, `1` means an
  authentication rejection, and `2` means a network, file, or setup problem.
- `fetch_fresh_menus.py` requests every restaurant menu and atomically updates
  the JSON exports under `outputs/mobile_order/`.
- `recapture_web_session.py` runs mitmdump and headless Chrome, submits the
  Duke web SSO form, computes the app's HMAC-SHA256 registration hash, captures
  the resulting Transact session, and can fetch menus afterward.
- `HASH_DISCOVERY_README.md` documents how the native app's SSO hash algorithm
  was identified. It is documentation only and is not required at runtime.

### Mac Mobile Order app flow

- `refresh_menus.sh` is the all-in-one Mac app workflow. It checks the current
  session, opens Mobile Order when needed, starts local process capture, opens
  a restaurant, and fetches fresh menus.
- `capture_transact_session.py` is the mitmproxy addon used by
  `refresh_menus.sh` to save session fields from Mobile Order traffic.
- `open_first_menu.applescript` clicks the first available restaurant in the
  Mac app. It requires Terminal Accessibility permission.

### Optional utilities

- `download_restaurant_icons.py` downloads restaurant icon images separately
  into `outputs/mobile_order/images/`.
- `build_restaurant_matching_files.py` creates the restaurant-scoped
  names-only comparison files used to match Mobile Order menus with nutrition
  data.
- `README.md` is this usage guide.

The `__pycache__/` folder contains automatically generated Python bytecode. It
is not source code, is ignored by Git, and can be deleted at any time.

## Before running

Make sure:

1. The **Mobile Order** Mac app is downloaded and installed.
2. You are already logged in to Mobile Order.
3. mitmproxy is installed.
4. mitmproxy's certificates are trusted in the **login** keychain in **Keychain Access**.
5. The **Mitmproxy Redirector** extension is enabled at:

   **System Settings → General → Login Items & Extensions → Extensions**

6. Terminal has Accessibility permission so the script can open the first restaurant automatically:

   **System Settings → Privacy & Security → Accessibility**

## Run

From the project root:

```bash
./mobile_order/refresh_menus.sh
```

The script first tests the saved credentials and fetches menus directly when
they still work. If authentication fails, it opens Mobile Order, starts
headless capture, pauses for the Duke SSO login, opens the first restaurant,
captures a new session, and retries the fetch.

If Mobile Order is logged out, the script pauses so you can complete the Duke
SSO login in the app, then retries the restaurant click and captures the new
session. This is the separate Mac-app recapture flow; the GitHub Actions flow
uses the web SSO recapture described below.

## Run it in the cloud with cron-job.org

The Mac app is not needed for scheduled fetches once you have a working
session. The repository's main GitHub Actions workflow includes a Mobile Order
refresh step:

```text
.github/workflows/main.yml
```

The workflow first checks the saved Transact credentials. If they are valid, it
fetches the menus normally. If Transact rejects them as expired, the workflow
starts headless mitmdump and headless Chrome, submits the Duke SSO form using
`TRANSACT_NETID` and `TRANSACT_PASSWORD`, captures a new session, and fetches the menus.
The workflow also reads and updates the private Blob session using
`BLOB_STORE_ID` and `BLOB_READ_WRITE_TOKEN`.
Other network or setup errors do not trigger a blind login. The Mobile Order
step is non-blocking: if it ultimately fails, the rest of the workflow can
still finish normally. It does not use the Mac app, AppleScript, or
Accessibility.

### 1. Add the GitHub Actions secrets

In the repository, open **Settings → Secrets and variables → Actions** and add:

```text
TRANSACT_LOGIN_TOKEN
TRANSACT_USER_ID
TRANSACT_SESSION_ID
TRANSACT_NETID
TRANSACT_PASSWORD
BLOB_STORE_ID
BLOB_READ_WRITE_TOKEN
```

Copy the three `TRANSACT_*` values from the local `.transact-session.json` file.
Add the Duke login values as separate secrets. Do not commit captured sessions,
passwords, or put any of these values in the cron-job.org URL.

Add `BLOB_STORE_ID` and `BLOB_READ_WRITE_TOKEN` to **GitHub Actions Secrets**
as well as Vercel. GitHub Actions does not automatically inherit Vercel
project environment variables. The Blob store must be private.

Keep `TRANSACT_LOGIN_TOKEN`, `TRANSACT_USER_ID`, and `TRANSACT_SESSION_ID` if
you want the workflow to test the existing session and avoid logging in on
every run. Removing them means the GitHub runner has no saved session to test;
the current workflow will stop rather than blindly recapture.

The workflow downloads `mobile-order/transact-session.json` from Blob before
checking credentials. If the session is valid, it fetches normally. If it is
expired, it logs in headlessly, uploads the refreshed session back to Blob, and
fetches the menus. The local runner copy is temporary and is never committed.

The helper implementing this decision is:

```bash
python3 mobile_order/refresh_with_reauth.py --output-dir outputs/mobile_order
```

For local headless testing, put `TRANSACT_NETID` and `TRANSACT_PASSWORD` in the
project-root `.env` file and run the same helper. `.env` is ignored by Git.
Duke MFA or WebAuthn may still require the visible login mode on a local Mac.

## Check whether the saved session still works

To test the captured session without opening Mobile Order or refreshing every
menu, run:

```bash
python3 mobile_order/check_transact_session.py
```

The script makes one menu request for the first restaurant and never prints the
token values. It exits with `0` when the session works, `1` when Transact
rejects the session because of authentication, and `2` for a missing file,
network/setup problem, or unrelated server error.

The fetcher itself now stops immediately on a Transact session-expired response
with exit code `3` and leaves the existing menu exports untouched. Use
`./mobile_order/refresh_menus.sh` for the interactive recapture flow.

## Output

Fresh menu files are written directly to:

```text
outputs/mobile_order/menus/
```

The run also refreshes:

```text
outputs/mobile_order/restaurants.json
outputs/mobile_order/all_restaurant_menus.json
```

The compact exports keep restaurant names, icon URLs, current open status, estimated wait time, simple weekly takeout/delivery hours, section names, item names and descriptions, prices, inner options such as sizes and add-ons, busy/normal pickup minutes, and visibility flags.

### Download restaurant icons once

Icon downloading is separate from the menu refresh workflow. To download the
icons referenced by the current exports into `outputs/mobile_order/images/`, run:

```bash
python3 mobile_order/download_restaurant_icons.py
```

The script is safe to run again and does not modify the menu JSON files.

### Build a names-only comparison dataset

To create a small dataset containing only restaurant names, dish names, menu
sections/categories, and Mobile Order option names:

```bash
python3 mobile_order/build_restaurant_matching_files.py
```

It writes:

```text
outputs/mobile_order/restaurant_matching/
```

Each file in `restaurant_matching/` contains one Mobile Order restaurant and
the Nutrition restaurant records that are relevant to it. Nutrition records are
read from the canonical files in `outputs/restaurants/`. Each file also has a
`restaurant_match` section showing the Mobile Order name, matched Nutrition
name(s), and whether the pairing used a normalized name or an alias. Dish,
option group, and option value records keep stable IDs; restaurant-level IDs
are omitted because each file is already restaurant-scoped. Restaurants
without a Nutrition source have an empty `nutrition` list. When there is one
clear Nutrition match, the matching file uses the same filename as its source
file in `outputs/restaurants/`; unmatched or multi-source restaurants use a
Mobile Order-based filename.

`price` is expressed in dollars.

## Understanding item options

Menu items keep their inner options, including choices such as small/medium/large,
creamer, creamer amount, and flavor shots. Each option group has these fields:

- `minimum`: the fewest choices the customer must make in that group.
- `maximum`: the most choices the customer may make in that group.
- `allow_quantity`: whether a choice can be added with a quantity.
- `values`: the choices in the group, including their names, prices, defaults,
  hidden/out-of-stock status, and any per-choice quantity limit.

For example, Bella Union's Espresso item has an **Espresso Sizes** group with
`minimum: 1` and `maximum: 1`. That means the customer must choose exactly one
size. A group with `minimum: 0` is optional, while a larger `maximum` allows
multiple choices.

`max_quantity` applies to one individual choice. A value of `0` generally means
that the menu did not configure a separate per-choice limit; it does not mean
the choice is unavailable. Use `is_out_of_stock` to identify unavailable
choices. `is_hidden` indicates that a choice or item is hidden from customers.

The temporary captured session is stored locally in `.transact-session.json` with restricted permissions and is not included in the menu JSON exports.
