# JANUS Google Play Data Safety & App Content Submission Guide

Status: working submission answers based on the JANUS code/privacy audit as of 20 August 2026. Re-audit the final shipping AAB and dependencies immediately before submission.

## Data Safety — overview answers

- Does the app collect or share required user data types? **Yes.**
- Is all user data encrypted in transit? **Yes** for JANUS-controlled Android/server transport: HTTPS/TLS is required and cleartext Android traffic is disabled.
- Does the app provide a way for users to request deletion? **Yes.** JANUS has authenticated in-app account deletion and a public `/delete-account` web resource.
- Account creation supported? **Yes.** Password accounts and optional Google Sign-In.

Google Play's definition of "sharing" has exceptions for transfers to service providers processing data on the developer's behalf. The final console answer must be checked against Google's current definitions and the production contracts/configuration for OpenAI, Google, Render and the transactional email provider.

## Data types to declare as collected

### Personal info — Name / username
Collected: **Yes**.
Purpose: App functionality; Account management.
Processing: Stored on JANUS server and used for user-scoped continuity/account identity.
Optional: Account identity is required to use authenticated persistent JANUS features.

### Personal info — Email address
Collected: **Yes**.
Purpose: Account management; Authentication; Developer communications for verification/password recovery.
Processing: Stored by JANUS; may be sent to Google during Google-authentication flows as applicable and to the transactional email service when JANUS sends account email.

### User-generated content — Other user-generated content
Collected: **Yes**.
Includes: JANUS conversation messages and content users intentionally submit.
Purpose: App functionality; AI response generation; persistent continuity/memory.
Processing: Stored by JANUS and may be transmitted to OpenAI as a service provider to generate responses.

### App activity — App interactions / other app activity
Collected: **Yes**.
Includes: JANUS activity/events, outbox/read state and background-reflection/continuity records generated from use of the service.
Purpose: App functionality; persistent continuity; account-scoped history and messaging.

## Data types currently NOT intentionally collected by JANUS app code

Do not select these unless the final AAB/dependencies show otherwise: precise location, approximate location, contacts, SMS/MMS, call logs, photos, videos, audio recordings, files/documents, calendar, health/fitness, payment information, purchase history, advertising ID, installed-app inventory, crash telemetry, diagnostics/performance telemetry, or advertising/marketing profile data.

The obsolete Android ID account-identity fallback has been removed and should not be declared as a JANUS-collected device identifier on that basis. Recheck bundled SDK behaviour before submission.

## Data usage purposes

Expected purposes to select where the Console asks per data type:

- **App functionality** — conversation, memory, continuity, JANUS messages/background features.
- **Account management** — username/email/account/session management.
- **Developer communications** — verification and password-recovery email only where applicable.

JANUS currently has no advertising, ad personalization or behavioural marketing purpose.

## Account deletion

Answer that JANUS supports account deletion.

In-app path: Options/account area -> Delete account -> confirmation -> authenticated server deletion.

External web resource to enter in Play Console:
`https://janus-global-core.onrender.com/delete-account`

Deletion removes the account and known associated user-scoped JANUS data. The Privacy Policy explains retention exceptions/temporary records. Public deletion requests require ownership verification rather than deleting an account based only on knowledge of an email address.

## Privacy policy

Play Console privacy-policy URL:
`https://janus-global-core.onrender.com/privacy`

Before submission, add an easily discoverable Privacy Policy link inside the Android app as well as the Play listing.

## Ads declaration

Does the app contain ads? **No**, based on the audited code.

## App access / reviewer instructions

JANUS has authenticated/restricted functionality, so provide Google Play reviewers with a working demo/test account or other valid access instructions. The review account must be able to reach the principal conversation/account-management features without requiring the reviewer to contact the developer.

Never put a production administrator credential into public store metadata. Create a dedicated review account and rotate/remove it when appropriate.

## Target audience / children

Current intended classification: JANUS is **not child-directed**. Final age groups must be selected deliberately in Play Console. Do not select child age groups unless JANUS is redesigned and reviewed for Google Play Families requirements and applicable child-privacy obligations.

## Content rating

Complete Google's required content-rating questionnaire based on the actual generative-AI conversational experience. Because JANUS can generate conversational content dynamically, answer conservatively and accurately rather than rating only static UI text.

## AI-generated content policy — RELEASE BLOCKER

JANUS is a text-to-text conversational generative-AI app. Google Play requires generative-AI apps to include an **in-app user reporting/flagging feature** allowing users to report offensive AI-generated content without leaving the app. JANUS should not be submitted to production until this is implemented and connected to a developer-review/moderation workflow.

The app must also comply with Google Play Restricted Content and other applicable policies for AI-generated output. User reports should inform moderation/content-filtering decisions.

## Data deletion and AI/service providers

For account deletion, JANUS deletes data from its own server. Before production launch, verify processor-specific deletion/retention behaviour for data previously sent to service providers and document/request deletion where required by Google Play policy and applicable law.

## Security statements

- HTTPS/TLS for Android-to-JANUS traffic.
- Passwords stored as salted hashes, not plaintext.
- Server stores hashes of JANUS session tokens.
- Google identity tokens are server-validated.
- Password reset invalidates sessions.
- Account deletion exists in-app and externally.

Do not claim independent security certification unless JANUS actually obtains one.

## Other App Content declarations

Expected current answers, subject to final Play Console wording:

- Ads: **No**.
- App access: **Restricted functionality exists; reviewer credentials/instructions required**.
- Target audience: **Adults / non-child-directed**; choose exact age bands at submission.
- News app: **No**.
- Government app: **No**.
- Financial features: **No**, unless future features change this.
- Health features: **No**, unless future features change this.
- High-risk permissions: none currently identified beyond ordinary Internet/notification permission; recheck final manifest.

## Pre-submission gates

1. Implement in-app AI response reporting/flagging and a developer moderation/review path.
2. Add in-app Privacy Policy and Terms links.
3. Re-run privacy/data audit against final AAB, manifest and Gradle dependency tree.
4. Verify the public `/privacy`, `/terms`, and `/delete-account` URLs are live and stable.
5. Verify production transactional email with a verified JANUS sender/domain.
6. Create a dedicated Play reviewer account and test it from a clean device.
7. Complete content rating from the actual app behaviour.
8. Confirm target audience and store listing accurately describe an AI conversational application.
9. Recheck Google Play policies immediately before submission; policies and Console wording can change.
