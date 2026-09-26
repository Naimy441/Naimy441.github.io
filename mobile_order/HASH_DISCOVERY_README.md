# Mobile Order SSO Hash Discovery

This documents the successful process used to identify how the Mobile Order macOS app creates the `hash` field for `registerwithcampusssotoken`.

## Important security note

The captured mitmproxy flow files can contain Duke credentials, SAML assertions, cookies, temporary tokens, and login tokens. Do not commit them, upload them, or share them. Delete old captures after analysis and change any password that appeared in a capture.

## 1. Install Ghidra

Ghidra was downloaded from the official NSA release page:

<https://github.com/NationalSecurityAgency/ghidra/releases/latest>

The archive was verified with its published SHA-256 checksum and extracted to:

```text
/Applications/ghidra_12.1.4_PUBLIC/
```

Java 21 was already installed. Ghidra initially warned that native components were missing because the public release did not include macOS ARM native binaries.

Command to open Ghidra manually:
/Applications/ghidra_12.1.4_PUBLIC/ghidraRun

## 2. Build Ghidra's macOS native components

The Mac was confirmed to be Apple Silicon and Xcode was installed:

```bash
uname -m
xcode-select -p
```

The native components were built with Ghidra's included Gradle wrapper:

```bash
cd /Applications/ghidra_12.1.4_PUBLIC/support/gradle
./gradlew buildNatives
```

The build completed successfully. Ghidra was then restarted.

## 3. Locate the actual Mobile Order executable

The outer app is a wrapper. The executable is not in the usual `Contents/MacOS` directory.

The app was located at:

```text
/Applications/Mobile Order.app/
```

The actual Mach-O executable was found with:

```bash
find "/Applications/Mobile Order.app" -type f -print0 \
  | xargs -0 file \
  | rg 'Mach-O'
```

The relevant executable is:

```text
/Applications/Mobile Order.app/Wrapper/TRANSACT.app/Transact Prod
```

It is an arm64 Mach-O binary.

## 4. Import the executable into Ghidra

In Ghidra:

1. Create a **Non-Shared Project**.
2. Choose **File → Import**.
3. Press **Cmd + Shift + G** in the file chooser.
4. Paste the executable path above.
5. Accept the Mach-O ARM64 format.
6. Run the default analyzers.

The outer `.app` folders are not the file to analyze. Import `Transact Prod` itself.

## 5. Identify the registration callback

Searching for the string `registerWithCampusSSOToken:withCampusId:` first led to a function named approximately:

```text
FUN_10000cdf8
```

That function was only a response callback. It:

- Processes the server response.
- Checks the response success value.
- Updates the user and campus objects.
- Posts success or failure notifications.

It does not calculate the hash.

The important distinction was to follow the actual Objective-C method implementation rather than the `_block_invoke` callback.

## 6. Locate the actual registration method

The Objective-C metadata showed this method:

```text
[APICall registerWithCampusSSOToken:withCampusId:]
```

Its implementation address was identified from the Objective-C method list:

```text
0x10000cb00
```

Disassembling around that address showed that the registration method calls:

```text
[self hashWithSalt:token]
```

The call is made through an Objective-C stub whose selector string is:

```text
hashWithSalt:
```

The registration method then uses the returned value while constructing the request body.

## 7. Locate `hashWithSalt:`

The Objective-C metadata mapped the `hashWithSalt:` method to:

```text
0x100014458
```

The relevant disassembly showed this sequence:

1. Load the app's embedded salt string.
2. Convert the salt to a UTF-8 C string.
3. Convert the input token to a UTF-8 C string.
4. Measure both byte lengths using UTF-8 encoding.
5. Call CommonCrypto's `CCHmac`.
6. Use algorithm value `2`, which is SHA-256.
7. Convert all 32 output bytes to lowercase hexadecimal using `%02x`.

The resulting output is therefore 64 hexadecimal characters.

## 8. Identify the embedded salt

The method loaded a constant Objective-C string. The constant was resolved through the app's `__DATA_CONST,__cfstring` section and its referenced string data.

The embedded salt is:

```text
dFz9Dq435BT3xCVU2PCy
```

## 9. Final algorithm

The app calculates:

```text
HMAC-SHA256(key = embedded salt, message = temp_token)
```

The result is encoded as lowercase hexadecimal.

Equivalent Python:

```python
import hashlib
import hmac

hash_value = hmac.new(
    b"dFz9Dq435BT3xCVU2PCy",
    temp_token.encode("utf-8"),
    hashlib.sha256,
).hexdigest()
```

## 10. Verify against a successful capture

The captured flow was analyzed without printing any token or credential values. The verification compared:

```text
HMAC-SHA256(salt, register_request.temp_token)
```

against the `hash` field in the captured `registerwithcampusssotoken` request.

The computed value matched the captured request hash exactly, confirming the algorithm.

## Useful static-analysis commands

List Mach-O binaries inside the app:

```bash
find "/Applications/Mobile Order.app" -type f -print0 \
  | xargs -0 file \
  | rg 'Mach-O'
```

Search strings:

```bash
strings -a -t x \
  "/Applications/Mobile Order.app/Wrapper/TRANSACT.app/Transact Prod" \
  | rg -i 'registerwithcampus|hashwithsalt|CCHmac|SHA256|temp_token'
```

Inspect Objective-C metadata:

```bash
otool -arch arm64 -ov \
  "/Applications/Mobile Order.app/Wrapper/TRANSACT.app/Transact Prod"
```

Disassemble the relevant app code:

```bash
xcrun llvm-objdump -d --macho --arch-name=arm64 \
  "/Applications/Mobile Order.app/Wrapper/TRANSACT.app/Transact Prod"
```

The important addresses discovered were:

```text
registerWithCampusSSOToken:withCampusId:  0x10000cb00
hashWithSalt:                             0x100014458
```

