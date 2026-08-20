# JANUS Privacy Policy

**Effective date: 20 August 2026**

JANUS is an experimental functional-metacognition/agency application. This policy explains what information JANUS processes, why it is processed, where it goes, how long it is kept, and how users can delete it.

## Information you provide

JANUS may collect your username, email address, password-derived authentication data, messages you send to JANUS, memories or context created from your conversations, account settings, and account-deletion requests. Passwords are not stored in plaintext; password-backed accounts use salted password hashes.

## Google Sign-In

If you use Google Sign-In, JANUS receives identity information needed to authenticate you, including your verified Google email address and Google account subject identifier. JANUS uses this only to create or link your JANUS account and authenticate access.

## Conversation and AI processing

Messages sent to JANUS may be transmitted to OpenAI's API to generate responses. Recent conversation context may be included so JANUS can maintain continuity. JANUS also stores user-scoped conversation, memory, activity, message/outbox and background-reflection records on the JANUS server.

## Email

JANUS may use a transactional email provider to send account-verification and password-reset messages. During development, email delivery may use a provider sandbox sender and may be limited to test recipients. Production public release requires a verified JANUS sending domain.

## Device permissions and identifiers

The Android app currently requests Internet access and notification permission. It does not request location, contacts, camera, microphone, SMS, calendar, Bluetooth, media/storage, or advertising-ID permissions. JANUS does not use Android device identifiers as an account identity fallback; authenticated sessions establish account identity.

## Notifications

If you allow notifications, JANUS may show locally generated notifications when new JANUS messages are available. Notification permission can be changed in Android settings.

## Security and sessions

JANUS uses bearer session tokens for authenticated access. Session tokens are stored as hashes on the server and expire after approximately 30 days. Password-reset and email-verification tokens are one-time, expiring values and are also stored only as hashes.

## Retention

Conversation, memory, activity, outbox and related continuity records are retained while your JANUS account exists because persistent continuity is a core feature. They are deleted when the account is permanently deleted. Expired sessions are automatically purged. Expired or used authentication-action tokens are cleaned up regularly. Unverified public deletion requests are retained for up to 90 days before automatic cleanup.

## Account deletion

You can permanently delete your account inside the JANUS app. This removes the account and known associated user-scoped JANUS data. If you cannot access the app, use the public account-deletion page at `/delete-account`. Public deletion requests require ownership verification before deletion.

## Service providers

JANUS currently relies on service providers including Render for hosting, Google for optional Google Sign-In, OpenAI for AI model processing, and a transactional email provider for verification/recovery messages. These providers process data only as needed to provide their respective services, subject to their own terms and privacy practices.

## Data sale and advertising

JANUS does not currently sell personal information and does not currently include third-party advertising or advertising-ID based tracking.

## Children

JANUS is not currently designed or marketed as a child-directed service. Age-targeting and store classification will be finalized before public release.

## Changes

This policy may be updated as JANUS features, providers or legal obligations change. Material changes should be reflected by updating the effective date and the public policy.

## Contact

Support/contact details will be published on the JANUS public website before public store release.
