# JANUS Android Google OAuth configuration

This document records the values required for Google Sign-In for the GitHub-built JANUS Android debug APK.

## Android OAuth client

Create or update a Google Auth Platform OAuth client of type **Android** with:

- Package name: `com.vardath.janus`
- SHA-1 certificate fingerprint: `52:CA:77:37:99:AB:23:1B:F9:A1:58:8C:E2:E5:17:4C:9C:9F:FC:FC`
- SHA-256 certificate fingerprint (reference): `26:25:E7:55:AE:7C:7B:38:1E:89:55:76:D3:9A:ED:8D:0E:20:96:45:64:98:89:1A:A2:64:A3:6C:1F:60:B2:4D`

These fingerprints come from the stable GitHub Actions debug keystore cached under `janus-android-debug-keystore-v1`. The Android OAuth client is used by Google to verify the package/signing identity; its client ID is not passed to `GetSignInWithGoogleOption`.

## Web OAuth client

The app passes the **Web application OAuth client ID** as the server client ID to Credential Manager / Sign in with Google. The server verifies ID tokens against that same Web client ID.

Do not replace the Web client ID in the Android code with the Android OAuth client ID.

## Error 16

`[16] Account reauth failed` can be returned by Google Credential Manager when the Android package/signing certificate does not match an Android OAuth client in the same Google Cloud project. Before treating it as a device-account problem, verify the package and SHA-1 above.

## Google Play later

When JANUS is distributed through Google Play App Signing, Google Play will use its own app-signing certificate. Add the Play App Signing SHA-1 as another Android OAuth client (same package name) before testing a Play-distributed build. Keep the GitHub debug SHA-1 above for direct APK testing.

## Build verification

The Android GitHub Actions workflow prints the signing SHA-1/SHA-256 each run. It should remain stable while the cached debug keystore remains intact.
