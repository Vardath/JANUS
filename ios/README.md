# JANUS for iOS

This folder contains the Apple/iOS version of JANUS.

It is a native SwiftUI client that connects to the hosted JANUS global core at:

`https://janus-global-core.onrender.com`

## Current feature-branch checkpoint

**iOS v0.2** supports authenticated JANUS accounts, Keychain-backed session storage, Chat/Messages/Observe/Options surfaces, and inline presentation of Stage-1 JANUS-generated images. Image bytes are fetched from the account-bound JANUS file endpoint using the saved bearer session; generated files are not exposed through public image URLs.

## Build locally on a Mac

1. Install Xcode from the Mac App Store.
2. Install XcodeGen:

   ```bash
   brew install xcodegen
   ```

3. Generate and open the project:

   ```bash
   cd ios
   xcodegen generate
   open JANUS.xcodeproj
   ```

4. In Xcode, choose the `JANUS` scheme and run it on an iPhone simulator or real iPhone.

## GitHub build

The repository has a GitHub Actions workflow at:

`.github/workflows/build-ios.yml`

It builds an unsigned iOS Simulator app. This is useful for checking that the Apple version compiles before store signing is added. The v0.2 image-capable simulator build has passed CI on the lightweight-image feature branch.

## App Store signing still needed

For TestFlight and App Store release, add the real Apple Developer Team ID, signing certificates, provisioning profiles, production app icons, privacy policy URL, screenshots, and App Store Connect listing details.

The bundle identifier is currently:

`com.vardath.janus`
