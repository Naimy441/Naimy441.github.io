# Mobile Order menu scraper

This folder contains a Mac workflow that captures fresh menus from the Mobile
Order app and saves the generated files under `outputs/mobile_order/`.

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
session. This interactive recapture step is available when running the script
from Terminal; cloud runs cannot complete the SSO login.

## Run it in the cloud with cron-job.org

The Mac app is not needed for scheduled fetches once you have a working
session. The repository's main GitHub Actions workflow includes a Mobile Order
refresh step:

```text
.github/workflows/main.yml
```

The workflow checks the saved Transact credentials, fetches all menus, and
commits changes to the Mobile Order JSON files. The Mobile Order step is
non-blocking: if its session is expired or fetching fails, the rest of the
workflow can still finish normally. It does not use the Mac app, mitmproxy,
AppleScript, or Accessibility.

### 1. Add the three GitHub Actions secrets

In the repository, open **Settings → Secrets and variables → Actions** and add:

```text
TRANSACT_LOGIN_TOKEN
TRANSACT_USER_ID
TRANSACT_SESSION_ID
```

Copy the values from the local `.transact-session.json` file. Do not commit that
file or put the Transact values in the cron-job.org URL.

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
