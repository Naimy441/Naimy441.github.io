# Mobile Order menu scraper

This folder contains a Mac workflow that captures fresh menus from the Mobile Order app and saves them as JSON files.

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

The script opens Mobile Order, finds its process automatically, starts headless capture, opens the first available restaurant, captures the session, and fetches all restaurant menus.

## Output

Fresh menu files are written directly to:

```text
mobile_order/menus/
```

The run also refreshes:

```text
mobile_order/restaurants.json
mobile_order/all_restaurant_menus.json
```

The compact exports keep restaurant names, icon URLs, current open status, estimated wait time, simple weekly takeout/delivery hours, section names, item names and descriptions, prices, inner options such as sizes and add-ons, busy/normal pickup minutes, and visibility flags.

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
