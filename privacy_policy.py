"""Public JANUS Privacy Policy page."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["legal"])

POLICY_HTML = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>JANUS Privacy Policy</title><style>body{font-family:Arial,sans-serif;max-width:820px;margin:40px auto;padding:0 18px;line-height:1.55;color:#171717}h1,h2{line-height:1.2}small{color:#666}a{color:#0645ad}</style></head><body>
<h1>JANUS Privacy Policy</h1><p><small>Effective: 21 August 2026</small></p>
<p>JANUS is an experimental functional-metacognition/agency application. This policy explains what information JANUS processes, why it is processed, where it goes, how long it is kept, and how users can delete it.</p>
<h2>Information you provide</h2><p>JANUS may collect your username, email address, password-derived authentication data, messages you send to JANUS, memories or context created from your conversations, account settings, and account-deletion requests. Passwords are not stored in plaintext; password-backed accounts use salted password hashes.</p>
<h2>Google Sign-In</h2><p>If you use Google Sign-In, JANUS receives identity information needed to authenticate you, including your verified Google email address and Google account subject identifier. JANUS uses this only to create or link your JANUS account and authenticate access.</p>
<h2>Conversation and AI processing</h2><p>Messages sent to JANUS may be transmitted to OpenAI's API to generate responses. Recent conversation context may be included so JANUS can maintain continuity. JANUS also stores user-scoped conversation, memory, activity, message/outbox and background-processing records on the JANUS server. Deterministic local/server core cycles do not themselves require external model calls; paid background language reflection is disabled by default in the current production configuration.</p>
<h2>Email</h2><p>JANUS may use a transactional email provider to send account-verification and password-reset messages. During development, email delivery may use a provider sandbox sender and may be limited to test recipients. Production public release will require a verified JANUS sending domain.</p>
<h2>Device permissions and identifiers</h2><p>The Android app currently requests Internet access and notification permission. It does not request location, contacts, camera, microphone, SMS, calendar, Bluetooth, media/storage, or advertising-ID permissions. JANUS no longer uses Android device identifiers as an account identity fallback; authenticated sessions establish account identity. A random installation/device identifier may be used to distinguish synchronized JANUS runtime summaries and is not used for advertising.</p>
<h2>Notifications</h2><p>If you allow notifications, JANUS may show locally generated notifications when new JANUS messages are available. Notification permission can be changed in Android settings.</p>
<h2>Security and sessions</h2><p>JANUS uses bearer session tokens for authenticated access. Session tokens are stored as hashes on the server and expire after approximately 30 days. Password reset and email-verification tokens are one-time, expiring values and are also stored only as hashes. Supported native clients use operating-system protected storage where implemented, including Windows DPAPI and Apple Keychain; passwords are not persisted by those clients.</p>
<h2>Retention</h2><p>Conversation, meaningful memory, activity, outbox and related continuity records are retained while your JANUS account exists because persistent continuity is a core feature. They are deleted when the account is permanently deleted. Temporary delivery/idempotency receipts are normally removed after about 7 days and repetitive runtime snapshots after about 30 days. Expired sessions are automatically purged. Expired or used authentication-action tokens are cleaned up regularly. Unverified public deletion requests are retained for up to 90 days before automatic cleanup.</p>
<h2>Account deletion</h2><p>You can permanently delete your account inside the JANUS app. This removes the account and known associated user-scoped JANUS data. If you cannot access the app, use the public account-deletion page at <a href='/delete-account'>/delete-account</a>. Public deletion requests require ownership verification before deletion.</p>
<h2>Service providers</h2><p>JANUS currently relies on service providers including Render for hosting, Google for optional Google Sign-In, OpenAI for AI model processing, and a transactional email provider for verification/recovery messages. These providers process data only as needed to provide their respective services, subject to their own terms and privacy practices.</p>
<h2>Data sale and advertising</h2><p>JANUS does not currently sell personal information and does not currently include third-party advertising or advertising-ID based tracking.</p>
<h2>Children</h2><p>JANUS is not currently designed or marketed as a child-directed service. Age-targeting and store classification will be finalized before public release.</p>
<h2>Changes</h2><p>This policy may be updated as JANUS features, providers or legal obligations change. Material changes should be reflected by updating the effective date and the public policy.</p>
<h2>Contact</h2><p>Support/contact details will be published on the JANUS public website before public store release.</p>
</body></html>"""


@router.get("/privacy", response_class=HTMLResponse)
def privacy_policy():
    return HTMLResponse(POLICY_HTML)
