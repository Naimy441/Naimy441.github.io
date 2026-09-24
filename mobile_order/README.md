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

The temporary captured session is stored locally in `.transact-session.json` with restricted permissions and is not included in the menu JSON exports.
