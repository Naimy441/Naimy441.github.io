# Transact Mobile Order API inventory

This is the current endpoint worksheet for the Duke Mobile Order client. It
combines observed mitmproxy traffic, the existing scraper, and the installed
2026.3.1 Mobile Order binary. A targeted Ghidra headless import plus binary
string/reference extraction was used to replace guessed endpoint keys wherever
the client contains an exact literal.

Use it only with an account and campus you are authorized to access. The
request templates contain placeholders and never include captured credentials.
The ordering, payment, account-changing, and cancellation calls are listed for
documentation only; do not replay them against production while exploring.

## Confidence labels

- **Confirmed** — observed in traffic or present in the working scraper.
- **Binary-confirmed key** — the exact lower-case endpoint key is present in the
  shipped client and is passed through the common API request builder. The
  `/api_user/<key>` prefix is confirmed for the observed menu/auth calls.
- **Source-confirmed** — the client call site exposes parameters, but the exact
  key or complete body still needs a traffic check.
- **Inferred** — derived from a selector or feature name only; do not treat the
  guessed path as confirmed.

## Binary findings from the installed client

The exact endpoint-key literals found in the local `Transact Prod` binary are:

```text
addcreditcard                  addcreditcardgeturl
addmealplandirectauth          addmealplantoken
calculatecart                  cancelpendingorder
changecampus                   changedefaultpaymentmethod
checkinorder                   changedietaryrestrictions
getaffiliationswithcampus      getallmenusforcampus
getcampuslocations             getcampuseswithbundlename
getcampuseswithbundlenamesecondary
getcontests                    getinboxmessages
getloyaltydata                 getmenu
getpastorders                  getpendingorders
getreviewquestions             getuser
ldaplogin                      loginwithemailandpassword
loginwithtoken                 logout
logoutanddelete                openedmessage
processorder                   processorderstaged
processorderstatuscheck        purchasereward
rateorder                      registerwithapple
registerwithcampusssotoken     registerwithcampussso
registerwithemail              registerwithsso
removepaymentmethod            submitcontestentry
submitrevieworder              trackappevents
validatepromocodeonetime
```

The binary contains selector names for the Amazon verification, app-rating,
photo-upload, and generic API-dispatch features, but no matching lower-case
endpoint literal was found in this pass. Those remain unresolved rather than
being presented as definite paths.

## Common request setup

The app's `APIUtility` builds JSON `POST` requests like this:

```bash
BASE='https://mobileorderprodapi.transactcampus.com'
LOGIN_TOKEN='REDACTED_LOGIN_TOKEN'
SESSION_ID='REDACTED_SESSION_ID'
USER_ID='REDACTED_USER_ID'
CAMPUS_ID='19'
LOCATION_ID='REDACTED_LOCATION_ID'

curl_json() {
  local endpoint="$1"
  local body="$2"
  curl --fail-with-body -sS "$BASE/api_user/$endpoint" \
    -X POST \
    -H 'Accept: */*' \
    -H 'Content-Type: application/json' \
    -H "sessionid: $SESSION_ID" \
    -H "login_token: $LOGIN_TOKEN" \
    --data "$body"
}
```

The app may also add `x-transact-token` for an override-server configuration.
That value is not required by the normal menu requests documented here.

## Confirmed request examples

### `GET /api_user/samllogin`

Starts the campus SAML login flow. This is a browser redirect, not a normal
authenticated API call.

Required query parameter: `campusid`.

```bash
curl --fail-with-body -sS \
  "$BASE/api_user/samllogin?campusid=$CAMPUS_ID" \
  -D -
```

### `POST /api_user/samlsuccess`

Browser SAML handoff endpoint. The response contains a temporary Transact token
that the native client hashes before calling the registration endpoint. It is
not intended to be called with a manually invented JSON body.

### `POST /api_user/registerwithcampusssotoken`

Observed after SAML login. Required header: `sessionid`.

Confirmed body fields:

```json
{
  "userid": "0",
  "hash": "REDACTED_HMAC_SHA256",
  "os_type": "0",
  "app_bundle_name": "com.transact.mobileorder",
  "language": "EN",
  "temp_token": "REDACTED_ONE_TIME_TOKEN",
  "campusid": "19"
}
```

```bash
curl_json registerwithcampusssotoken '{
  "userid": "0",
  "hash": "REDACTED_HMAC_SHA256",
  "os_type": "0",
  "app_bundle_name": "com.transact.mobileorder",
  "language": "EN",
  "temp_token": "REDACTED_ONE_TIME_TOKEN",
  "campusid": "19"
}'
```

The response provides the user ID and an intermediate login token.

### `POST /api_user/loginwithtoken`

Completes the native-client login. Required headers: `sessionid` and the
intermediate `login_token`.

Confirmed body fields from the working web recapture:

```json
{
  "device_model": "DukeHalal Web SSO",
  "campusid": "19",
  "on_launch": "1",
  "app_version": "2026.3.1",
  "userid": "REDACTED_USER_ID",
  "carrier_name": "",
  "accessibility_mode": "0",
  "device_name": "DukeHalal Web SSO",
  "push_enabled": "0",
  "os_language": "en-US",
  "timezone": "EST",
  "app_bundle_name": "com.transact.mobileorder",
  "os_version": "web",
  "push_token": "",
  "os_type": "0"
}
```

```bash
curl "$BASE/api_user/loginwithtoken" \
  -X POST \
  -H 'Content-Type: application/json' \
  -H "sessionid: $SESSION_ID" \
  -H 'login_token: REDACTED_INTERMEDIATE_TOKEN' \
  --data '{
    "device_model": "DukeHalal Web SSO",
    "campusid": "19",
    "on_launch": "1",
    "app_version": "2026.3.1",
    "userid": "REDACTED_USER_ID",
    "carrier_name": "",
    "accessibility_mode": "0",
    "device_name": "DukeHalal Web SSO",
    "push_enabled": "0",
    "os_language": "en-US",
    "timezone": "EST",
    "app_bundle_name": "com.transact.mobileorder",
    "os_version": "web",
    "push_token": "",
    "os_type": "0"
  }'
```

### `POST /api_user/getmenu`

This is the endpoint used by `fetch_fresh_menus.py` and is fully confirmed.

Required headers: `sessionid`, `login_token`.

Confirmed body fields:

```json
{
  "ct_id2": "0",
  "target_date": "",
  "userid": "REDACTED_USER_ID",
  "target_time": "",
  "campusid": "19",
  "ct_id": "0",
  "locationid": "REDACTED_LOCATION_ID",
  "payment_method": "0",
  "retrieval_type": "0"
}
```

```bash
curl_json getmenu '{
  "ct_id2": "0",
  "target_date": "",
  "userid": "REDACTED_USER_ID",
  "target_time": "",
  "campusid": "19",
  "ct_id": "0",
  "locationid": "REDACTED_LOCATION_ID",
  "payment_method": "0",
  "retrieval_type": "0"
}'
```

### `POST /api_user/getaffiliationswithcampus`

Observed in traffic.

Required body fields: `userid`, `campusid`.

```bash
curl_json getaffiliationswithcampus '{
  "userid": "0",
  "campusid": "19"
}'
```

## Endpoint worksheet

All entries below are client API actions. Unless a different method is shown,
the native client uses `POST` with JSON and the common `sessionid` and
`login_token` headers. The `curl_json` examples are request-shape templates,
not instructions to execute mutating production calls.

| Client action | Endpoint key/path | Parameters currently known | Confidence | Risk | Curl template |
|---|---|---|---|---|---|
| `loginWithToken:` | `loginwithtoken` | Device/app fields, `userid`, `campusid`; intermediate `login_token` header | Confirmed | Auth | `curl_json loginwithtoken '{"userid":"REDACTED_USER_ID","campusid":"19"}'` |
| `logout` | `logout` | None confirmed | Binary-confirmed key | Account | `curl_json logout '{}'` |
| `logoutAndDelete` | `logoutanddelete` | None confirmed | Binary-confirmed key | Account deletion | `curl_json logoutanddelete '{}'` |
| `getUser:` | `getuser` | No endpoint-specific parameters | Binary-confirmed key | Read-only | `curl_json getuser '{}'` |
| `getLocations` | `getcampuslocations` | `campusid` | Binary-confirmed key | Read-only | `curl_json getcampuslocations '{"campusid":"19"}'` |
| `getMenu:withHUD:andPaymentMethod:` | `getmenu` | `campusid`, `locationid`, `userid`, `payment_method`, `retrieval_type`, date/time and `ct_id` fields | Confirmed | Read-only | See confirmed `getmenu` example |
| `getAllMenusForCampus:` | `getallmenusforcampus` | Campus and menu-selection values; full body unverified | Binary-confirmed key | Read-only | Capture before reproducing |
| `getContests` | `getcontests` | None confirmed | Binary-confirmed key | Read-only | Capture before reproducing |
| `getPastOrders` | `getpastorders` | None confirmed | Binary-confirmed key | Read-only | Capture before reproducing |
| `getCampusesWithBundleName:withBundle:usingSecondary:` | `getcampuseswithbundlename` | Bundle name, bundle/configuration value, secondary flag | Binary-confirmed key | Read-only | `curl_json getcampuseswithbundlename '{"bundle_name":"REDACTED","bundle":"REDACTED","using_secondary":"0"}'` |
| Secondary campus lookup | `getcampuseswithbundlenamesecondary` | Same as campus lookup; exact body unverified | Binary-confirmed key | Read-only | `curl_json getcampuseswithbundlenamesecondary '{"bundle_name":"REDACTED","bundle":"REDACTED"}'` |
| `loginWithEmail:andPassword:forCampus:` | `loginwithemailandpassword` | Email, password, `campusid` | Binary-confirmed key | Auth | `curl_json loginwithemailandpassword '{"email":"REDACTED","password":"REDACTED","campusid":"19"}'` |
| `registerWithEmail:pass:first:last:campusid:` | `registerwithemail` | Email/password, first/last name, `campusid` | Binary-confirmed key | Account creation | `curl_json registerwithemail '{"email":"REDACTED","pass":"REDACTED","first":"REDACTED","last":"REDACTED","campusid":"19"}'` |
| `registerWithApple:userid:first:last:campusid:` | `registerwithapple` | Apple token, user ID, first/last name, `campusid` | Binary-confirmed key | Auth/account | `curl_json registerwithapple '{"userid":"REDACTED","first":"REDACTED","last":"REDACTED","campusid":"19"}'` |
| `registerWithGoogle:authtoken:googleUserid:fullname:photo_url:campusid:` | Not exposed as a simple lower-case key | Google auth token, Google user ID, full name, photo URL, `campusid` | Source-confirmed | Auth/account | Capture the request before reproducing it |
| `registerWithSSO:token:userid:first:last:phone:photo_url:campusid:` | `registerwithsso` | SSO token, user ID, name, phone, photo URL, `campusid` | Binary-confirmed key | Auth/account | `curl_json registerwithsso '{"token":"REDACTED","userid":"REDACTED","first":"REDACTED","last":"REDACTED","phone":"REDACTED","photo_url":"REDACTED","campusid":"19"}'` |
| `registerWithCampusSSO:cardid:first:last:campusid:extra1:extra2:` | `registerwithcampussso` | Card ID, name, `campusid`, `extra1`, `extra2` | Binary-confirmed key | Auth/account | `curl_json registerwithcampussso '{"cardid":"REDACTED","first":"REDACTED","last":"REDACTED","campusid":"19","extra1":"","extra2":""}'` |
| `registerWithCampusSSOToken:withCampusId:` | `registerwithcampusssotoken` | `userid`, hash, app/device fields, temp token, `campusid` | Confirmed | Auth | See confirmed registration example |
| `ldapLogin:password:campusid:from_reg:withAcountType:` | `ldaplogin` | LDAP identity, password, `campusid`, registration flag, account type | Binary-confirmed key | Auth | `curl_json ldaplogin '{"ldap":"REDACTED","password":"REDACTED","campusid":"19","from_reg":"0","account_type":"REDACTED"}'` |
| `changeCampus:fromProfile:` | `changecampus` | Target campus/profile values | Binary-confirmed key | Account state | `curl_json changecampus '{"campusid":"REDACTED"}'` |
| Email-receipt preference | `changeemailreceipts` | Preference value; exact caller body unverified | Binary-confirmed key | Account mutation | **Do not replay** |
| Loyalty opt-in preference | `changeloyaltyoptin` | Opt-in value; exact caller body unverified | Binary-confirmed key | Account mutation | **Do not replay** |
| `apiCallUpdatingUserWithEndpoint:...` | Generic dispatcher | Caller-supplied endpoint and parameters | Source-confirmed | Varies | `curl_json ENDPOINT_KEY '{"fields":"from caller"}'` |
| `addCreditCard:withLastFour:andCardType:` | `addcreditcard` | Card/payment payload, last four, card type | Binary-confirmed key | Payment | **Do not replay** |
| `removePaymentMethod:` | `removepaymentmethod` | Payment method ID | Binary-confirmed key | Payment mutation | **Do not replay** |
| `changeDefaultPaymentMethod:` | `changedefaultpaymentmethod` | Payment method ID | Binary-confirmed key | Payment mutation | **Do not replay** |
| `addCreditCardGetUrl` | `addcreditcardgeturl` | None confirmed | Binary-confirmed key | Payment | Capture before reproducing |
| `addMealplanToken:` | `addmealplantoken` | Meal-plan token | Binary-confirmed key | Account/payment | **Do not replay** |
| `addMealplanDirectAuth:withPassword:` | `addmealplandirectauth` | Direct-auth identity/password | Binary-confirmed key | Account/payment | **Do not replay** |
| `calculateCart:withHud:` | `calculatecart` | Cart payload | Binary-confirmed key | Read-only calculation | `curl_json calculatecart '{"cart":"REDACTED_CART"}'` |
| `validatePromoCode:withLocation:andSubtotal:` | `validatepromocodeonetime` | Promo code, location, subtotal | Binary-confirmed key | Read-only calculation | `curl_json validatepromocodeonetime '{"promo_code":"REDACTED","locationid":"REDACTED","subtotal":"REDACTED"}'` |
| `processOrder:` | `processorder` | Complete order payload | Binary-confirmed key | **Order creation** | **Do not replay** |
| `processOrderStatusCheck:` | `processorderstatuscheck` | Order ID/reference | Binary-confirmed key | Read-only order | `curl_json processorderstatuscheck '{"order":"REDACTED_ORDER"}'` |
| `getPendingOrders` | `getpendingorders` | None confirmed | Binary-confirmed key | Read-only order | `curl_json getpendingorders '{}'` |
| `cancelPendingOrder:` | `cancelpendingorder` | Pending order ID | Binary-confirmed key | **Order cancellation** | **Do not replay** |
| `checkinOrder:withCheckinCode:` | `checkinorder` | Order ID, check-in code | Binary-confirmed key | Order mutation | **Do not replay** |
| `emailOrderReceipt:` | `emailorderreceipt` | Order ID/reference | Source-confirmed | External side effect | **Do not replay** |
| `rateOrder:withAppRating:withFoodRating:withAppComment:withFoodComment:` | `rateorder` | Order ID, ratings, comments | Binary-confirmed key | Account/content mutation | **Do not replay** |
| `getReviewQuestions` | `getreviewquestions` | None confirmed | Binary-confirmed key | Read-only | `curl_json getreviewquestions '{}'` |
| `submitReviewOrder:withAnswers:` | `submitrevieworder` | Order ID, answers | Binary-confirmed key | Content mutation | **Do not replay** |
| `rateAppClicked` | No matching lower-case key found | None confirmed | Inferred | Analytics | Capture before reproducing |
| `getLoyaltyData` | `getloyaltydata` | None confirmed | Binary-confirmed key | Read-only account | `curl_json getloyaltydata '{}'` |
| `getInboxMessages` | `getinboxmessages` | None confirmed | Binary-confirmed key | Read-only account | `curl_json getinboxmessages '{}'` |
| `submitContestEntry:` | `submitcontestentry` | Contest/entry payload | Binary-confirmed key | Account/content mutation | **Do not replay** |
| `purchaseReward:` | `purchasereward` | Reward ID/purchase payload | Binary-confirmed key | **Purchase mutation** | **Do not replay** |
| `changeDietaryRestrictions:` | `changedietaryrestrictions` | Dietary restriction values | Binary-confirmed key | Account mutation | **Do not replay** |
| `openedMessage:` | `openedmessage` | Message ID | Binary-confirmed key | Account mutation | **Do not replay** |
| `retrievePhotoAndSendToServer:` | No matching lower-case key found | Photo/reference payload | Inferred | Upload/content mutation | **Do not replay** |
| `trackAppEvents` | `trackappevents` | Event list, session metadata | Binary-confirmed key | Analytics | `curl_json trackappevents '{"userid":"REDACTED_USER_ID","campusid":"19","events":[]}'` |
| `verifyAmazonIdentity:authLocation:timestamp:identityKey:requestId:storeId:` | No matching lower-case key found | Amazon identity/auth fields, timestamp, key, request/store IDs | Inferred | Payment integration | **Do not replay** |
| `verifyAmazonShopperWithStoreId:identityKey:requestId:timestamp:` | No matching lower-case key found | Store ID, identity key, request ID, timestamp | Inferred | Payment integration | **Do not replay** |
| `verifyAmazonCart:` | No matching lower-case key found (`amazon_cart` and `verify amazon cart` strings exist) | Cart/payment verification payload | Inferred | Payment integration | **Do not replay** |

### Other client API features with no endpoint literal yet

These feature methods are present in the binary, but the current pass did not
find a dedicated lower-case API key. They should remain names in the map—not
guessed URLs—until a call site or captured request resolves them:

```text
getAutomatedCheckoutLocations
getAutomatedCheckoutBarcode:withPublicKeyX:andPublicKeyY:isAssociate:...
getTendersFromServerForLocation:
retrievePhotoAndSendToServer:
rateAppClicked
verifyAmazonIdentity:...
verifyAmazonShopperWithStoreId:...
verifyAmazonCart:
```

## How to turn inferred rows into confirmed rows

For each endpoint key in Ghidra:

1. Find the `cf_*` string reference.
2. Follow the caller into `APIUtility::setup:withParameters:withOverrideServerUrl:`.
3. Inspect the caller's dictionary construction to identify exact JSON keys.
4. Capture the same action in mitmproxy using your own authorized account.
5. Record the observed path, body, response status, and required headers here.

The actual URL mapping is assembled by the app from `getServerURL` plus the
endpoint key. Do not assume every selector maps to `/api_user/<lowercased
selector>` until the request is observed or the URL construction is confirmed.

## Known common headers

From `APIUtility` and captured traffic:

```text
sessionid       Client-generated tracking/session value.
login_token     Server-issued authentication token.
Content-Type    application/json.
Content-Length  Serialized JSON body length.
x-transact-token Optional override-server configuration header.
```

Never commit actual values for these headers or request bodies.
